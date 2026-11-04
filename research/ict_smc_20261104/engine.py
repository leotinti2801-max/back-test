"""Reuse frozen account/path logic; ICT order replaces only entry/target checks."""
from types import FunctionType
from simple_forex import runner as core
from backtest_bot.reference import X


def order(mk, i, event, params, cfg, balance):
    d, px = event['direction'], mk.px
    bid, ask, fx = (float(px[s + '_open'][i]) for s in ['bid', 'ask', 'mid'])
    fee, slip = params['costs']['fee_round_trip_quote'], params['costs']['slip_quote_per_market_execution']
    entry = (ask if d == 1 else bid) + d * slip
    stop, target = event['stop'], event['structural_target']
    distance, reward = d * (entry - stop), d * (target - entry)
    friction, reasons = ask - bid + fee + 2 * slip, []
    if float(mk.first_ts[i]) - mk.t(i) > cfg['first_tick_max_delay_ms']:
        reasons.append('FIRST_TICK_LATE')
    if not event['fvg_low'] <= fx <= event['fvg_high']:
        reasons.append('ENTRY_QUOTE_OUTSIDE_FVG')
    if distance <= 0:
        reasons.append('STOP_WRONG_SIDE')
    if reward <= 0:
        reasons.append('TARGET_WRONG_SIDE')
    if friction > cfg['friction_max_fraction_of_stop'] * distance:
        reasons.append('FRICTION_TOO_LARGE')
    risk_unit = (distance + fee + slip) / fx
    ratio = (reward - fee) / (distance + fee + slip) if distance > 0 else None
    if ratio is not None and ratio < 2:
        reasons.append('STRUCTURAL_TARGET_BELOW_2R')
    qty = X.size_position(params, risk_unit, balance, fx, entry)[0] if distance > 0 else 0
    if qty < cfg['qty_min_eur']:
        reasons.append('SIZE_BELOW_MINIMUM')
    return {'entry_price': entry, 'stop': stop, 'target': target, 'qty_eur': qty,
        'planned_risk_eur': qty * risk_unit, 'spread': ask - bid, 'friction': friction,
        'planned_net_quote_R': ratio, 'setup_at_entry': event['setup'], 'reasons': reasons}


_simulate = FunctionType(core.simulate.__code__, {**core.simulate.__globals__, 'order': order},
    name='simulate_ict', argdefs=core.simulate.__defaults__, closure=core.simulate.__closure__)
_simulate.__kwdefaults__ = dict(core.simulate.__kwdefaults__) if core.simulate.__kwdefaults__ else None


def simulate(*args, signal_source, **kwargs):
    if signal_source is None:
        raise ValueError('Explicit ICT signals required')
    return _simulate(*args, signal_source=signal_source, **kwargs)
