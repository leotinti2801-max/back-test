"""Finite context/target comparison and separately labelled TP2 continuations."""
import argparse
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import talib

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT, D
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from simple_forex.runner import parameters
from simple_forex.strategy_rearmed import signals
from context import ChartContext, simulate
from continuation import continue_trade, source_identity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnostics(summary, trades, events):
    entries = Counter(e['day'] for e in events if e['reason'] == 'ENTERED')
    summary.update(win_rate=summary['wins'] / len(trades) if trades else None,
        loss_rate=summary['losses'] / len(trades) if trades else None,
        max_executed_entries_per_day=max(entries.values(), default=0),
        exits=dict(Counter(t['exit_reason'] for t in trades)),
        negative_exits=dict(Counter(t['exit_reason'] for t in trades if t['net_eur'] < 0)),
        account_refusals_nonexclusive=dict(Counter(r for e in events for r in e.get('refusal_reasons', []))),
        signal_filter_reasons_nonexclusive=dict(Counter(r for e in events for r in e.get('signal_filter_reasons', []))),
        monthly_net_eur={month: sum(t['net_eur'] for t in trades if t['entry_utc'].startswith(month))
            for month in ['2021-01', '2021-02', '2021-03']})
    accepted = {(D.iso(e['decision_ms']), e['direction']): e for e in events if e['reason'] == 'ENTERED'}
    return [{**t, 'chart_context_at_entry': accepted[(t['entry_utc'], t['direction'])].get('chart_context'),
        'mechanical_loss_reason': 'STOP_TOUCHED' if t['exit_reason'].startswith('SL') else 'NEGATIVE_NET_AT_TIME_EXIT',
        'no_speculative_macro_cause': True} for t in trades if t['net_eur'] < 0]


def count_continuations(records):
    counts = {'actual_TP2_exits': len(records), 'hypothetical_not_portfolio': True, 'thresholds': {}}
    for level in ['3R', '4R', '5R']:
        outcomes = [r['thresholds'][level] for r in records]
        hits = [r for r in outcomes if r['reached'] is True]
        unknown = sum(r['reached'] is None for r in outcomes)
        counts['thresholds'][level] = {'reached': len(hits),
            'reached_in_later_M1': sum(r['time_relation'] == 'LATER_M1_AFTER_2R' for r in hits),
            'reached_in_same_M1_as_TP2': sum(r['time_relation'] == 'SAME_M1_AS_2R' for r in hits),
            'stop_before_threshold': sum(r['status'] == 'STOP_BEFORE_THRESHOLD' for r in outcomes),
            'expired_at_16_London': sum(r['status'] == 'EXPIRED_AT_DEADLINE' for r in outcomes),
            'unknown': unknown,
            'stop_threshold_same_M1_ambiguities': sum(r['stop_and_target_same_M1'] is True for r in outcomes),
            'descriptive_reach_fraction_lower': len(hits) / len(outcomes) if outcomes else None,
            'descriptive_reach_fraction_upper': (len(hits) + unknown) / len(outcomes) if outcomes else None}
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new directory')
    here = Path(__file__).resolve().parent
    plan = json.loads((here / 'PLAN_BEFORE_RESULTS.json').read_text())
    baseline = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    paths = [*here.glob('*.py'), here / 'PLAN_BEFORE_RESULTS.json', ROOT / 'simple_forex/runner.py',
        ROOT / 'simple_forex/strategy_rearmed.py', ROOT / 'simple_forex/protocol_v03.json']
    identity = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    identity.update(source_identity())
    shared = code_identity()
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {'plan': plan, 'baseline_protocol': baseline,
        'source_sha256': identity, 'shared_source_sha256': shared,
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
            'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode(),
            'compatibility': talib.get_compatibility(), 'ADX_unstable_period': talib.get_unstable_period('ADX')},
        'active_rules_modified': False, 'future_continuation_used_as_filter': False})
    market, quality = market_from_cache(args.cache)
    chart = ChartContext(market)
    results, table, continuation_counts = {}, [], {}
    for variant in plan['variants']:
        name = variant['name']
        cfg = {**baseline, 'planned_quote_reward_risk': variant['target_R'], 'research_level_veto': variant['level_veto']}
        results[name], continuation_counts[name] = {}, {}
        for costs, stress in [('base', False), ('higher_costs', True)]:
            summary, trades, events, envelopes = simulate(market, cfg, reference,
                epoch_ms(plan['period']['start']), epoch_ms(plan['period']['end_exclusive']), stress,
                signal_source=chart.signal_source if variant['context_filter'] else signals)
            losses = diagnostics(summary, trades, events)
            folder = args.output / name / costs
            folder.mkdir(parents=True)
            for label, rows in [('TRADES', trades), ('DECISIONS', events), ('LOSSES', losses), ('LIQUIDATION_ENVELOPES', envelopes)]:
                write_csv(folder / (label + '.csv'), rows)
            continuations = []
            if variant['target_R'] == 2:
                for trade in trades:
                    if trade['exit_reason'] != 'TP':
                        continue
                    hard = pd.Timestamp(f"{trade['day']} 16:00", tz='Europe/London').tz_convert('UTC')
                    params = parameters(reference, cfg, int(hard.value // 1_000_000), stress)
                    continuations.append(continue_trade(market, trade, params, cfg))
                write_json(folder / 'TP2_CONTINUATIONS.json', continuations)
                write_csv(folder / 'TP2_CONTINUATIONS.csv', [
                    {'entry_utc': r['entry_utc'], 'direction': r['direction'],
                     'TP2_row_utc': D.iso(r['original_2R']['exit_row_open_ms']), 'threshold': threshold,
                     **outcome} for r in continuations for threshold, outcome in r['thresholds'].items()])
                continuation_counts[name][costs] = count_continuations(continuations)
            results[name][costs] = summary
            table.append({'variant': name, 'costs': costs,
                **{k: summary[k] for k in ['closed_trades', 'wins', 'losses', 'win_rate', 'loss_rate',
                    'known_closed_net_eur', 'net_eur', 'closed_drawdown_eur', 'max_executed_entries_per_day']},
                'actual_TP_exits': summary['exits'].get('TP', 0),
                'halt_reason': summary['halt']['reason'] if summary['halt'] else ''})
            print(name, costs, 'N', len(trades), 'wins', summary['wins'], 'net', summary['net_eur'],
                'TP', summary['exits'].get('TP', 0), 'continuations', count_continuations(continuations)['thresholds']['3R'], flush=True)
    previous = ROOT / 'research/indicator_study_20261104/lab/comparison_01'
    for costs in ['base', 'higher_costs']:
        for label in ['TRADES', 'DECISIONS']:
            assert (args.output / 'V03_3R' / costs / (label + '.csv')).read_bytes() == (previous / f'V03_{costs}_{label}.csv').read_bytes()
    write_json(args.output / 'RESULTS.json', {'variants': results, 'cache_quality': quality,
        'new_active_filter': None, 'independent_validation': False, 'FTMO_pass_claimed': False,
        'annual_total_still_unknown': True, 'future_continuations_do_not_change_portfolio': True})
    write_json(args.output / 'CONTINUATION_COUNTS.json', continuation_counts)
    write_csv(args.output / 'COMPARISON.csv', table)
    for relative, expected in {**identity, **shared}.items():
        assert digest(ROOT / relative) == expected
    write_json(args.output / 'MANIFEST_SHA256.json', {str(p.relative_to(args.output)): digest(p)
        for p in args.output.rglob('*') if p.is_file()})


if __name__ == '__main__':
    main()
