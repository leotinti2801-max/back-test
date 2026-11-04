"""Single causal ICT price-pattern hypothesis; explicit state journal, no broker."""
import importlib.util
import numpy as np
import pandas as pd
from backtest_bot.reference import D, ROOT


def indicator_library():
    path = ROOT / 'research/indicator_study_20261104/lab/features.py'
    spec = importlib.util.spec_from_file_location('ict_indicator_reference', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ICT:
    def __init__(self, market):
        self.market = market
        self.bars = D.make_bars(market, 5, 'M5')
        self.values = indicator_library().indicators(self.bars)
        self.pivots = D.find_pivots(self.bars)

    def signals(self, mk, day, tick=0.00001):
        times = [pd.Timestamp(f'{day} {h}', tz='Europe/London').tz_convert('UTC')
                 for h in ['08:00', '09:00', '14:30', '16:00']]
        a, b, end, deadline = [mk.idx(int(t.value // 1_000_000)) for t in times]
        session = {'day': str(day), 'deadline_i': deadline}
        def event(i, reason, **extra):
            return {'decision_ms': mk.t(i), 'reason': reason, **extra}
        if a < 0 or b > mk.n or not mk.present[a:b].all():
            return [event(max(b, 0), 'RANGE_DATA_INCOMPLETE')], session
        px, bars = mk.px, self.bars
        high, low = float(px['mid_high'][a:b].max()), float(px['mid_low'][a:b].min())
        targets = {1: float(px['bid_high'][a:b].max()), -1: float(px['ask_low'][a:b].min())}
        events, pending = [event(b, 'RANGE_READY', range_high=high, range_low=low)], None
        for i in range(b + 5, end, 5):
            s = bars.slot_of_close(mk.t(i))
            if i > mk.n or not bars.complete[s]:
                events.append(event(i, 'SIGNAL_GAP_SESSION_CANCELLED', setup=pending))
                pending = None
                break
            close = float(bars.close[s])
            if pending:
                p, d = pending, pending['direction']
                field = 'bid_low' if d == 1 else 'ask_high'
                touched = np.any(d * (px[field][i - 5:i] - p['stop']) <= 0)
                limit = p['sweep_slot'] + 6 if p['stage'] == 'MSS' else p['mss_slot'] + 6
                if touched or s > limit:
                    events.append(event(i, 'SETUP_STOP_INVALIDATED' if touched else 'SETUP_EXPIRED_' + p['stage'], setup=dict(p)))
                    pending = None
                    continue
                if p['stage'] == 'MSS':
                    if d * (close - p['mss_level']) <= 0:
                        events.append(event(i, 'WAIT_MSS', setup=dict(p)))
                        continue
                    atr = self.values['atr14'][s - 1]
                    gap_low, gap_high = ((float(bars.high[s - 2]), float(bars.low[s])) if d == 1
                        else (float(bars.high[s]), float(bars.low[s - 2])))
                    failures = []
                    if not np.isfinite(atr):
                        failures.append('ATR_PREVIOUS_UNKNOWN')
                    elif d * (close - float(bars.open[s])) <= 0:
                        failures.append('DISPLACEMENT_NON_DIRECTIONAL')
                    elif d * (close - float(bars.open[s])) < atr:
                        failures.append('DISPLACEMENT_BELOW_PREVIOUS_ATR')
                    if not bars.complete[s - 2:s + 1].all() or gap_high - gap_low < tick - 1e-12:
                        failures.append('NO_DIRECTIONAL_FVG')
                    if failures:
                        events.append(event(i, 'FIRST_MSS_REJECTED', rejection_reasons=failures, setup=dict(p)))
                        pending = None
                        continue
                    opposite = [k for k in range(max(0, s - 5), s) if bars.complete[k]
                                and d * (bars.close[k] - bars.open[k]) < 0]
                    ob = ({'slot': opposite[-1], 'low': float(bars.low[opposite[-1]]),
                           'high': float(bars.high[opposite[-1]]), 'known_at_ms': mk.t(i)} if opposite else None)
                    p.update(stage='RETURN', mss_slot=s, mss_known_at_ms=mk.t(i), fvg_low=gap_low,
                        fvg_high=gap_high, atr_previous=float(atr), order_block=ob)
                    events.append(event(i, 'MSS_FVG_CONFIRMED', setup=dict(p)))
                    continue
                invalid_gap = close < p['fvg_low'] if d == 1 else close > p['fvg_high']
                if invalid_gap:
                    events.append(event(i, 'FVG_INVALIDATED', setup=dict(p)))
                    pending = None
                    continue
                if p['fvg_low'] <= close <= p['fvg_high']:
                    events.append(event(i, 'BREAKOUT', direction=d, stop=p['stop'],
                        structural_target=targets[d], fvg_low=p['fvg_low'], fvg_high=p['fvg_high'], setup=dict(p)))
                    pending = None
                else:
                    events.append(event(i, 'WAIT_FVG_RETURN', setup=dict(p)))
                continue
            swept_high = bars.high[s] >= high + tick - 1e-12
            swept_low = bars.low[s] <= low - tick + 1e-12
            if swept_high and swept_low:
                events.append(event(i, 'SWEEP_BOTH_SIDES_AMBIGUOUS'))
                continue
            if not low < close < high or not (swept_high or swept_low):
                events.append(event(i, 'NO_VALID_SWEEP'))
                continue
            d = -1 if swept_high else 1
            eligible = [p for p in self.pivots if p.kind == ('HIGH' if d == 1 else 'LOW')
                        and s - 12 <= p.center <= s and p.known_at_ms <= mk.t(i)
                        and d * (p.price - close) > 0]
            if not eligible:
                events.append(event(i, 'SWEEP_NO_CONFIRMED_MSS_LEVEL', direction=d))
                continue
            pivot = max(eligible, key=lambda p: p.known_at_ms)
            pending = {'stage': 'MSS', 'direction': d, 'sweep_slot': s, 'sweep_known_at_ms': mk.t(i),
                'mss_pivot_id': pivot.pid, 'mss_level': pivot.price, 'mss_pivot_known_at_ms': pivot.known_at_ms,
                'stop': float(bars.bid_low[s] - tick if d == 1 else bars.ask_high[s] + tick),
                'range_high': high, 'range_low': low, 'structural_target': targets[d]}
            events.append(event(i, 'SWEEP_CONFIRMED', setup=dict(pending)))
        if pending:
            events.append(event(end, 'SETUP_EXPIRED_SESSION_END', setup=dict(pending)))
        return events, session
