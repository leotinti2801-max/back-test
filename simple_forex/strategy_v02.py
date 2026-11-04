"""Range breakout, later retest, then entry; no indicator or future prices."""
import pandas as pd


def signals(market, day, tick=0.00001):
    times = [pd.Timestamp(f'{day} {h}', tz='Europe/London').tz_convert('UTC')
             for h in ('08:00', '09:00', '14:30', '16:00')]
    a, b, end, deadline = [market.idx(int(t.value // 1_000_000)) for t in times]
    session = {'day': str(day), 'deadline_i': deadline}
    def event(i, reason, **extra):
        return {'decision_ms': market.t(i), 'reason': reason, **extra}
    if a < 0 or b > market.n:
        return [event(max(0, a), 'SESSION_OUTSIDE_DATA_GRID')], session
    if not market.present[a:b].all():
        return [event(b, 'RANGE_M1_MISSING')], session
    px = market.px
    high, low = float(px['mid_high'][a:b].max()), float(px['mid_low'][a:b].min())
    session.update(range_high=high, range_low=low, range_known_at_ms=market.t(b))
    events = [event(b, 'RANGE_READY', range_high=high, range_low=low)]
    previous = armed = 0
    for i in range(b + 5, end, 5):
        if i > market.n or not market.present[i - 5:i].all():
            events.append(event(i, 'SIGNAL_DATA_INCOMPLETE_SESSION_CANCELLED'))
            break
        close = float(px['mid_close'][i - 1])
        direction = 1 if close > high else -1 if close < low else 0
        stop, reason = None, 'WAIT_FOR_INTERIOR_CLOSE'
        if not direction:
            armed, reason = 0, 'INTERIOR_CLOSE_REARMED'
        elif not previous:
            armed, reason = direction, 'BREAKOUT_ARMED'
        elif direction != previous:
            armed, reason = 0, 'OPPOSITE_SWITCH_WITHOUT_INTERIOR_CLOSE'
        elif armed == direction:
            boundary = high if direction == 1 else low
            touched = px['mid_low'][i - 5:i].min() <= boundary <= px['mid_high'][i - 5:i].max()
            reason = 'WAIT_FOR_RETEST'
            if touched:
                side, field = ('bid', 'low') if direction == 1 else ('ask', 'high')
                values = px[side + '_' + field][i - 5:i]
                stop = float(values.min() if direction == 1 else values.max()) - direction * tick
                armed, reason = 0, 'BREAKOUT'
        events.append(event(i, reason, direction=direction, close_mid=close,
                            stop=stop, range_high=high, range_low=low))
        previous = direction
    return events, session
