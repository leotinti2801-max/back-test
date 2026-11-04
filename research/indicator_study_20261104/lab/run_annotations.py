"""Compute indicators and historical levels without changing any trade decision."""
import argparse
import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import talib
from talib import abstract

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT, D
from backtest_bot.research import write_csv, write_json
from features import Features


def number(value):
    return float(value) if value not in (None, '') else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new output directory')
    source = ROOT / 'reports/simple_rearmed_v03_01'
    with (source / 'Y2021_base_DECISIONS.csv').open(newline='') as stream:
        decisions = [row for row in csv.DictReader(stream) if row['reason'] in ('ENTERED', 'REFUSED')]
    with (source / 'Y2021_base_TRADES.csv').open(newline='') as stream:
        trades = list(csv.DictReader(stream))
    outcome = {(t['entry_utc'], int(t['direction'])): t for t in trades}
    functions = [('EMA', 20), ('EMA', 50), ('RSI', 14), ('ATR', 14), ('ADX', 14), ('BBANDS', 20)]
    lookbacks = {}
    for name, period in functions:
        f = abstract.Function(name)
        f.set_parameters({'timeperiod': period})
        lookbacks[f'{name}{period}'] = f.lookback
    args.output.mkdir(parents=True)
    identity = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).resolve().parent.glob('*.py')}
    runtime = {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
               'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode(),
               'lookbacks_in_complete_M5_bars': lookbacks,
               'compatibility': talib.get_compatibility(),
               'unstable_periods': {name: talib.get_unstable_period(name) for name in ['EMA', 'RSI', 'ATR', 'ADX']},
               'constant_series_RSI14_probe': float(talib.RSI(np.ones(40), 14)[-1])}
    write_json(args.output / 'FREEZE_BEFORE_ANNOTATIONS.json', {'source_sha256': identity, 'runtime': runtime,
                'decision_csv_sha256': hashlib.sha256((source / 'Y2021_base_DECISIONS.csv').read_bytes()).hexdigest(),
                'trades_csv_sha256': hashlib.sha256((source / 'Y2021_base_TRADES.csv').read_bytes()).hexdigest(),
                'active_rules_modified': False, 'new_market_backtest': False})
    mk, quality = market_from_cache(args.cache)
    lab = Features(mk)
    rows, matched = [], set()
    for d in decisions:
        t, direction = int(d['decision_ms']), int(d['direction'])
        entered = d['reason'] == 'ENTERED'
        row = lab.snapshot(t, direction,
            planned_entry=number(d.get('entry_price')) if entered else None,
            planned_target=number(d.get('target')) if entered else None, stop=number(d.get('stop')))
        # Outcomes are joined only after all causal features have been computed.
        key = D.iso(t), direction
        closed = outcome.get(key) if entered else None
        row.update(original_decision=d['reason'], refusal_reasons=d.get('refusal_reasons', ''),
                   position_outcome_status='CLOSED' if closed else 'UNRESOLVED' if entered else 'NOT_ENTERED',
                   observed_net_eur=number(closed.get('net_eur')) if closed else None)
        if closed:
            matched.add(key)
        rows.append(row)
    assert matched == set(outcome), 'All closed trades must remain in the analysis'
    write_csv(args.output / 'CAUSAL_ANNOTATIONS.csv', rows)
    coverage = {}
    keys = ['ema20', 'ema50', 'rsi14', 'atr14', 'adx14', 'bb_upper',
            'nearest_resistance', 'nearest_support', 'nearest_opposing_executable_level']
    for group in ['CLOSED', 'UNRESOLVED', 'NOT_ENTERED']:
        cohort = [r for r in rows if r['position_outcome_status'] == group]
        coverage[group] = {'decisions': len(cohort),
            'available': {key: sum(r[key] is not None for r in cohort) for key in keys},
            'previous_NY_days_complete': sum(r['NY_DAY_complete'] for r in cohort),
            'previous_London_sessions_complete': sum(r['LONDON_SESSION_complete'] for r in cohort),
            'historical_opponent_before_or_at_target': sum(r['known_level_before_or_at_planned_target'] is True for r in cohort)}
    write_json(args.output / 'COVERAGE_AND_LIMITS.json', {
        'runtime': runtime, 'coverage': coverage, 'all_closed_positions_retained': len(matched),
        'decision_types': dict(Counter(r['original_decision'] for r in rows)),
        'new_market_backtest': False, 'active_filter': None, 'indicator_winner_selected': None,
        'causal_time_checks_passed': True, 'cache_quality': quality,
        'warnings': ['No prediction or trading improvement established', '2021 is development already viewed',
                     'Observed daily extrema are not certified levels when a minute is missing',
                     'Previous-day convention is NY17, not a verified MT5 broker candle',
                     'No global FX volume supplied; no VWAP or volume profile qualified',
                     'Historical levels can be stale or revisited; presence is not proof of reversal',
                     'RSI conventions of the tested 0.6.4 C library differ from newer main source docs']})
    for rel, digest in identity.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()})
    print(json.dumps(coverage, indent=2))


if __name__ == '__main__':
    main()
