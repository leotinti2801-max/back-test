"""Session replay with explicit unknowns and conservative M1 execution.

Continuous runs stop on a potentially hidden entry or an unresolved position.
Separate independent-day experiments are diagnostic, never a replacement equity.
"""
from collections import Counter
from dataclasses import dataclass, field

from .reference import B, D, E, X, ExecutionPathUnknown
from .strategy import create_pending, entry_check


@dataclass
class Ledger:
    capital: float
    balance: float
    trades: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    losses: int = 0
    pause_end_ms: int = 0
    halt: dict | None = None
    cancelled_on_gap: int = 0


def allowed_time(t, controls):
    minute = t % D.DAY_MS // D.MIN_MS
    if not controls['entry_start_utc_minute'] <= minute < controls['entry_end_utc_minute']:
        return False
    paris, _ = E.paris_minute(t)
    return not controls['no_entry_paris_start_minute'] <= paris < controls['no_entry_paris_end_minute']


def session(ctx, params, candidate, controls, day, ledger, bos_by_close):
    mk = ctx.market
    setup = position = None
    entered = False
    start = day + controls['entry_start_utc_minute'] * D.MIN_MS
    end = day + controls['hard_exit_utc_minute'] * D.MIN_MS
    for t in range(start, end + D.MIN_MS, D.MIN_MS):
        if position is not None and t >= position['closed_at_ms']:
            ledger.balance += position['net_eur']
            position['balance_after_eur'] = ledger.balance
            ledger.trades.append(position)
            if position['net_eur'] < 0:
                ledger.losses += 1
            elif position['net_eur'] > 0:
                ledger.losses = 0
            if ledger.losses >= 2:
                ledger.pause_end_ms = t + controls['pause_hours_after_two_losses'] * 60 * D.MIN_MS
                ledger.counts['PAUSE_AFTER_TWO_LOSSES'] += 1
                setup = None
            position = None
        if ledger.pause_end_ms and t >= ledger.pause_end_ms:
            ledger.pause_end_ms = 0
            ledger.losses = 0
        if ledger.balance <= 0:
            ledger.halt = {'reason': 'NON_POSITIVE_EQUITY', 'at_utc': D.iso(t), 'uncertain': False}
            return
        # At most one entry a day; the position's outcome is only booked at its close.
        if position is not None or entered or t == end or t < ledger.pause_end_ms:
            continue
        state = ctx.bias.state_at(t)
        if setup is not None and (t >= setup.expiry_ms or state != B.DIRECTION_STATE[setup.direction]):
            ledger.counts['SETUP_EXPIRED_OR_BIAS_CHANGED'] += 1
            setup = None
        i = mk.idx(t) - 1
        if setup is not None and t - D.MIN_MS >= setup.created_ms:
            d = setup.direction
            if not mk.present[i]:
                # Do not discard a possible trade just because its data are missing.
                if allowed_time(t, controls):
                    ledger.halt = {'reason': 'MISSING_M1_MAY_HIDE_ENTRY', 'at_utc': D.iso(t),
                                   'setup_id': setup.setup_id, 'uncertain': True}
                    return
                ledger.cancelled_on_gap += 1
                setup = None
            else:
                tick = params['costs']['tick_quote']
                if setup.target is not None and (
                        mk.px['bid_high'][i] >= setup.target + tick if d == 1
                        else mk.px['ask_low'][i] <= setup.target - tick):
                    ledger.counts['TARGET_REVISITED_BEFORE_ENTRY'] += 1
                    setup = None
                elif mk.px['mid_low'][i] <= setup.zone_hi and mk.px['mid_high'][i] >= setup.zone_lo:
                    current, setup = setup, None  # First return is consumed on every refusal.
                    reasons = []
                    if not allowed_time(t, controls):
                        reasons.append('OUTSIDE_ENTRY_WINDOW')
                    if not current.zone_lo <= mk.px['mid_close'][i] <= current.zone_hi:
                        reasons.append('RETURN_CLOSED_OUTSIDE_ZONE')
                    e = i + 1
                    decision = {'setup_id': current.setup_id, 'decision_utc': D.iso(t),
                                'return_open_utc': D.iso(t - D.MIN_MS), 'direction': d}
                    if not reasons and (e >= mk.n or not mk.present[e]):
                        ledger.halt = {'reason': 'ENTRY_QUOTE_MISSING', 'at_utc': D.iso(t),
                                       'setup_id': current.setup_id, 'uncertain': True}
                        return
                    if not reasons:
                        checks = entry_check(mk, e, current, params, candidate, ledger.balance)
                        reasons.extend(checks['reasons'])
                        decision.update({k: v for k, v in checks.items() if k != 'reasons'})
                    decision['reasons'] = reasons
                    decision['outcome'] = reasons[0] if reasons else 'ENTERED'
                    ledger.decisions.append(decision)
                    ledger.counts['DECISION_' + decision['outcome']] += 1
                    if not reasons:
                        qty = checks['qty']
                        try:
                            path = X.structural_path(mk, e, d, current.stop, current.target, params)
                        except ExecutionPathUnknown as exc:
                            ledger.halt = {'reason': 'UNRESOLVED_EXECUTION', 'at_utc': D.iso(t),
                                           'setup_id': current.setup_id, 'uncertain': True,
                                           'qty_eur': qty, 'details': exc.event,
                                           'known_partial_cash_eur': qty * exc.event.get('known_realized_per_unit', 0)}
                            return
                        position = {
                            'setup_id': current.setup_id, 'entry_utc': D.iso(t), 'direction': d,
                            'closed_at_ms': path['closed_at_ms'], 'exit_utc': D.iso(path['closed_at_ms']),
                            'entry_price': path['entry_price'], 'stop': current.stop, 'target': current.target,
                            'target_known_at_utc': D.iso(current.target_known_at_ms),
                            'qty_eur': qty, 'planned_risk_eur': checks['planned_risk_eur'],
                            'net_eur': qty * path['net_unit'],
                            'R': qty * path['net_unit'] / checks['planned_risk_eur'],
                            'exit_reason': path['reason'],
                            'ambiguous_stop_and_target': path['ambiguous_stop_and_target_same_m1'],
                            'commission_eur': qty * path['flow_summary_per_unit']['commission_eur'],
                            'slippage_eur': qty * path['flow_summary_per_unit']['slippage_eur'],
                        }
                        entered = True
        # Minute-close decisions precede creation of a new M30 setup at that close.
        if t % D.M30_MS == 0 and not entered and t >= ledger.pause_end_ms:
            if setup is not None:
                bar = ctx.m30.slot_of_close(t)
                if ctx.m30.complete[bar]:
                    close = ctx.m30.close[bar]
                    if close < setup.zone_lo if setup.direction == 1 else close > setup.zone_hi:
                        ledger.counts['ZONE_INVALIDATED'] += 1
                        setup = None
            for event in bos_by_close.get(t, ()):
                ledger.counts['BOS_OBSERVED'] += 1
                if event.static_reasons:
                    ledger.counts.update('BOS_REFUSED_' + r for r in event.static_reasons)
                    continue
                new = create_pending(ctx, event, candidate, params)
                if new is None:
                    ledger.counts['NO_PREKNOWN_TARGET'] += 1
                    continue
                setup = new
                ledger.counts['SETUP_CREATED'] += 1
    if position is not None:
        raise AssertionError('The hard exit must close every known position within the session')


