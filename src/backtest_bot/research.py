"""Frozen, bounded research runner. No broker, orders or automatic promotion."""
import argparse
import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .data import CACHE_SHA256, market_from_cache
from .reference import D, E, ROOT
from .simulation import run_period
from .strategy import build_context, make_params, shared_structures


def epoch_ms(value):
    return int(pd.Timestamp(value).value // 1_000_000)


def select_development(results, rule):
    """Never inspect later period returns. No candidate is mandatory."""
    eligible = []
    for name, periods in results.items():
        m = periods['development']
        pf_ok = (m['profit_factor'] is not None and m['profit_factor'] >= rule['min_profit_factor']) or (
            m['gross_profit_eur'] > 0 and m['gross_loss_eur'] == 0)
        if (m['halt'] is None and m['closed_trades'] >= rule['min_closed_trades'] and pf_ok
                and m['net_eur'] is not None and m['net_eur'] > 0
                and m['closed_drawdown_eur'] <= rule['max_closed_drawdown_eur']):
            score = m['net_eur'] / max(250, m['closed_drawdown_eur'])
            eligible.append((-score, name))
    return sorted(eligible)[0][1] if eligible else None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    if not fields:
        fields = ['no_rows']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def code_identity():
    paths = sorted([*ROOT.glob('src/**/*.py'), *ROOT.glob('vendor/**/*.py'), *ROOT.glob('config/*.json')])
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def run(cache, output):
    if output.exists():
        raise ValueError('Output already exists: use a new directory; previous experiments are never overwritten')
    spec = json.loads((ROOT / 'config/research_v02.json').read_text())
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    output.mkdir(parents=True)
    freeze = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'protocol': spec,
              'source_sha256': code_identity(), 'data_sha256': CACHE_SHA256,
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__}}
    write_json(output / 'FREEZE_BEFORE_RESULTS.json', freeze)
    market, quality = market_from_cache(cache)
    structures = shared_structures(market, reference)
    original_ctx = build_context(market, reference, spec['fixed_controls'], {'bias': 'structure'}, structures)
    baseline = E.run_cell(market, reference, epoch_ms('2021-01-01T00:00:00Z'), market.end_ms, ctx=original_ctx)
    baseline_report = {
        'setups_2021': sum(e['event'] == 'SETUP_CREATED' and e['in_window'] for e in baseline.setup_events),
        'counted_closed_trades': sum(t['counted'] for t in baseline.trades),
        'halt': baseline.halt,
        'expected_uploaded_setups': 12, 'expected_uploaded_trades': 0,
    }
    if (baseline_report['setups_2021'], baseline_report['counted_closed_trades'], baseline.halt) != (12, 0, None):
        raise AssertionError(f'Reference reproduction failed: {baseline_report}')
    print('Reference reproduced: 12 setups, 0 trades', flush=True)
    results = {}
    diagnostics = {}
    all_trades, all_decisions = [], []
    controls = spec['fixed_controls']
    for candidate in spec['candidates']:
        name = candidate['name']
        params = make_params(reference, controls, candidate)
        ctx = build_context(market, params, controls, candidate, structures)
        results[name] = {}
        for period in spec['periods']:
            summary, trades, decisions = run_period(ctx, params, candidate, controls,
                                                    epoch_ms(period['start']), epoch_ms(period['end']))
            results[name][period['name']] = summary
            all_trades.extend({'candidate': name, 'period': period['name'], 'mode': 'continuous', **t} for t in trades)
            all_decisions.extend({'candidate': name, 'period': period['name'], 'mode': 'continuous', **d} for d in decisions)
            print(name, period['name'], 'closed', summary['closed_trades'],
                  'net', summary['net_eur'], 'halt', summary['halt']['reason'] if summary['halt'] else None, flush=True)
        diag, trades, decisions = run_period(ctx, params, candidate, controls, epoch_ms('2021-01-01T00:00:00Z'),
                                            market.end_ms, independent_days=True)
        diagnostics[name] = diag
        all_trades.extend({'candidate': name, 'period': 'independent_days_2021', 'mode': 'diagnostic', **t} for t in trades)
        all_decisions.extend({'candidate': name, 'period': 'independent_days_2021', 'mode': 'diagnostic', **d} for d in decisions)
    selected = select_development(results, spec['selection'])
    stress = None
    if selected is not None:
        candidate = next(c for c in spec['candidates'] if c['name'] == selected)
        p = make_params(reference, controls, candidate, stress=True, stress_spec=spec['stress'])
        ctx = build_context(market, p, controls, candidate, structures)
        stress = {}
        for period in spec['periods']:
            summary, trades, _ = run_period(ctx, p, candidate, controls,
                                            epoch_ms(period['start']), epoch_ms(period['end']))
            stress[period['name']] = summary
            all_trades.extend({'candidate': selected, 'period': period['name'], 'mode': 'stress', **t} for t in trades)
    bundle = {
        'version': spec['version'], 'baseline_reproduced': baseline_report, 'cache_quality': quality,
        'continuous_periods': results, 'independent_daily_diagnostics': diagnostics,
        'selected_on_development_only': selected, 'selected_cost_stress': stress,
        'cost_stress_status': 'EXECUTED' if stress is not None else 'NOT_RUN_NO_ELIGIBLE_CANDIDATE',
        'live_trading_enabled': False, 'production_qualified': False,
        'limitations': ['All supplied 2021 data have already been used for development',
                        'No genuinely independent holdout is available',
                        'Historical quotes are incomplete; unknown paths are never replaced by zero PnL',
                        'Daily diagnostics restart flat and exclude cross-day pauses; never a portfolio return',
                        'Five new candidates plus a reproduced reference; no further tuning in this batch'],
    }
    write_json(output / 'RESULTS.json', bundle)
    write_csv(output / 'TRADES.csv', all_trades)
    write_csv(output / 'DECISIONS.csv', all_decisions)
    if freeze['source_sha256'] != code_identity():
        raise AssertionError('Source changed during experiment')
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}
    write_json(output / 'MANIFEST_SHA256.json', files)
    print('Selected on development:', selected, '; production qualified: false', flush=True)
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.cache, args.output)


if __name__ == '__main__':
    main()
