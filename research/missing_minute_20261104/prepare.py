"""Authorized preparation ONLY: synthetic tests, Q1 witness and exposure-free gap inventory."""
import argparse
import csv
import io
import json
import platform
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from backtest_bot.data import market_from_cache, CACHE_SHA256
from backtest_bot.reference import ROOT, D
from backtest_bot.research import epoch_ms, write_csv
from simple_forex.strategy_rearmed import signals
from common import HERE, START, CONTROL_END, END, SCENARIOS, assert_scope, configs, control_market, digest, write_json
from engine import simulate
from statistics_frozen import draw_identity


def inventory(mk):
    """Only timestamps/presence/quarantine masks, NEVER signals or positions."""
    a, b = mk.idx(epoch_ms(START)), mk.idx(epoch_ms(END))
    absent = ~mk.present[a:b]
    starts = np.flatnonzero(absent & np.r_[True, ~absent[:-1]]) + a
    ends = np.flatnonzero(absent & np.r_[~absent[1:], True]) + a + 1
    rows = []
    for lo, hi in zip(starts, ends, strict=True):
        length = int(hi - lo)
        end_of_data = hi >= mk.n
        rule = 'R2' if end_of_data or length > 5 else 'R1'
        rows.append({'start_utc': D.iso(mk.t(lo)), 'end_exclusive_utc': D.iso(mk.t(hi)),
            'missing_minutes': length, 'first_observed_after_utc': D.iso(mk.t(hi)) if not end_of_data else None,
            'quarantine_overlap': bool(mk.quality_minutes[lo:hi].any()),
            'cause': 'QUARANTINE_PRESENT' if mk.quality_minutes[lo:hi].any() else 'UNKNOWN_NO_TICK_VS_LOST_DATA',
            'if_position_exposed': rule,
            'S_CONT_if_exposed': 'resume; delayedTIME if needed' if rule == 'R1' else 'UNRESOLVED_EXECUTION; net null',
            'S_PESS_if_exposed': 'original stop or worse first observed open; slip/FX at resume' if rule == 'R1' else 'UNRESOLVED_EXECUTION; net null',
            'S_OPT_if_exposed': 'target, no improvement; FX at resume' if rule == 'R1' else 'UNRESOLVED_EXECUTION; net null',
            'if_entry_quote_missing': 'R3 ENTRY_QUOTE_MISSING_REFUSED; continue',
            'actual_exposure_checked': False})
    write_csv(HERE / 'KNOWN_GAPS_NO_EXPOSURE.csv', rows)
    months = pd.date_range(START, END, freq='min', inclusive='left').strftime('%Y-%m')
    counts = [{'month': month, 'scope_start_utc': START if month == '2021-01' else month + '-01T00:00:00Z',
        'grid_minutes': int((months == month).sum()),
        'missing_minutes': int(absent[months == month].sum())} for month in sorted(set(months))]
    write_json(HERE / 'GAP_INVENTORY_SUMMARY.json', {'gaps': len(rows), 'missing_minutes': int(absent.sum()),
        'R1_if_exposed': sum(r['if_position_exposed'] == 'R1' for r in rows),
        'R2_if_exposed': sum(r['if_position_exposed'] == 'R2' for r in rows),
        'per_month': counts, 'actual_positions_or_performance_evaluated': False,
        'note': 'Classification solely hypothetical by gap length/end of grid, no market closure inferred'})


