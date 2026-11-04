"""Single predeclared EMA20/50 experiment on an already-viewed development quarter."""
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
from backtest_bot.reference import ROOT
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from simple_forex.runner import simulate
from simple_forex.strategy_rearmed import signals as baseline_signals
from features import Features
from trend_filter import filtered_signals


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new output directory')
    here = Path(__file__).resolve().parent
    plan_path = here / 'SINGLE_COMPARISON_PLAN.json'
    plan = json.loads(plan_path.read_text())
    cfg = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    files = list(here.glob('*.py')) + [plan_path, ROOT / 'simple_forex/protocol_v03.json',
        ROOT / 'simple_forex/strategy_rearmed.py', ROOT / 'simple_forex/runner.py']
    identity = {str(p.relative_to(ROOT)): digest(p) for p in files}
    shared = code_identity()
    runtime = {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
        'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode(),
        'compatibility': talib.get_compatibility(), 'EMA_unstable_period': talib.get_unstable_period('EMA')}
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {
        'plan': plan, 'protocol': cfg, 'source_sha256': identity,
        'shared_source_sha256': shared, 'runtime': runtime, 'active_rules_modified': False,
        'live_trading_enabled': False, 'independent_validation': False})
    mk, quality = market_from_cache(args.cache)
    features = Features(mk)
    results = {}
    for label, signal_source in [('V03', baseline_signals), ('EMA20_50', filtered_signals(features))]:
        results[label] = {}
        for costs, stress in [('base', False), ('higher_costs', True)]:
            summary, trades, events, envelopes = simulate(mk, cfg, reference,
                epoch_ms(plan['start_utc']), epoch_ms(plan['end_exclusive_utc']), stress,
                signal_source=signal_source)
            summary['closed_win_rate'] = summary['wins'] / len(trades) if trades else None
            summary['closed_exits'] = dict(Counter(t['exit_reason'] for t in trades))
            summary['max_executed_entries_per_day'] = max(Counter(t['day'] for t in trades).values(), default=0)
            summary['refusal_reasons_nonexclusive'] = dict(Counter(
                reason for event in events for reason in event.get('refusal_reasons', [])))
            summary['filter_rejections'] = dict(Counter(e['reason'] for e in events if e['reason'].startswith('FILTER_')))
            summary['post_D45_closed_net_eur'] = sum(t['net_eur'] for t in trades if t['entry_utc'] >= '2021-02-18T00:00:00Z')
            results[label][costs] = summary
            prefix = label + '_' + costs
            write_csv(args.output / (prefix + '_TRADES.csv'), trades)
            write_csv(args.output / (prefix + '_DECISIONS.csv'), events)
            write_csv(args.output / (prefix + '_LIQUIDATION_ENVELOPES.csv'), envelopes)
            print(prefix, len(trades), summary['net_eur'], summary['filter_rejections'], flush=True)
    # Confirm the unchanged witness reproduces the previously frozen closed prefix.
    with (ROOT / 'reports/simple_rearmed_v03_01/RESULTS.json').open() as stream:
        previous = json.load(stream)
    for costs in ['base', 'higher_costs']:
        old, new = previous['periods']['Y2021'][costs], results['V03'][costs]
        assert new['closed_trades'] == old['closed_trades']
        assert abs(new['known_closed_net_eur'] - old['known_closed_net_eur']) < 1e-8
    write_json(args.output / 'RESULTS.json', {'results': results, 'cache_quality': quality,
        'development_only': True, 'FTMO_pass_claimed': False, 'active_variant_selected': False,
        'common_period_excludes_known_April_exposure_gap': True,
        'filter_account_overlap_not_evaluated_for_filter_rejections': True})
    for relative, expected in {**identity, **shared}.items():
        assert digest(ROOT / relative) == expected
    write_json(args.output / 'MANIFEST_SHA256.json', {p.name: digest(p)
        for p in args.output.iterdir() if p.is_file()})


if __name__ == '__main__':
    main()
