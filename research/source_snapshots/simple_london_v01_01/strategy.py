"""EURUSD: London opening-range breakout. Closed prices only, no indicator."""
import pandas as pd


def signals(market, day, tick=0.00001):
    hours = ('08:00', '09:00', '12:00', '16:00')
    times = [pd.Timestamp(f'{day} {h}', tz='Europe/London').tz_convert('UTC') for h in hours]
    a, b, end, deadline = [market.idx(int(t.value // 1_000_000)) for t in times]
    session = {'day': str(day), 'deadline_i': deadline}
    def event(i, reason, **extra):
        return {'decision_ms': market.t(i), 'reason': reason, **extra}
    if a < 0 or deadline >= market.n:
        return [event(max(0, a), 'SESSION_OUTSIDE_DATA_GRID')], session
    if not market.present[a:b].all():
        missing = int((~market.present[a:b]).sum())
        return [event(b, 'RANGE_M1_MISSING', missing_minutes=missing)], session
    px = market.px
    high = float(px['mid_high'][a:b].max())
    low = float(px['mid_low'][a:b].min())
    stops = {1: float(px['bid_low'][a:b].min()) - tick,
             -1: float(px['ask_high'][a:b].max()) + tick}
    session.update(range_high=high, range_low=low, range_known_at_ms=market.t(b))
    events = [event(b, 'RANGE_READY', range_high=high, range_low=low)]
    attempted = set()
    for i in range(b + 5, end, 5):
        if not market.present[i - 5:i].all():
            events.append(event(i, 'SIGNAL_M5_INCOMPLETE_SESSION_CANCELLED'))
            break
        close = float(px['mid_close'][i - 1])
        direction = 1 if close > high else -1 if close < low else 0
        reason = 'NO_BREAKOUT' if not direction else 'DIRECTION_ALREADY_CONSUMED'
        if direction and direction not in attempted:
            attempted.add(direction)
            reason = 'BREAKOUT'
        events.append(event(i, reason, direction=direction, close_mid=close,
                            stop=stops.get(direction), range_high=high, range_low=low))
    return events, session