def compare_trades(actual, expected):
    assert len(actual) == len(expected) == 61, 'Expected61 closed trades'
    maximum = 0.0
    for i, (trade, source) in enumerate(zip(actual, expected, strict=True)):
        for field, original in source.items():
            value = trade[field]
            if isinstance(value, bool):
                assert str(value) == original, (i, field)
            elif isinstance(value, (float, int)):
                delta = abs(float(value) - float(original))
                maximum = max(maximum, delta)
                assert delta <= 1e-8, (i, field, delta)
            else:
                assert str(value) == original, (i, field)
    return maximum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    assert_scope()
    if (HERE / 'FREEZE_BEFORE_RESULTS.json').exists() or (HERE / 'WITNESS.json').exists() or (HERE / 'WITNESS_FAILURE.json').exists():
        raise RuntimeError('Preparation already attempted; no automatic replay or overwrite')
    buffer = io.StringIO()
    tests = unittest.defaultTestLoader.discover(str(HERE), pattern='test_*.py')
    outcome = unittest.TextTestRunner(stream=buffer, verbosity=2).run(tests)
    (HERE / 'TEST_RESULTS.txt').write_text(buffer.getvalue())
    write_json(HERE / 'TEST_RESULTS.json', {'command': 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -B research/missing_minute_20261104/prepare.py --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl',
        'synthetic_tests': outcome.testsRun, 'success': outcome.wasSuccessful(), 'market_prices_read_by_tests': False})
    if not outcome.wasSuccessful():
        raise RuntimeError('Synthetic tests failed; witness not started')
    market, quality = market_from_cache(args.cache)
    inventory(market)  # Inventory only; no exposure joins or post-Q1 performance.
    mk = control_market(market, epoch_ms(CONTROL_END))
    del market
    assert mk.end_ms == epoch_ms(CONTROL_END) and mk.n == mk.idx(mk.end_ms)
    ref = json.loads((ROOT / 'config/reference_params.json').read_text())
    protocol = json.loads((HERE / 'protocol.json').read_text())
    records, source_hashes = [], {}
    try:
        for name, cfg in configs().items():
            for cost, stress in [('base', False), ('higher_costs', True)]:
                source = ROOT / 'research/chart_context_20261104/run_01' / ('V03_3R' if name == 'V03' else 'V03_2R') / cost / 'TRADES.csv'
                source_hashes[str(source.relative_to(ROOT))] = digest(source)
                with source.open(newline='') as stream:
                    expected = list(csv.DictReader(stream))
                for scenario in SCENARIOS:
                    summary, trades, decisions, envelopes, gaps = simulate(mk, cfg, ref,
                        epoch_ms(START), epoch_ms(CONTROL_END), stress, signal_source=signals, scenario=scenario)
                    assert summary['halt'] is None and not gaps, 'Control must not have exposure gap'
                    delta = compare_trades(trades, expected)
                    assert abs(summary['net_eur'] - protocol['Q1_witness'][name + '_' + cost + '_exact']) <= 1e-8
                    record = {'strategy': name, 'cost': cost, 'scenario': scenario,
                        'closed_trades': len(trades), 'net_eur': summary['net_eur'],
                        'max_absolute_trade_field_difference': delta, 'exposure_gaps': 0, 'status': 'PASS'}
                    records.append(record)
                    write_csv(HERE / f'WITNESS_{name}_{scenario}_{cost}_TRADES.csv', trades)
    except Exception as exc:
        write_json(HERE / 'WITNESS_FAILURE.json', {'error': str(exc), 'completed_checks': records,
            'stopped': True, 'expected_values_unchanged': True, 'evaluation_run': False})
        raise
    write_json(HERE / 'WITNESS.json', {'status': 'PASS', 'checks': records,
        'published_source_sha256': source_hashes, 'physically_truncated_market_end': CONTROL_END,
        'performance_after_2021_03_31_calculated': False, 'cache_quality': quality})
    paths = [p for p in HERE.iterdir() if p.is_file() and p.name not in
        ['FREEZE_BEFORE_RESULTS.json','FREEZE_BEFORE_RESULTS.sha256']]
    paths += [ROOT / rel for rel in json.loads((HERE / 'PROVENANCE.json').read_text())['source_sha256']]
    paths += [ROOT / rel for rel in source_hashes]
    paths += list((ROOT / 'src/backtest_bot').glob('*.py')) + list((ROOT / 'vendor/h4m30_v01').glob('*.py')) + list((ROOT / 'config').glob('*.json'))
    frozen = {'lot': 'MISSING_MINUTE_V01', 'rules_and_user_amendments': protocol,
        'cache_sha256': CACHE_SHA256, 'cache_bytes': args.cache.stat().st_size,
        'base_comparison': json.loads((HERE / 'PROVENANCE.json').read_text()),
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
        'frozen_files_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))},
        'bootstrap_calendar_draws_before_prices': draw_identity(),
        'witness': 'WITNESS.json;12 scenario/control checks,61 trades each',
        'evaluation_has_not_run': True,
        'planned_outputs': ['run_01/EXECUTION_RECORD.json','run_01/{V03,V04}/{S_CONT,S_PESS,S_OPT}/{base,higher_costs}/TRADES.csv',
            'DECISIONS.csv','GAPS_ENCOUNTERED.csv','CONTROL_TRADES.csv','EVALUATION_TRADES.csv',
            'LIQUIDATION_ENVELOPES.csv','RESULTS.json','INFERENCE_AND_VERDICTS.json','MANIFEST_SHA256.json',
            'TECHNICAL_FAILURE_STOP.json only on error; no automatic retry'],
        'exact_GO_required': True, 'no_live_orders_or_deployment': True}
    write_json(HERE / 'FREEZE_BEFORE_RESULTS.json', frozen)
    sha = digest(HERE / 'FREEZE_BEFORE_RESULTS.json')
    (HERE / 'FREEZE_BEFORE_RESULTS.sha256').write_text(sha + '  FREEZE_BEFORE_RESULTS.json\n')
    print(json.dumps({'synthetic_tests': outcome.testsRun, 'witness_checks': len(records), 'status': 'PASS',
        'freeze_sha256': sha, 'evaluation_run': False}, indent=2))


if __name__ == '__main__':
    main()