def metrics(ledger):
    pnls = [t['net_eur'] for t in ledger.trades]
    gross_profit = sum(max(0, n) for n in pnls)
    gross_loss = -sum(min(0, n) for n in pnls)
    equity = peak = ledger.capital
    drawdown = 0.0
    for n in pnls:
        equity += n
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    unknown = ledger.halt is not None and ledger.halt.get('uncertain', False)
    return {
        'closed_trades': len(pnls), 'wins': sum(n > 0 for n in pnls),
        'losses': sum(n < 0 for n in pnls),
        'win_rate': sum(n > 0 for n in pnls) / len(pnls) if pnls else None,
        'net_eur': None if unknown else sum(pnls),
        'known_closed_net_eur': sum(pnls),
        'profit_factor': gross_profit / gross_loss if gross_loss else None,
        'gross_profit_eur': gross_profit, 'gross_loss_eur': gross_loss,
        'closed_drawdown_eur': drawdown, 'mean_R': sum(t['R'] for t in ledger.trades) / len(pnls) if pnls else None,
        'commission_eur': sum(t['commission_eur'] for t in ledger.trades),
        'slippage_eur': sum(t['slippage_eur'] for t in ledger.trades),
        'cancelled_on_gap_outside_entry_window': ledger.cancelled_on_gap,
        'halt': ledger.halt, 'counts': dict(ledger.counts),
        'coverage': 'PARTIAL_UNRESOLVED_ACTIVE_STATE' if unknown else 'OBSERVED_STREAM_ONLY',
        'market_period_certified': False,
    }


def run_period(ctx, params, candidate, controls, start_ms, end_ms, independent_days=False):
    events = {}
    for event in ctx.bos:
        if start_ms <= event.close_ms < end_ms:
            events.setdefault(event.close_ms, []).append(event)
    ledger = Ledger(controls['capital_eur'], controls['capital_eur'])
    if independent_days:
        days = []
        trades, decisions = [], []
        for day in range(start_ms, end_ms, D.DAY_MS):
            daily = Ledger(controls['capital_eur'], controls['capital_eur'])
            session(ctx, params, candidate, controls, day, daily, events)
            days.append({'date_utc': D.iso(day)[:10], **metrics(daily)})
            trades.extend(daily.trades)
            decisions.extend(daily.decisions)
        return {
            'mode': 'INDEPENDENT_DAILY_DIAGNOSTICS_NO_PORTFOLIO_OR_CROSS_DAY_PAUSE',
            'days': days, 'closed_trades': len(trades),
            'unknown_days': sum(d['halt'] is not None for d in days),
            'known_trial_net_eur': sum(t['net_eur'] for t in trades),
            'portfolio_net_eur': None,
            'warning': 'Known trials are a conditional subset, not an annual equity or return estimate',
        }, trades, decisions
    for day in range(start_ms, end_ms, D.DAY_MS):
        session(ctx, params, candidate, controls, day, ledger, events)
        if ledger.halt:
            break
    return metrics(ledger), ledger.trades, ledger.decisions
