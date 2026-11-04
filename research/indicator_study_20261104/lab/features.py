"""Point-in-time annotations only. Nothing here opens, rejects or closes trades."""
from datetime import timedelta
import numpy as np
import pandas as pd
import talib
from backtest_bot.reference import D


def previous_window(t_ms, kind):
    zone, hour = ('America/New_York', 17) if kind == 'NY_DAY' else ('Europe/London', 16)
    now = pd.Timestamp(t_ms, unit='ms', tz='UTC')
    date = now.tz_convert(zone).date()
    end = pd.Timestamp(f'{date} {hour}:00', tz=zone)
    if end > now:
        date -= timedelta(days=1)
    while date.weekday() >= 5:
        date -= timedelta(days=1)
    end = pd.Timestamp(f'{date} {hour}:00', tz=zone)
    start = pd.Timestamp(f'{date - timedelta(days=1)} 17:00', tz=zone) if kind == 'NY_DAY' else pd.Timestamp(f'{date} 08:00', tz=zone)
    return int(start.value // 1_000_000), int(end.value // 1_000_000)


def indicators(bars):
    result = {name: np.full(bars.n, np.nan) for name in (
        'ema20', 'ema50', 'rsi14', 'atr14', 'adx14', 'bb_upper', 'bb_middle', 'bb_lower')}
    # TA-Lib resets its seed after every missing bar. No interpolation or gap-skipping.
    starts = np.flatnonzero(bars.complete & np.r_[True, ~bars.complete[:-1]])
    ends = np.flatnonzero(bars.complete & np.r_[~bars.complete[1:], True]) + 1
    for a, b in zip(starts, ends, strict=True):
        close, high, low = (np.ascontiguousarray(values[a:b]) for values in (bars.close, bars.high, bars.low))
        upper, middle, lower = talib.BBANDS(close, 20, 2, 2, 0)
        values = [talib.EMA(close, 20), talib.EMA(close, 50), talib.RSI(close, 14),
                  talib.ATR(high, low, close, 14), talib.ADX(high, low, close, 14), upper, middle, lower]
        for name, value in zip(result, values, strict=True):
            result[name][a:b] = value
    return result


def finite(value):
    return float(value) if np.isfinite(value) else None


class Features:
    def __init__(self, market):
        self.mk = market
        self.m5 = D.make_bars(market, 5, 'M5')
        self.h1 = D.make_bars(market, 60, 'H1')
        self.pivots = D.find_pivots(self.h1)
        self.values = indicators(self.m5)
        self.cache = {}

    def window(self, t, kind):
        start, end = previous_window(t, kind)
        key = kind, start, end
        if key in self.cache:
            return self.cache[key]
        a, b = self.mk.idx(start), self.mk.idx(end)
        expected = int((end - start) // D.MIN_MS)
        out = {'source': kind, 'start_utc': D.iso(start), 'end_utc': D.iso(end),
               'expected_m1': expected, 'complete': False, 'observed_m1': 0,
               'observed_high': None, 'observed_low': None, 'levels': []}
        if a < 0 or b > self.mk.n:
            out['status'] = 'WINDOW_OUTSIDE_GRID'
        else:
            present = self.mk.present[a:b]
            out['observed_m1'] = int(present.sum())
            if present.any():
                out['observed_high'] = float(self.mk.px['mid_high'][a:b][present].max())
                out['observed_low'] = float(self.mk.px['mid_low'][a:b][present].min())
            out['complete'] = bool(present.all())
            out['status'] = 'COMPLETE' if out['complete'] else 'INCOMPLETE_LEVELS_UNKNOWN'
            if not out['complete']:
                out['first_missing_utc'] = D.iso(self.mk.t(a + int(np.flatnonzero(~present)[0])))
            else:
                for label, field, reduction in [('HIGH', 'high', np.max), ('LOW', 'low', np.min)]:
                    out['levels'].append({'name': kind + '_' + label, 'kind': label,
                        'mid': float(reduction(self.mk.px['mid_' + field][a:b])),
                        'bid': float(reduction(self.mk.px['bid_' + field][a:b])),
                        'ask': float(reduction(self.mk.px['ask_' + field][a:b])),
                        'known_at_ms': end})
        self.cache[key] = out
        return out

    def snapshot(self, t, direction, planned_entry=None, planned_target=None, stop=None):
        mk = self.mk
        i, k = mk.idx(t), self.m5.slot_of_close(t)
        if t % (5 * D.MIN_MS):
            raise ValueError('Snapshot requires a closed M5 boundary')
        if i <= 0 or i > mk.n or k < 0 or k >= self.m5.n:
            raise ValueError('Decision outside the observed grid')
        ref = float(mk.px['mid_close'][i - 1]) if mk.present[i - 1] else None
        out = {'decision_ms': t, 'decision_utc': D.iso(t), 'direction': direction,
               'reference_mid_close': ref, 'last_M5_complete': bool(self.m5.complete[k]),
               'feature_bars_known_at_ms': self.m5.close_ms(k)}
        for name, values in self.values.items():
            out[name] = finite(values[k])
        if out['bb_upper'] is not None and out['bb_upper'] != out['bb_lower'] and ref is not None:
            out['bollinger_percent_b'] = (ref - out['bb_lower']) / (out['bb_upper'] - out['bb_lower'])
        else:
            out['bollinger_percent_b'] = None
        out['ema20_minus_ema50'] = out['ema20'] - out['ema50'] if out['ema20'] is not None and out['ema50'] is not None else None
        spread = float(mk.px['ask_close'][i - 1] - mk.px['bid_close'][i - 1]) if mk.present[i - 1] else None
        out['spread_at_last_close_over_atr'] = spread / out['atr14'] if spread is not None and out['atr14'] and out['atr14'] > 0 else None
        out['signal_stop_distance_over_atr'] = direction * (ref - stop) / out['atr14'] if ref is not None and stop is not None and out['atr14'] and out['atr14'] > 0 else None
        levels = []
        for p in self.pivots:
            if p.known_at_ms > t:
                continue
            levels.append({'name': p.pid, 'kind': p.kind, 'mid': p.price,
                'bid': p.bid_high if p.kind == 'HIGH' else float(self.h1.bid_low[p.center]),
                'ask': float(self.h1.ask_high[p.center]) if p.kind == 'HIGH' else p.ask_low,
                'known_at_ms': p.known_at_ms})
        for kind in ['NY_DAY', 'LONDON_SESSION']:
            window = self.window(t, kind)
            out[kind + '_complete'] = window['complete']
            out[kind + '_status'] = window['status']
            out[kind + '_observed_m1'] = window['observed_m1']
            out[kind + '_expected_m1'] = window['expected_m1']
            out[kind + '_observed_high_not_certified'] = window['observed_high']
            out[kind + '_observed_low_not_certified'] = window['observed_low']
            levels.extend(window['levels'])
        out['confirmed_H1_pivots_available'] = sum(p.known_at_ms <= t for p in self.pivots)
        above = [x for x in levels if ref is not None and x['kind'] == 'HIGH' and x['mid'] > ref]
        below = [x for x in levels if ref is not None and x['kind'] == 'LOW' and x['mid'] < ref]
        resistance = min(above, key=lambda x: (x['mid'], -x['known_at_ms'])) if above else None
        support = max(below, key=lambda x: (x['mid'], x['known_at_ms'])) if below else None
        for name, level in [('nearest_resistance', resistance), ('nearest_support', support)]:
            out[name] = level
        side = 'bid' if direction == 1 else 'ask'
        exit_ref = float(mk.px[side + '_close'][i - 1]) if mk.present[i - 1] else None
        out['reference_exit_side_close'] = exit_ref
        # Compare a bid level with the last bid (or ask with ask). A level may still
        # lie ahead of the exit quote while remaining below the entry cost basis.
        candidates = [x for x in levels if exit_ref is not None
                      and x['kind'] == ('HIGH' if direction == 1 else 'LOW')
                      and direction * (x[side] - exit_ref) > 0]
        opponent = min(candidates, key=lambda x: direction * (x[side] - exit_ref)) if candidates else None
        out['nearest_opposing_executable_level'] = opponent
        out['known_level_before_or_at_planned_target'] = None
        out['level_distance_over_planned_stop'] = None
        out['exit_close_to_level_over_planned_stop'] = None
        if opponent and planned_entry is not None and planned_target is not None and stop is not None:
            executable_level = opponent[side]
            distance = direction * (executable_level - planned_entry)
            out['known_level_before_or_at_planned_target'] = direction * (executable_level - planned_target) <= 0
            risk = direction * (planned_entry - stop)
            out['level_distance_over_planned_stop'] = distance / risk if risk > 0 else None
            out['exit_close_to_level_over_planned_stop'] = direction * (executable_level - exit_ref) / risk if risk > 0 else None
        out['eligibility_note'] = 'Historical levels, not proof of unvisited liquidity or future reversal. No trading filter applied.'
        assert out['feature_bars_known_at_ms'] <= t
        assert all(x['known_at_ms'] <= t for x in levels)
        return out
