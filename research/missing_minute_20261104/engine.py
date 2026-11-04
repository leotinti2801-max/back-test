"""Local copy of frozen simulate; changes restricted to R3 and gap journal. See PROVENANCE.json."""
from collections import Counter
from types import SimpleNamespace
import pandas as pd
from backtest_bot.reference import D, ExecutionPathUnknown
from simple_forex.runner import parameters, order, close_position
from simple_forex.strategy_rearmed import signals
from path import structural_path

def simulate(mk, cfg, reference, start_ms, end_ms, stress=False, signal_source=None, *, scenario='S_CONT'):
    gap_log = []
    X = SimpleNamespace(structural_path=lambda *a: structural_path(*a, scenario=scenario, gap_sink=gap_log))
    state = {'balance': cfg['capital_eur'], 'losses': 0, 'pause_until': 0, 'halt': None}
    trades, events, envelopes = [], [], []
    dates = pd.date_range(pd.Timestamp(start_ms, unit='ms', tz='UTC'),
                          pd.Timestamp(end_ms, unit='ms', tz='UTC'), inclusive='left', freq='D')
    for date in dates:
        if state['halt']:
            break
        day = date.date()
        if date.weekday() >= 5:
            events.append({'day': str(day), 'reason': 'WEEKEND_NO_SESSION'})
            continue
        raw, session = (signal_source or signals)(mk, day, cfg['tick_quote'])
        params = parameters(reference, cfg, mk.t(session['deadline_i']), stress)
        position, daily_risk, attempts, entries = None, 0.0, 0, 0
        for signal_index, signal in enumerate(raw):
            event = {'day': str(day), **signal}
            t = signal['decision_ms']
            if position and position['closed_at_ms'] <= t:
                close_position(position, state, trades, events, cfg)
                position = None
            if state['pause_until'] and t >= state['pause_until']:
                state.update(losses=0, pause_until=0)
            if signal['reason'] != 'BREAKOUT':
                events.append(event)
                continue
            attempts += 1
            reasons = []
            if position:
                reasons.append('POSITION_OPEN')
            if t < state['pause_until']:
                reasons.append('PAUSE_AFTER_TWO_LOSSES')
            if cfg.get('max_attempts_per_day') is not None and attempts > cfg['max_attempts_per_day']:
                reasons.append('DAILY_ATTEMPT_LIMIT')
            if cfg.get('max_entries_per_day') is not None and entries >= cfg['max_entries_per_day']:
                reasons.append('DAILY_ENTRY_LIMIT')
            if daily_risk + cfg['risk_budget_per_trade_eur'] > cfg['max_planned_daily_risk_eur'] + 1e-8:
                reasons.append('DAILY_PLANNED_RISK_LIMIT')
            if state['balance'] <= 0:
                reasons.append('NON_POSITIVE_BALANCE')
            i = mk.idx(t)
            if i < 0 or i >= mk.n or not mk.present[i]:
                reasons.append('ENTRY_QUOTE_MISSING_REFUSED')
            if not reasons:
                check = order(mk, i, signal, params, cfg, state['balance'])
                reasons = check['reasons']
                event.update(check)
            event.update(reason='REFUSED' if reasons else 'ENTERED', refusal_reasons=reasons)
            events.append(event)
            if reasons:
                continue
            qty = check['qty_eur']
            try:
                path = X.structural_path(mk, i, signal['direction'], check['stop'], check['target'], params)
            except ExecutionPathUnknown as exc:
                missing_ms = exc.event['first_unobserved_minute_ms']
                state['halt'] = {'reason': 'UNRESOLVED_EXECUTION', 'at_utc': D.iso(missing_ms),
                                 'entry_at_utc': D.iso(t),
                                 'details': exc.event, 'known_partial_cash_eur': qty * exc.event['known_realized_per_unit']}
                for observed in raw[signal_index + 1:]:
                    if observed['decision_ms'] >= missing_ms:
                        break
                    row = {'day': str(day), **observed}
                    if observed['reason'] == 'BREAKOUT':
                        row.update(reason='REFUSED', refusal_reasons=['POSITION_OPEN'])
                    events.append(row)
                events.append({'day': str(day), 'decision_ms': missing_ms, 'reason': 'UNRESOLVED_EXECUTION'})
                break
            position = {'day': str(day), 'entry_utc': D.iso(t), 'exit_utc': D.iso(path['closed_at_ms']),
                        'closed_at_ms': path['closed_at_ms'], 'direction': signal['direction'],
                        **{k: v for k, v in check.items() if k != 'reasons'},
                        'net_eur': qty * path['net_unit'],
                        'R': qty * path['net_unit'] / check['planned_risk_eur'],
                        'exit_reason': path['reason'], 'ambiguous_stop_and_target': path['ambiguous_stop_and_target_same_m1']}
            daily_risk += check['planned_risk_eur']
            entries += 1
            for at, low, high, mark in zip(path['t'], path['worst'], path['best'], path['mark'], strict=True):
                envelopes.append({'entry_utc': D.iso(t), 't_utc': D.iso(at),
                                  'liquidation_low_eur': state['balance'] + qty * low,
                                  'liquidation_high_eur': state['balance'] + qty * high,
                                  'liquidation_mark_eur': state['balance'] + qty * mark})
        if position:
            close_position(position, state, trades, events, cfg)
    pnls = [r['net_eur'] for r in trades]
    equity = peak = cfg['capital_eur']
    drawdown = 0.0
    for net in pnls:
        equity += net
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    gains, losses = sum(max(0, n) for n in pnls), -sum(min(0, n) for n in pnls)
    summary = {'closed_trades': len(trades), 'wins': sum(n > 0 for n in pnls),
               'losses': sum(n < 0 for n in pnls), 'known_closed_net_eur': sum(pnls),
               'net_eur': None if state['halt'] else sum(pnls),
               'profit_factor': gains / losses if losses else None, 'closed_drawdown_eur': drawdown,
               'halt': state['halt'], 'event_counts': dict(Counter(e['reason'] for e in events)),
               'full_market_period_certified': False, 'FTMO_compliance_verified': False,
               'equity_warning': 'M1 hypothetical liquidation envelopes include exit costs; not contractual FTMO equity.'}
    return summary, trades, events, envelopes, gap_log
