"""Causal chart context: one H1 direction condition, M5 ADX, known H1 levels."""
from types import FunctionType
import numpy as np
import talib

from backtest_bot.reference import D
from simple_forex import runner as core
from simple_forex.strategy_rearmed import signals as original_signals


class ChartContext:
    def __init__(self, market):
        self.market = market
        self.h1 = D.make_bars(market, 60, 'H1')
        self.m5 = D.make_bars(market, 5, 'M5')
        self.pivots = D.find_pivots(self.h1)
        self.adx = np.full(self.m5.n, np.nan)
        complete = self.m5.complete
        starts = np.flatnonzero(complete & np.r_[True, ~complete[:-1]])
        ends = np.flatnonzero(complete & np.r_[~complete[1:], True]) + 1
        for a, b in zip(starts, ends, strict=True):
            self.adx[a:b] = talib.ADX(self.m5.high[a:b], self.m5.low[a:b], self.m5.close[a:b], 14)
        self.cache = {}

    def snapshot(self, t, direction):
        key = t, direction
        if key in self.cache:
            return self.cache[key]
        mk = self.market
        i = mk.idx(t)
        k = self.m5.slot_of_close(t)
        h = (t - self.h1.origin_ms) // self.h1.period_ms - 1
        if t % (5 * D.MIN_MS) or not 0 <= h < self.h1.n or not 0 <= k < self.m5.n:
            raise ValueError('Closed M5 decision outside data grid')
        reasons = []
        h_complete = bool(self.h1.complete[h])
        body = float(self.h1.close[h] - self.h1.open[h]) if h_complete else None
        adx = float(self.adx[k]) if np.isfinite(self.adx[k]) else None
        if not h_complete:
            reasons.append('H1_DATA_UNKNOWN')
        elif direction * body <= 0:
            reasons.append('H1_BODY_NOT_ALIGNED')
        if adx is None:
            reasons.append('ADX_WARMUP_UNKNOWN')
        elif adx < 25:
            reasons.append('ADX_BELOW_25')
        levels = []
        for p in self.pivots:
            if not t - D.DAY_MS <= p.known_at_ms <= t or p.kind != ('HIGH' if direction == 1 else 'LOW'):
                continue
            level = p.bid_high if direction == 1 else p.ask_low
            a = mk.idx(p.known_at_ms)
            present = mk.present[a:i]
            observed = mk.px['bid_high' if direction == 1 else 'ask_low'][a:i][present]
            touched = bool(np.any(direction * (observed - level) >= 0))
            status = 'VISITED' if touched else 'INTACT_OBSERVED' if present.all() else 'UNKNOWN_SINCE_CONFIRMATION'
            levels.append({'id': p.pid, 'kind': p.kind, 'mid_price': p.price,
                'executable_price': level, 'known_at_ms': p.known_at_ms,
                'freshness': status, 'observed_minutes': int(present.sum()), 'expected_minutes': i - a})
        result = {'decision_ms': t, 'H1_known_at_ms': self.h1.close_ms(h),
            'H1_complete': h_complete, 'H1_body': body, 'ADX14_M5': adx,
            'M5_known_at_ms': self.m5.close_ms(k), 'reasons': reasons, 'levels': levels}
        assert result['H1_known_at_ms'] <= t and result['M5_known_at_ms'] == t
        self.cache[key] = result
        return result

    def signal_source(self, market, day, tick=0.00001):
        raw, session = original_signals(market, day, tick)
        for event in raw:
            if event['reason'] != 'BREAKOUT':
                continue
            info = self.snapshot(event['decision_ms'], event['direction'])
            event['chart_context'] = info
            if info['reasons']:
                event.update(unfiltered_reason='BREAKOUT',
                    reason='CHART_CONTEXT_UNKNOWN' if any('UNKNOWN' in r for r in info['reasons']) else 'CHART_CONTEXT_REJECTED',
                    signal_filter_reasons=info['reasons'], account_checks_status='NOT_EVALUATED_AFTER_CONTEXT_REJECTION')
        return raw, session


def room_check(levels, direction, exit_quote, target):
    considered, reasons = [], []
    for level in levels:
        price = level['executable_price']
        if direction * (price - exit_quote) <= 0 or direction * (target - price) < 0:
            continue
        considered.append(level)
        if level['freshness'] == 'INTACT_OBSERVED' and 'H1_LEVEL_BEFORE_OR_AT_TARGET' not in reasons:
            reasons.append('H1_LEVEL_BEFORE_OR_AT_TARGET')
        if level['freshness'] == 'UNKNOWN_SINCE_CONFIRMATION' and 'H1_LEVEL_FRESHNESS_UNKNOWN' not in reasons:
            reasons.append('H1_LEVEL_FRESHNESS_UNKNOWN')
    return considered, reasons


def order(market, i, event, params, cfg, balance):
    check = core.order(market, i, event, params, cfg, balance)
    if cfg.get('research_level_veto'):
        d = event['direction']
        quote = float(market.px['bid_open' if d == 1 else 'ask_open'][i])
        levels, reasons = room_check(event['chart_context']['levels'], d, quote, check['target'])
        check['level_guard_considered'] = levels
        check['reasons'] = [*check['reasons'], *reasons]
    return check


# Only this function's private namespace replaces the order check. Original
# accounting, quote handling, positions, quotas and unknown-path halt are reused.
_simulate = FunctionType(core.simulate.__code__, {**core.simulate.__globals__, 'order': order},
    name='simulate_chart_context', argdefs=core.simulate.__defaults__, closure=core.simulate.__closure__)
_simulate.__kwdefaults__ = dict(core.simulate.__kwdefaults__) if core.simulate.__kwdefaults__ else None


def simulate(*args, signal_source, **kwargs):
    if signal_source is None:
        raise ValueError('Explicit signal source required')
    return _simulate(*args, signal_source=signal_source, **kwargs)
