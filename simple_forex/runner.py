"""Paper research only. Costs, accounting and journals stay outside the signal."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from backtest_bot.data import market_from_cache
from backtest_bot.reference import D, ROOT, X, ExecutionPathUnknown
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from simple_forex.strategy import signals

HERE = Path(__file__).resolve().parent


def parameters(reference, cfg, deadline_ms, stress):
    p = copy.deepcopy(reference)
    p['account'].update(capital_eur=cfg['capital_eur'],
                        risk_budget_eur_per_position=cfg['risk_budget_per_trade_eur'],
                        qty_step_eur=cfg['qty_step_eur'], qty_min_eur=cfg['qty_min_eur'],
                        leverage_max=cfg['leverage_max'])
    p['exit'].update(max_holding_minutes=1440,
                     hard_exit_utc_minute=int(deadline_ms % D.DAY_MS // D.MIN_MS))
    p['costs'].update(fee_round_trip_quote=cfg['fee_round_trip_quote'] * (1.5 if stress else 1),
                      slip_quote_per_market_execution=cfg['slip_quote_per_market_execution'] * (2 if stress else 1),
                      tick_quote=cfg['tick_quote'])
    return p


def order(mk, i, event, params, cfg, balance):
    d, px = event['direction'], mk.px
    bid, ask, fx = (float(px[s + '_open'][i]) for s in ('bid', 'ask', 'mid'))
    fee, slip = params['costs']['fee_round_trip_quote'], params['costs']['slip_quote_per_market_execution']
    entry = (ask if d == 1 else bid) + d * slip
    distance = d * (entry - event['stop'])
    friction = ask - bid + fee + 2 * slip
    reasons = []
    if float(mk.first_ts[i]) - mk.t(i) > cfg['first_tick_max_delay_ms']:
        reasons.append('FIRST_TICK_LATE')
    boundary = event['range_high'] if d == 1 else event['range_low']
    if d * (fx - boundary) <= 0:
        reasons.append('ENTRY_NO_LONGER_BEYOND_RANGE')
    if distance <= 0:
        reasons.append('STOP_WRONG_SIDE')
    if friction > cfg['friction_max_fraction_of_stop'] * distance:
        reasons.append('FRICTION_TOO_LARGE')
    risk_unit = (distance + fee + slip) / fx
    qty = X.size_position(params, risk_unit, balance, fx, entry)[0] if distance > 0 else 0
    if qty < cfg['qty_min_eur']:
        reasons.append('SIZE_BELOW_MINIMUM')
    target = entry + d * (cfg['planned_quote_reward_risk'] * (distance + fee + slip) + fee)
    return {'entry_price': entry, 'stop': event['stop'], 'target': target, 'qty_eur': qty,
            'planned_risk_eur': qty * risk_unit, 'spread': ask - bid,
            'friction': friction, 'reasons': reasons}


def close_position(pos, state, trades, events, cfg):
    state['balance'] += pos['net_eur']
    pos['balance_after_eur'] = state['balance']
    trades.append(pos)
    state['losses'] = state['losses'] + 1 if pos['net_eur'] < 0 else 0 if pos['net_eur'] > 0 else state['losses']
    if state['losses'] >= cfg['pause_after_consecutive_losses']:
        state['pause_until'] = pos['closed_at_ms'] + cfg['pause_hours'] * 60 * D.MIN_MS
    events.append({'day': pos['day'], 'decision_ms': pos['closed_at_ms'],
                   'reason': 'TRADE_CLOSED_' + pos['exit_reason'], 'net_eur': pos['net_eur']})


def simulate(mk, cfg, reference, start_ms, end_ms, stress=False, signal_source=None):
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
            if not reasons and (i >= mk.n or not mk.present[i]):
                state['halt'] = {'reason': 'ENTRY_QUOTE_MISSING', 'at_utc': D.iso(t)}
                events.append({**event, 'reason': 'ENTRY_UNKNOWN'})
                break
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
    return summary, trades, events, envelopes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--protocol', type=Path, default=HERE / 'protocol_v01.json')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    cfg = json.loads(args.protocol.read_text())
    selected_signal = signals
    if cfg.get('signal_source') == 'rearmed':
        from simple_forex.strategy_rearmed import signals as selected_signal
    elif cfg.get('signal_source', 'v01') != 'v01':
        raise ValueError('Unsupported signal source')
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    source = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [*sorted(HERE.glob('*.py')), args.protocol.resolve()]}
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {'protocol': cfg, 'new_source_sha256': source,
                'shared_source_sha256': code_identity(), 'live_trading_enabled': False})
    mk, quality = market_from_cache(args.cache)
    results = {}
    for period in cfg['historical_periods']:
        results[period['name']] = {}
        for label, stress in [('base', False), ('higher_costs', True)]:
            summary, trades, events, envelopes = simulate(mk, cfg, reference, epoch_ms(period['start']),
                                                         epoch_ms(period['end_exclusive']), stress,
                                                         signal_source=selected_signal)
            summary['observed_closed_win_rate'] = summary['wins'] / summary['closed_trades'] if summary['closed_trades'] else None
            prefix = period['name'] + '_' + label
            results[period['name']][label] = summary
            write_csv(args.output / (prefix + '_TRADES.csv'), trades)
            write_csv(args.output / (prefix + '_DECISIONS.csv'), events)
            write_csv(args.output / (prefix + '_LIQUIDATION_ENVELOPES.csv'), envelopes)
            print(prefix, 'closed', summary['closed_trades'], 'net', summary['net_eur'], 'halt', summary['halt'], flush=True)
    write_json(args.output / 'RESULTS.json', {'strategy': cfg['version'], 'periods': results,
                'cache_quality': quality, 'independent_validation': False, 'FTMO_pass_claimed': False})
    for name, digest in source.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Source changed during calculation')
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.iterdir()) if p.is_file()})


if __name__ == '__main__':
    main()
