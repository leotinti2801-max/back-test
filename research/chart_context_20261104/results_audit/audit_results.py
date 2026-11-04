"""Read recorded context/continuation outputs and source quotes; no path simulator.

No call to continue_trade, structural_path, order or any portfolio simulator.
Only existing fills, feature timestamps and declared continuation rows are audited.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import talib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
STUDY, RUN = HERE.parent, HERE.parent / 'run_01'
sys.path[:0] = [str(REPO), str(REPO / 'src')]
from backtest_bot.data import market_from_cache
from backtest_bot.reference import D


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def ms(stamp):
    return int(pd.Timestamp(stamp).value // 1_000_000)


def close(a, b, name, tolerance=1e-7):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=tolerance), (name, a, b)


def stamp(day, hour):
    return ms(pd.Timestamp(f'{day} {hour}', tz='Europe/London'))


def costs_of(cfg, scenario):
    return (cfg['fee_round_trip_quote'] * (1.5 if scenario == 'higher_costs' else 1),
            cfg['slip_quote_per_market_execution'] * (2 if scenario == 'higher_costs' else 1))


def audit_fills(trades, decisions, cfg, summary, market, target_r):
    fee, slip = costs_of(cfg, summary['audit_cost_scenario'])
    qty_step, budget, tick = cfg['qty_step_eur'], cfg['risk_budget_per_trade_eur'], cfg['tick_quote']
    balance, pause, streak, max_error = cfg['capital_eur'], 0, 0, 0.0
    daily, risk = Counter(), Counter()
    for n, t in enumerate(trades):
        at, end, d = ms(t['entry_utc']), ms(t['exit_utc']), int(t['direction'])
        i, j = market.idx(at), market.idx(end) - (t['exit_reason'] != 'TIME')
        assert stamp(t['day'], '09:05') <= at < stamp(t['day'], '14:30')
        assert at % (5 * D.MIN_MS) == 0 and end <= stamp(t['day'], '16:00')
        assert market.present[i:j + 1].all()
        if n:
            assert at >= ms(trades[n - 1]['exit_utc'])
        if pause and at >= pause:
            pause, streak = 0, 0
        assert at >= pause, 'pause violation'
        bid, ask, fx = (float(market.px[s + '_open'][i]) for s in ('bid', 'ask', 'mid'))
        entry = (ask if d == 1 else bid) + d * slip
        stop = float(t['stop'])
        distance = d * (entry - stop)
        unit_risk = (distance + fee + slip) / fx
        target = entry + d * (target_r * (distance + fee + slip) + fee)
        qty = math.floor(min(budget / unit_risk, cfg['leverage_max'] * balance * fx / entry) / qty_step) * qty_step
        planned = qty * unit_risk
        close(t['entry_price'], entry, 'entry')
        close(t['target'], target, 'target')
        close(t['qty_eur'], qty, 'quantity')
        close(t['planned_risk_eur'], planned, 'planned risk')
        assert planned <= 125 + 1e-8
        side = 'bid' if d == 1 else 'ask'
        op = float(market.px[side + '_open'][j])
        hi, lo = float(market.px[side + '_high'][j]), float(market.px[side + '_low'][j])
        reason = t['exit_reason']
        if reason == 'TP':
            assert hi >= target + tick if d == 1 else lo <= target - tick
            fill = target
        elif reason == 'TIME':
            assert end == stamp(t['day'], '16:00')
            fill = op - d * slip
        else:
            assert reason in ('SL', 'SL_GAP')
            assert lo <= stop if d == 1 else hi >= stop
            assert (reason == 'SL_GAP') == (d * (op - stop) < 0)
            fill = (min(op, stop) if d == 1 else max(op, stop)) - d * slip
        exit_fx = float(market.px['mid_open'][j])
        net = qty * (-fee / 2 / fx + (d * (fill - entry) - fee / 2) / exit_fx)
        max_error = max(max_error, abs(float(t['net_eur']) - net))
        close(t['net_eur'], net, 'recorded cash')
        balance += float(t['net_eur'])
        close(t['balance_after_eur'], balance, 'balance')
        net = float(t['net_eur'])
        streak = streak + 1 if net < 0 else 0 if net > 0 else streak
        if streak >= 2:
            pause = end + 24 * 60 * D.MIN_MS
        daily[t['day']] += 1
        risk[t['day']] += planned
    assert max(daily.values(), default=0) <= 4
    assert max(risk.values(), default=0) <= 500 + 1e-8
    assert len(trades) == len({(t['entry_utc'], t['direction']) for t in trades}) == summary['closed_trades']
    assert len(trades) == sum(e['reason'] == 'ENTERED' for e in decisions)
    assert summary['event_counts'] == dict(Counter(e['reason'] for e in decisions))
    close(sum(float(t['net_eur']) for t in trades), summary['net_eur'], 'net summary')
    assert summary['halt'] is None
    return {'status': 'PASS', 'closed_trades': len(trades), 'maximum_fill_cash_error_eur': max_error}


def audit_context(info, direction, market, h1, m5, pivots):
    t, i = int(info['decision_ms']), market.idx(int(info['decision_ms']))
    h = (t - h1.origin_ms) // h1.period_ms - 1
    k = m5.slot_of_close(t)
    assert info['H1_known_at_ms'] == h1.close_ms(h) <= t
    assert info['M5_known_at_ms'] == m5.close_ms(k) == t
    assert info['H1_complete'] == bool(h1.complete[h])
    body = float(h1.close[h] - h1.open[h]) if h1.complete[h] else None
    if body is None:
        assert info['H1_body'] is None
    else:
        close(info['H1_body'], body, 'H1 body', 1e-12)
    # Prefix-only recomputation checks the feature without passing any future bar.
    a = k
    while a >= 0 and m5.complete[a]:
        a -= 1
    value = talib.ADX(m5.high[a + 1:k + 1], m5.low[a + 1:k + 1], m5.close[a + 1:k + 1], 14)[-1]
    adx = float(value) if np.isfinite(value) else None
    if adx is None:
        assert info['ADX14_M5'] is None
    else:
        close(info['ADX14_M5'], adx, 'prefix ADX', 1e-10)
    reasons = []
    if body is None:
        reasons.append('H1_DATA_UNKNOWN')
    elif direction * body <= 0:
        reasons.append('H1_BODY_NOT_ALIGNED')
    if adx is None:
        reasons.append('ADX_WARMUP_UNKNOWN')
    elif adx < 25:
        reasons.append('ADX_BELOW_25')
    assert reasons == info['reasons']
    eligible = {p.pid: p for p in pivots if t - D.DAY_MS <= p.known_at_ms <= t and p.kind == ('HIGH' if direction == 1 else 'LOW')}
    assert {p['id'] for p in info['levels']} == set(eligible)
    for level in info['levels']:
        p = eligible[level['id']]
        assert level['known_at_ms'] == p.known_at_ms
        price = p.bid_high if direction == 1 else p.ask_low
        close(level['executable_price'], price, 'level quote', 1e-12)
        start = market.idx(p.known_at_ms)
        present = market.present[start:i]
        values = market.px['bid_high' if direction == 1 else 'ask_low'][start:i][present]
        visited = bool(np.any(direction * (values - price) >= 0))
        expected = 'VISITED' if visited else 'INTACT_OBSERVED' if present.all() else 'UNKNOWN_SINCE_CONFIRMATION'
        assert level['freshness'] == expected
        assert level['observed_minutes'] == int(present.sum()) and level['expected_minutes'] == i - start


def count_outcomes(records, level):
    outcomes = [r['thresholds'][level] for r in records]
    hits = [r for r in outcomes if r['reached'] is True]
    unknown = sum(r['reached'] is None for r in outcomes)
    return {'reached': len(hits),
            'reached_in_later_M1': sum(r['time_relation'] == 'LATER_M1_AFTER_2R' for r in hits),
            'reached_in_same_M1_as_TP2': sum(r['time_relation'] == 'SAME_M1_AS_2R' for r in hits),
            'stop_before_threshold': sum(r['status'] == 'STOP_BEFORE_THRESHOLD' for r in outcomes),
            'expired_at_16_London': sum(r['status'] == 'EXPIRED_AT_DEADLINE' for r in outcomes),
            'unknown': unknown,
            'stop_threshold_same_M1_ambiguities': sum(r['stop_and_target_same_M1'] is True for r in outcomes),
            'descriptive_reach_fraction_lower': len(hits) / len(outcomes) if outcomes else None,
            'descriptive_reach_fraction_upper': (len(hits) + unknown) / len(outcomes) if outcomes else None}


def audit_continuation(record, trade, cfg, scenario, market):
    fee, slip = costs_of(cfg, scenario)
    entry, stop, qty, d = (float(trade[k]) for k in ('entry_price', 'stop', 'qty_eur', 'direction'))
    original = record['original_2R']
    row2 = int(original['exit_row_open_ms'])
    assert original['validated_actual_TP'] is True and trade['exit_reason'] == 'TP'
    assert int(original['model_closed_at_ms']) == ms(trade['exit_utc']) == row2 + D.MIN_MS
    assert record['entry_utc'] == trade['entry_utc'] and record['direction'] == int(d)
    close(original['target'], trade['target'], 'original target')
    close(original['actual_net_eur'], trade['net_eur'], 'original cash')
    close(record['initial_stop'], stop, 'initial stop')
    close(record['qty_eur_unchanged'], qty, 'initial quantity')
    deadline = stamp(trade['day'], '16:00')
    assert record['deadline_ms'] == deadline
    side = 'bid' if d == 1 else 'ask'
    first, limit = market.idx(row2), market.idx(deadline)
    assert record['portfolio_equity_must_not_be_aggregated'] is True
    evidence = []
    for name, out in record['thresholds'].items():
        multiple = int(name[:-1])
        target = entry + d * (multiple * (d * (entry - stop) + fee + slip) + fee)
        close(out['target'], target, 'continued target', 1e-12)
        close(out['stop_unchanged'], stop, 'continued stop')
        close(out['quantity_unchanged'], qty, 'continued quantity')
        at = int(out['event_row_open_ms'])
        j = market.idx(at)
        assert row2 <= at <= deadline
        assert out['event_row_end_exclusive_ms'] == at + D.MIN_MS
        assert out['time_relation'] == ('SAME_M1_AS_2R' if at == row2 else 'LATER_M1_AFTER_2R')
        assert out['exact_intraminute_fill_order_verified'] is False
        assert out['reached'] is not None, 'An unknown continuation requires separate unresolved audit'
        assert market.present[first:j + 1].all()
        assert out['row_first_quote_ms_not_fill_time'] == int(market.first_ts[j])
        stop_values = market.px[side + ('_low' if d == 1 else '_high')]
        target_values = market.px[side + ('_high' if d == 1 else '_low')]
        tick = cfg['tick_quote']
        touch = target_values >= target + tick if d == 1 else target_values <= target - tick
        # Quote checks stay inside the already recorded continuation interval.
        # They neither generate an alternative trade nor invoke an execution path.
        if out['status'] == 'REACHED_BEFORE_STOP_OR_DEADLINE':
            assert out['reached'] is True and out['exit_reason'] == 'TP'
            assert at < deadline and bool(touch[j])
            assert not touch[first:j].any()
            assert not (d * (stop_values[first:j + 1] - stop) <= 0).any()
            assert out['model_closed_at_ms'] == at + D.MIN_MS
        elif out['status'] == 'EXPIRED_AT_DEADLINE':
            assert out['reached'] is False and out['exit_reason'] == 'TIME'
            assert j == limit and out['model_closed_at_ms'] == deadline
            assert not touch[first:limit].any()
            assert not (d * (stop_values[first:limit] - stop) <= 0).any()
        else:
            raise AssertionError('Unexpected terminal status in this recorded batch')
        evidence.append({'threshold': name, 'reached': out['reached'], 'target': target,
                         'event_row_utc': D.iso(at), 'model_closed_utc': D.iso(out['model_closed_at_ms']),
                         'executable_favorable_extreme': float(target_values[j]),
                         'row_first_quote_utc_not_fill': D.iso(int(market.first_ts[j]))})
    return {'entry_utc': trade['entry_utc'], 'TP2_row_utc': D.iso(row2),
            'TP2_model_closed_utc': D.iso(original['model_closed_at_ms']),
            'deadline_utc': D.iso(deadline), 'thresholds': evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'AUDIT_RESULTS.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(HERE) or output.exists():
        raise ValueError('Use a new file within results_audit')
    freeze = json.loads((RUN / 'FREEZE_BEFORE_RESULTS.json').read_text())
    manifest = json.loads((RUN / 'MANIFEST_SHA256.json').read_text())
    for name, expected in manifest.items():
        assert digest(RUN / name) == expected, name
    source = {**freeze['source_sha256'], **freeze['shared_source_sha256']}
    for name, expected in source.items():
        assert digest(REPO / name) == expected, name
    pre = json.loads((STUDY / 'continuation/SOURCE_IDENTITY_BEFORE_HISTORY.json').read_text())['source_sha256']
    assert all(source[k] == v for k, v in pre.items())
    old = json.loads((REPO / 'reports/simple_rearmed_v03_01/FREEZE_BEFORE_RESULTS.json').read_text())
    for name, expected in {**old['new_source_sha256'], **old['shared_source_sha256']}.items():
        if name in source:
            assert source[name] == expected, name
    results = json.loads((RUN / 'RESULTS.json').read_text())['variants']
    counts = json.loads((RUN / 'CONTINUATION_COUNTS.json').read_text())
    cfg = freeze['baseline_protocol']
    market, _ = market_from_cache(REPO / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl')
    h1, m5 = D.make_bars(market, 60, 'H1'), D.make_bars(market, 5, 'M5')
    pivots = D.find_pivots(h1)
    contexts, cells, continuation_evidence = {}, {}, {}
    outcome_count = 0
    for variant in freeze['plan']['variants']:
        name = variant['name']
        for scenario in ('base', 'higher_costs'):
            folder = RUN / name / scenario
            trades, decisions = rows(folder / 'TRADES.csv'), rows(folder / 'DECISIONS.csv')
            summary = {**results[name][scenario], 'audit_cost_scenario': scenario}
            cells[f'{name}/{scenario}'] = audit_fills(trades, decisions, cfg, summary, market, variant['target_R'])
            for event in decisions:
                if not event.get('chart_context'):
                    continue
                info = json.loads(event['chart_context'])
                direction = int(event['direction'])
                key = info['decision_ms'], direction
                if key in contexts:
                    assert contexts[key] == info
                else:
                    audit_context(info, direction, market, h1, m5, pivots)
                    contexts[key] = info
                if event['reason'] in ('ENTERED', 'REFUSED'):
                    assert not info['reasons']
                else:
                    assert json.loads(event['signal_filter_reasons']) == info['reasons']
                    assert event['account_checks_status'] == 'NOT_EVALUATED_AFTER_CONTEXT_REJECTION'
                if variant['level_veto'] and event.get('level_guard_considered'):
                    d, i = direction, market.idx(int(event['decision_ms']))
                    quote = float(market.px['bid_open' if d == 1 else 'ask_open'][i])
                    target = float(event['target'])
                    wanted = [x for x in info['levels'] if d * (x['executable_price'] - quote) > 0 and d * (target - x['executable_price']) >= 0]
                    assert json.loads(event['level_guard_considered']) == wanted
                    refusal = json.loads(event['refusal_reasons'])
                    assert ('H1_LEVEL_BEFORE_OR_AT_TARGET' in refusal) == any(x['freshness'] == 'INTACT_OBSERVED' for x in wanted)
                    assert ('H1_LEVEL_FRESHNESS_UNKNOWN' in refusal) == any(x['freshness'] == 'UNKNOWN_SINCE_CONFIRMATION' for x in wanted)
            if variant['target_R'] == 2:
                records = json.loads((folder / 'TP2_CONTINUATIONS.json').read_text())
                actual = {(t['entry_utc'], int(t['direction'])): t for t in trades if t['exit_reason'] == 'TP'}
                assert len(records) == len(actual) == counts[name][scenario]['actual_TP2_exits']
                assert {(r['entry_utc'], r['direction']) for r in records} == set(actual)
                continuation_evidence[f'{name}/{scenario}'] = [audit_continuation(r, actual[(r['entry_utc'], r['direction'])], cfg, scenario, market) for r in records]
                flat = rows(folder / 'TP2_CONTINUATIONS.csv')
                assert len(flat) == 3 * len(records)
                for level in ('3R', '4R', '5R'):
                    assert count_outcomes(records, level) == counts[name][scenario]['thresholds'][level]
                by_key = {(r['entry_utc'], str(r['direction']), level): out for r in records for level, out in r['thresholds'].items()}
                for row in flat:
                    out = by_key[(row['entry_utc'], row['direction'], row['threshold'])]
                    assert row['reached'] == str(out['reached'])
                    assert int(row['event_row_open_ms']) == out['event_row_open_ms']
                    assert int(row['model_closed_at_ms']) == out['model_closed_at_ms']
                    close(row['target'], out['target'], 'CSV continued target')
                    assert row['status'] == out['status'] and row['time_relation'] == out['time_relation']
                outcome_count += 3 * len(records)
    for scenario in ('base', 'higher_costs'):
        for label in ('TRADES', 'DECISIONS'):
            oldfile = REPO / 'research/indicator_study_20261104/lab/comparison_01' / f'V03_{scenario}_{label}.csv'
            assert (RUN / 'V03_3R' / scenario / f'{label}.csv').read_bytes() == oldfile.read_bytes()
    report = {'status': 'PASS', 'audit_type': 'Recorded outputs and direct source quote checks only',
              'audit_script_sha256': digest(Path(__file__)), 'run_manifest_sha256': digest(RUN / 'MANIFEST_SHA256.json'),
              'result_files_verified': len(manifest), 'source_identities_verified': len(source),
              'original_core_and_continuation_pre_history_hashes_unchanged': True,
              'control_3R_trade_and_decision_byte_parity': True, 'cells_verified': cells,
              'unique_price_time_context_snapshots_prefix_checked': len(contexts),
              'continued_threshold_outcomes_checked_correlated': outcome_count,
              'continuation_evidence': continuation_evidence,
              'new_financial_backtest': False, 'execution_path_simulator_called': False,
              'counterfactual_portfolio_aggregated': False,
              'limits': ['Counts apply to actual TP2 exits, not all trades or a prediction',
                         'M1 row boundaries and model close times are not certified intraminute fills',
                         'Known threshold horizons checked only for already recorded continuation observations',
                         'Same trades repeated across variants/costs are correlated',
                         '2021 development; no FTMO compliance or independent validation established']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'result_files_verified', 'source_identities_verified', 'unique_price_time_context_snapshots_prefix_checked', 'continued_threshold_outcomes_checked_correlated')}, indent=2))


if __name__ == '__main__':
    main()
