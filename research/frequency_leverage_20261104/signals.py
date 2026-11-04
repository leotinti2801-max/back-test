"""Same simple V03 rearming, with declared bar length and end-of-session inputs."""
from functools import partial
import pandas as pd


def signals(market, day, tick=0.00001, *, entry_end='14:30', hard_exit='16:00', minutes=5):
    if minutes not in (1, 5) or not '09:00' < entry_end <= hard_exit:
        raise ValueError('Unsupported research session')
    times = [pd.Timestamp(f'{day} {h}', tz='Europe/London').tz_convert('UTC')
             for h in ('08:00', '09:00', entry_end, hard_exit)]
    a, b, end, deadline = [market.idx(int(t.value // 1_000_000)) for t in times]
    session = {'day': str(day), 'deadline_i': deadline}
    def event(i, reason, **extra):
        return {'decision_ms': market.t(i), 'reason': reason, **extra}
    if a < 0 or b > market.n or not market.present[a:b].all():
        return [event(max(0, b), 'RANGE_DATA_INCOMPLETE')], session
    px = market.px
    high, low = float(px['mid_high'][a:b].max()), float(px['mid_low'][a:b].min())
    stops = {1: float(px['bid_low'][a:b].min()) - tick,
             -1: float(px['ask_high'][a:b].max()) + tick}
    events = [event(b, 'RANGE_READY', range_high=high, range_low=low)]
    previous = 0
    for i in range(b + minutes, end, minutes):
        if i > market.n or not market.present[i - minutes:i].all():
            events.append(event(i, 'SIGNAL_DATA_INCOMPLETE_SESSION_CANCELLED'))
            break
        close = float(px['mid_close'][i - 1])
        direction = 1 if close > high else -1 if close < low else 0
        reason = 'INTERIOR_CLOSE_REARMED' if not direction else 'NO_FRESH_CROSS'
        if direction and not previous:
            reason = 'BREAKOUT'
        events.append(event(i, reason, direction=direction, close_mid=close,
                            stop=stops.get(direction), range_high=high, range_low=low))
        previous = direction
    return events, session


def configured(cfg, minutes):
    return partial(signals, entry_end=cfg['entry_end_exclusive'], hard_exit=cfg['hard_exit'], minutes=minutes)
