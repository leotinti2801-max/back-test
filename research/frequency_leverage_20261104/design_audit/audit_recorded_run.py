"""Audit recorded fills and state transitions only; never call a trading simulator.

Read exact cache with the existing SHA/size check and restricted pandas unpickler.
All writes stay in design_audit. Existing reports are never overwritten.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
STUDY = HERE.parent
RUN = STUDY / 'run_01'
sys.path[:0] = [str(REPO), str(REPO / 'src')]
from backtest_bot.data import market_from_cache

MIN = 60000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def ms(value):
    return int(pd.Timestamp(value).value // 1_000_000)


def close(a, b, why, tolerance=1e-7):
    if not math.isclose(float(a), float(b), rel_tol=0, abs_tol=tolerance):
        raise AssertionError(f'{why}: {a} != {b}')


def clock(day, hour):
    return ms(pd.Timestamp(f'{day} {hour}', tz='Europe/London').tz_convert('UTC'))


def audit_cell(folder, variant, period, costs, summary, cfg, market):
    ts, ds = rows(folder / 'TRADES.csv'), rows(folder / 'DECISIONS.csv')
    ss, losses = rows(folder / 'SIZING_AUDIT.csv'), rows(folder / 'LOSSES.csv')
    budget = cfg['risk_budget_per_trade_eur']
    cap, holding = cfg['max_entries_per_day'], variant['max_holding_minutes']
    fee = cfg['fee_round_trip_quote'] * (1.5 if costs == 'higher_costs' else 1)
    slip = cfg['slip_quote_per_market_execution'] * (2 if costs == 'higher_costs' else 1)
    tick, px = cfg['tick_quote'], market.px
    assert summary['halt'] is None, 'Encountered unknown branch; do not audit as a completed period'
    assert len(ts) == summary['closed_trades'] == len(ss)
    assert len(ts) == len({(t['entry_utc'], t['direction']) for t in ts})
    assert dict(Counter(d['reason'] for d in ds)) == summary['event_counts']
    assert len(ts) == sum(d['reason'] == 'ENTERED' for d in ds)
    assert {t['entry_utc'] for t in ts if float(t['net_eur']) < 0} == {t['entry_utc'] for t in losses}
    close(sum(float(t['net_eur']) for t in ts), summary['net_eur'], 'summary net')
    close(summary['net_eur'], summary['known_closed_net_eur'], 'known total')
    assert sum(float(t['net_eur']) > 0 for t in ts) == summary['wins']
    assert sum(float(t['net_eur']) < 0 for t in ts) == summary['losses']
    balance, peak, dd = cfg['capital_eur'], cfg['capital_eur'], 0.0
    daily_entries, daily_risk = Counter(), Counter()
    max_pnl_error = 0.0
    for n, (trade, sizing) in enumerate(zip(ts, ss, strict=True)):
        t, end, direction = ms(trade['entry_utc']), ms(trade['exit_utc']), int(trade['direction'])
        i = market.idx(t)
        reason = trade['exit_reason']
        j = market.idx(end) - (0 if reason == 'TIME' else 1)
        assert ms(period['start']) <= t < end < ms(period['end_exclusive'])
        assert int(trade['closed_at_ms']) == end
        assert trade['day'] == str(pd.Timestamp(t, unit='ms', tz='UTC').tz_convert('Europe/London').date())
        assert clock(trade['day'], '09:00') + variant['signal_minutes'] * MIN <= t < clock(trade['day'], cfg['entry_end_exclusive'])
        assert (t - clock(trade['day'], '09:00')) % (variant['signal_minutes'] * MIN) == 0
        deadline = min(t + holding * MIN, clock(trade['day'], cfg['hard_exit']))
        assert end <= deadline, 'holding/session deadline exceeded'
        if reason == 'TIME':
            assert end == deadline
        if n:
            assert t >= ms(ts[n - 1]['exit_utc']), 'overlapping position'
        assert market.present[i:j + 1].all(), 'closed exposure crosses missing quote'
        assert float(market.first_ts[i]) - t <= cfg['first_tick_max_delay_ms']
        a, b = market.idx(clock(trade['day'], '08:00')), market.idx(clock(trade['day'], '09:00'))
        assert market.present[a:b].all()
        bid, ask, fx = (float(px[s + '_open'][i]) for s in ('bid', 'ask', 'mid'))
        entry = (ask if direction == 1 else bid) + direction * slip
        stop = float(px['bid_low'][a:b].min()) - tick if direction == 1 else float(px['ask_high'][a:b].max()) + tick
        distance = direction * (entry - stop)
        risk_unit = (distance + fee + slip) / fx
        target = entry + direction * (3 * (distance + fee + slip) + fee)
        qty_budget = budget / risk_unit
        qty_leverage = cfg['leverage_max'] * balance * fx / entry
        qty = math.floor(min(qty_budget, qty_leverage) / cfg['qty_step_eur']) * cfg['qty_step_eur']
        planned = qty * risk_unit
        for actual, expected, label in [
            (trade['entry_price'], entry, 'entry'), (trade['stop'], stop, 'stop'),
            (trade['target'], target, 'target'), (trade['qty_eur'], qty, 'quantity'),
            (trade['planned_risk_eur'], planned, 'risk'), (trade['spread'], ask - bid, 'spread'),
            (sizing['entry_fx'], fx, 'entry FX'), (sizing['qty_risk_budget'], qty_budget, 'budget quantity'),
            (sizing['qty_leverage_cap'], qty_leverage, 'leverage quantity'),
            (sizing['qty_executed'], qty, 'sizing quantity'),
            (sizing['balance_before_eur'], balance, 'starting cash')]:
            close(actual, expected, label)
        assert qty >= cfg['qty_min_eur'] and planned <= budget + 1e-8
        assert sizing['leverage_cap_binding_before_rounding'] == str(qty_leverage < qty_budget)
        close(sizing['effective_model_leverage'], qty * entry / fx / balance, 'effective leverage')
        side = 'bid' if direction == 1 else 'ask'
        op, hi, lo = (float(px[side + '_' + field][j]) for field in ('open', 'high', 'low'))
        exit_fx = float(px['mid_open'][j])
        if reason == 'TIME':
            fill = op - direction * slip
        elif reason in ('SL', 'SL_GAP'):
            assert lo <= stop if direction == 1 else hi >= stop
            raw = min(op, stop) if direction == 1 else max(op, stop)
            assert (reason == 'SL_GAP') == (direction * (op - stop) < 0)
            fill = raw - direction * slip
        elif reason == 'TP':
            assert hi >= target + tick if direction == 1 else lo <= target - tick
            fill = target
        else:
            raise AssertionError(f'Unknown exit reason {reason}')
        net = qty * (-0.5 * fee / fx + (direction * (fill - entry) - 0.5 * fee) / exit_fx)
        max_pnl_error = max(max_pnl_error, abs(float(trade['net_eur']) - net))
        close(trade['net_eur'], net, 'recorded fill cash')
        close(trade['R'], net / planned, 'cash R')
        balance += float(trade['net_eur'])
        close(trade['balance_after_eur'], balance, 'balance after')
        peak = max(peak, balance)
        dd = max(dd, peak - balance)
        daily_entries[trade['day']] += 1
        daily_risk[trade['day']] += planned
    close(summary['closed_drawdown_eur'], dd, 'closed drawdown')
    assert max(daily_entries.values(), default=0) <= cap
    assert max(daily_risk.values(), default=0) <= 500 + 1e-8
    assert summary['maximum_executed_entries_per_day'] == max(daily_entries.values(), default=0)

    # Independently follow the written event stream; no new orders or paths generated.
    trade_by_entry = {ms(t['entry_utc']): t for t in ts}
    balance, streak, pause, position = cfg['capital_eur'], 0, 0, None
    day, entries, reserved, previous, last_signal, active_range = None, 0, 0.0, 0, None, None
    closed_count, raw_signals = 0, 0
    for event in ds:
        reason = event['reason']
        if not event.get('decision_ms'):
            continue
        at = int(event['decision_ms'])
        if reason.startswith('TRADE_CLOSED_'):
            assert position is not None and at == ms(position['exit_utc'])
            close(event['net_eur'], position['net_eur'], 'closed event cash')
            assert reason == 'TRADE_CLOSED_' + position['exit_reason']
            net = float(position['net_eur'])
            balance += net
            streak = streak + 1 if net < 0 else 0 if net > 0 else streak
            if streak >= 2:
                pause = at + 24 * 60 * MIN
            position, closed_count = None, closed_count + 1
            continue
        if event['day'] != day:
            day, entries, reserved, previous, last_signal, active_range = event['day'], 0, 0.0, 0, None, None
        if pause and at >= pause:
            pause, streak = 0, 0
        if reason == 'RANGE_READY':
            a, b = market.idx(clock(day, '08:00')), market.idx(clock(day, '09:00'))
            assert at == market.t(b) and market.present[a:b].all()
            active_range = float(px['mid_high'][a:b].max()), float(px['mid_low'][a:b].min())
            close(event['range_high'], active_range[0], 'raw range high')
            close(event['range_low'], active_range[1], 'raw range low')
            last_signal = at
            continue
        if not event.get('close_mid'):
            continue
        assert active_range is not None
        raw_signals += 1
        step = variant['signal_minutes']
        assert at == last_signal + step * MIN
        assert at < clock(day, cfg['entry_end_exclusive'])
        k = market.idx(at)
        assert market.present[k - step:k].all()
        price = float(px['mid_close'][k - 1])
        close(event['close_mid'], price, 'closed confirmation price')
        high, low = active_range
        direction = 1 if price > high else -1 if price < low else 0
        assert int(event['direction']) == direction
        raw_reason = 'INTERIOR_CLOSE_REARMED' if direction == 0 else 'BREAKOUT' if previous == 0 else 'NO_FRESH_CROSS'
        previous, last_signal = direction, at
        if raw_reason != 'BREAKOUT':
            assert reason == raw_reason
            continue
        assert reason in ('ENTERED', 'REFUSED')
        account = []
        if position is not None:
            account.append('POSITION_OPEN')
        if at < pause:
            account.append('PAUSE_AFTER_TWO_LOSSES')
        if entries >= cap:
            account.append('DAILY_ENTRY_LIMIT')
        if reserved + budget > 500 + 1e-8:
            account.append('DAILY_PLANNED_RISK_LIMIT')
        if balance <= 0:
            account.append('NON_POSITIVE_BALANCE')
        recorded = json.loads(event['refusal_reasons']) if event.get('refusal_reasons') else []
        if account:
            assert reason == 'REFUSED' and recorded == account, 'account reasons/state mismatch'
        else:
            assert not set(recorded).intersection({'POSITION_OPEN', 'PAUSE_AFTER_TWO_LOSSES', 'DAILY_ENTRY_LIMIT', 'DAILY_PLANNED_RISK_LIMIT', 'NON_POSITIVE_BALANCE'})
        if reason == 'ENTERED':
            assert position is None and not recorded
            position = trade_by_entry[at]
            assert int(position['direction']) == direction
            close(event['planned_risk_eur'], position['planned_risk_eur'], 'entry event risk')
            reserved += float(position['planned_risk_eur'])
            entries += 1
    assert position is None and closed_count == len(ts)
    return {'status': 'PASS', 'closed_trades': len(ts), 'raw_closed_bar_events': raw_signals,
            'net_eur': summary['net_eur'], 'maximum_recorded_fill_pnl_error_eur': max_pnl_error,
            'maximum_daily_entries': max(daily_entries.values(), default=0),
            'maximum_daily_planned_risk_eur': max(daily_risk.values(), default=0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'FINAL_AUDIT.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(HERE) or output.exists():
        raise ValueError('Use a fresh output file within design_audit')
    freeze = json.loads((RUN / 'FREEZE_BEFORE_RESULTS.json').read_text())
    manifest = json.loads((RUN / 'MANIFEST_SHA256.json').read_text())
    for name, expected in manifest.items():
        assert digest(RUN / name) == expected, name
    source = {**freeze['source_sha256'], **freeze['shared_source_sha256']}
    for name, expected in source.items():
        assert digest(REPO / name) == expected, name
    original_freeze = json.loads((REPO / 'reports/simple_rearmed_v03_01/FREEZE_BEFORE_RESULTS.json').read_text())
    for name, expected in {**original_freeze['new_source_sha256'], **original_freeze['shared_source_sha256']}.items():
        if name in source:
            assert source[name] == expected, f'original frozen core changed: {name}'
    plan = freeze['plan']
    assert plan == json.loads((STUDY / 'PLAN_BEFORE_RESULTS.json').read_text())
    assert len(plan['variants']) == 9
    core_spec = importlib.util.spec_from_file_location('isolated_study_engine_audit', STUDY / 'engine.py')
    core = importlib.util.module_from_spec(core_spec)
    core_spec.loader.exec_module(core)
    assert core._simulate.__code__ is core.frozen.simulate.__code__
    assert core._simulate.__defaults__ == core.frozen.simulate.__defaults__
    assert core._simulate.__kwdefaults__ == core.frozen.simulate.__kwdefaults__
    assert core._simulate.__globals__ is not core.frozen.simulate.__globals__
    assert [k for k in core._simulate.__globals__ if core._simulate.__globals__[k] is not core.frozen.simulate.__globals__[k]] == ['parameters']
    assert core.frozen.simulate.__globals__['parameters'] is core.frozen.parameters
    market, quality = market_from_cache(REPO / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl')
    original = json.loads((REPO / 'simple_forex/protocol_v03.json').read_text())
    results = json.loads((RUN / 'RESULTS.json').read_text())['variants']
    cells, failures = {}, []
    for variant in plan['variants']:
        cfg = {**original, **variant['overrides']}
        for period in [plan['common_period'], *plan['diagnostic_attempts']]:
            for costs in ('base', 'higher_costs'):
                key = f"{variant['name']}/{period['name']}/{costs}"
                try:
                    cells[key] = audit_cell(RUN / key, variant, period, costs,
                                           results[variant['name']][period['name']][costs], cfg, market)
                except (AssertionError, KeyError, ValueError) as exc:
                    failures.append({'cell': key, 'error': str(exc)})
    parity = []
    for period in [plan['common_period'], *plan['diagnostic_attempts']]:
        for costs in ('base', 'higher_costs'):
            for arm in ('LEVERAGE30', 'LEVERAGE100'):
                for name in ('TRADES.csv', 'DECISIONS.csv', 'LIQUIDATION_ENVELOPES.csv', 'LOSSES.csv'):
                    assert (RUN / arm / period['name'] / costs / name).read_bytes() == (RUN / 'V03' / period['name'] / costs / name).read_bytes(), (arm, period['name'], costs, name)
                parity.append(f"{arm}/{period['name']}/{costs}")
    for costs in ('base', 'higher_costs'):
        for name in ('TRADES', 'DECISIONS'):
            old = REPO / 'research/indicator_study_20261104/lab/comparison_01' / f'V03_{costs}_{name}.csv'
            assert (RUN / 'V03/Q1' / costs / f'{name}.csv').read_bytes() == old.read_bytes()
    report = {'audit': 'INDEPENDENT_RECORDED_RUN_CHECK_20261104',
              'status': 'PASS' if not failures and len(cells) == 72 else 'FAIL',
              'audit_script_sha256': digest(Path(__file__)), 'run_manifest_sha256': digest(RUN / 'MANIFEST_SHA256.json'),
              'result_files_verified': len(manifest), 'source_identities_verified': len(source),
              'frozen_original_core_unchanged': True, 'function_clone_isolated': True,
              'baseline_Q1_trade_and_decision_bytes_reproduced': True,
              'leverage_financial_byte_parity_cells': parity,
              'cells_passed': len(cells), 'closed_trade_rows_audited_correlated': sum(c['closed_trades'] for c in cells.values()),
              'cells': cells, 'failures': failures,
              'method': 'Existing CSV state transitions and recorded fills recomputed from source quotes; no new order, trading simulator or market backtest called',
              'limits': ['72 correlated development cells, not independent samples',
                         'No tick path or FTMO compliance certified',
                         'Recorded exit fills audited; no counterfactual stop/TP path generated',
                         'No unknown exposure encountered in the72 recorded cells; preservation also inspected in frozen exception branch',
                         'Six source tests reviewed, not rerun by this audit'],
              'new_financial_backtest': False, 'active_sources_modified': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'cells_passed', 'closed_trade_rows_audited_correlated', 'failures')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
