"""Annual continuous replay and cost stress of the same five frozen candidates.

This adds no candidate and changes no strategy parameter. Annual loss pauses are
carried across quarter boundaries. Every result, including failure, is retained.
"""
import argparse
import hashlib
import json
from pathlib import Path

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from backtest_bot.simulation import run_period
from backtest_bot.strategy import build_context, make_params, shared_structures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    freeze = json.loads(args.freeze.read_text())
    if freeze['source_sha256'] != code_identity():
        raise RuntimeError('Source/configuration differ from the first experiment')
    if args.output.exists():
        raise ValueError('Use a new output directory')
    args.output.mkdir(parents=True)
    spec = freeze['protocol']
    write_json(args.output / 'PLAN_BEFORE_ANNUAL_RESULTS.json', {
        'first_experiment_freeze_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'analyses': ['full 2021 continuous replay', 'same candidates: fee x1.5, market slippage x2'],
        'no_new_candidates': True, 'no_parameter_retuning': True,
    })
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    mk, _ = market_from_cache(args.cache)
    structures = shared_structures(mk, reference)
    results, trades, decisions = {}, [], []
    for candidate in spec['candidates']:
        name = candidate['name']
        results[name] = {}
        for label, stressed in [('base', False), ('higher_costs', True)]:
            params = make_params(reference, spec['fixed_controls'], candidate,
                                 stress=stressed, stress_spec=spec['stress'])
            ctx = build_context(mk, params, spec['fixed_controls'], candidate, structures)
            summary, ts, ds = run_period(ctx, params, candidate, spec['fixed_controls'],
                                         epoch_ms('2021-01-01T00:00:00Z'), mk.end_ms)
            results[name][label] = summary
            trades.extend({'candidate': name, 'scenario': label, **t} for t in ts)
            decisions.extend({'candidate': name, 'scenario': label, **d} for d in ds)
            print(name, label, 'N', summary['closed_trades'], 'net', summary['net_eur'],
                  'PF', summary['profit_factor'], 'halt', summary['halt'], flush=True)
    write_json(args.output / 'ANNUAL_RESULTS.json', results)
    write_csv(args.output / 'TRADES.csv', trades)
    write_csv(args.output / 'DECISIONS.csv', decisions)
    if freeze['source_sha256'] != code_identity():
        raise RuntimeError('Source changed during annual verification')
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.iterdir()) if p.is_file()
    })


if __name__ == '__main__':
    main()
