"""Availability audit only: no outcome fields, account replay, filters or tuning."""
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
from backtest_bot.reference import D, ROOT

OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'research/indicator_study_20261104/lab/comparison_01'
CACHE = ROOT / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl'
HOUR = 60 * D.MIN_MS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csv_write(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    tracked = [ROOT / p for p in ['simple_forex/strategy_rearmed.py', 'simple_forex/protocol_v03.json',
        'simple_forex/runner.py', 'src/backtest_bot/data.py', 'vendor/h4m30_v01/h4m30_data.py',
        'research/indicator_study_20261104/lab/features.py']]
    tracked.extend([SOURCE / 'V03_base_TRADES.csv', SOURCE / 'V03_base_DECISIONS.csv'])
    identities = {str(p.relative_to(ROOT)): digest(p) for p in tracked}
    # Explicitly extract timestamps/directions only; no result or PnL column is retained.
    with (SOURCE / 'V03_base_TRADES.csv').open(newline='') as stream:
        entries = [{'time_ms': int(pd.Timestamp(r['entry_utc']).value // 1_000_000),
                    'direction': int(r['direction'])} for r in csv.DictReader(stream)]
    with (SOURCE / 'V03_base_DECISIONS.csv').open(newline='') as stream:
        breakouts = [{'time_ms': int(r['decision_ms']), 'direction': int(r['direction'])}
            for r in csv.DictReader(stream) if r['reason'] in ['ENTERED', 'REFUSED']]
    assert len(entries) == 61 and len(breakouts) == 202
    lookbacks = {}
    for name, period in [('EMA', 20), ('ATR', 14)]:
        function = abstract.Function(name)
        function.set_parameters({'timeperiod': period})
        lookbacks[f'{name}{period}'] = int(function.lookback)
    runtime = {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
        'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode(),
        'compatibility': int(talib.get_compatibility()),
        'unstable_periods': {x: int(talib.get_unstable_period(x)) for x in ['EMA', 'ATR']},
        'lookbacks_H1_indices': lookbacks}
    spec = {'purpose': 'Availability only, before possible pre-registration; no financial selection',
        'H1': 'UTC-aligned 60-minute bins, all 60 validated M1 required',
        'close_reference': 'Last nominal H1 close <= decision time, no stale fallback',
        'forming_H1_bar0': 'UTC hour containing decision time; explicitly excluded',
        'gap_policy': 'Reset TA-Lib state after EVERY incomplete H1, including absent closures without cited closure calendar',
        'EMA_period_H1': 20, 'ATR_period_H1': 14, 'ohlc_side': 'mid',
        'entry_count': len(entries), 'raw_BREAKOUT_count': len(breakouts),
        'Q1_start_utc': '2021-01-04T00:00:00Z', 'Q1_end_exclusive_utc': '2021-04-01T00:00:00Z',
        'no_PnL_join': True, 'no_market_simulation': True, 'no_parameter_search': True,
        'no_active_source_changes': True, 'runtime': runtime, 'source_sha256': identities,
        'script_sha256': digest(Path(__file__))}
    spec_path = OUT / 'SPEC_BEFORE_AVAILABILITY.json'
    if spec_path.exists():
        raise FileExistsError('Do not overwrite a preceding audit')
    write_json(spec_path, spec)
    market, quality = market_from_cache(CACHE)
    bars = D.make_bars(market, 60, 'H1')
    assert bars.period_ms == HOUR and bars.origin_ms % HOUR == 0
    assert np.array_equal(bars.complete, bars.m1_count == 60)
    present = market.present.reshape(bars.n, 60)
    assert np.array_equal(bars.complete, present.all(axis=1))
    # Cross-check aggregation independently from the preserved make_bars path.
    for field, reducer in [('open', 'first'), ('close', 'last'), ('high', 'max'), ('low', 'min')]:
        m1 = market.px['mid_' + field].reshape(bars.n, 60)[bars.complete]
        expected = m1[:, 0] if reducer == 'first' else m1[:, -1] if reducer == 'last' else m1.max(axis=1) if reducer == 'max' else m1.min(axis=1)
        assert np.array_equal(getattr(bars, field)[bars.complete], expected)
        assert np.isnan(getattr(bars, field)[~bars.complete]).all()
    ema, atr = np.full(bars.n, np.nan), np.full(bars.n, np.nan)
    run_lengths = np.zeros(bars.n, dtype=int)
    segment_start_slots = np.full(bars.n, -1, dtype=int)
    starts = np.flatnonzero(bars.complete & np.r_[True, ~bars.complete[:-1]])
    ends = np.flatnonzero(bars.complete & np.r_[~bars.complete[1:], True]) + 1
    segment_lengths = []
    for a, b in zip(starts, ends, strict=True):
        close, high, low = [np.ascontiguousarray(values[a:b]) for values in [bars.close, bars.high, bars.low]]
        ema[a:b], atr[a:b] = talib.EMA(close, 20), talib.ATR(high, low, close, 14)
        run_lengths[a:b] = np.arange(1, b - a + 1)
        segment_start_slots[a:b] = a
        segment_lengths.append(int(b - a))
        assert np.isfinite(ema[a:b]).sum() == max(0, b - a - lookbacks['EMA20'])
        assert np.isfinite(atr[a:b]).sum() == max(0, b - a - lookbacks['ATR14'])
    rows = []
    for group, cohort in [('V03_CLOSED_ENTRY', entries), ('Q1_RAW_BREAKOUT', breakouts)]:
        for index, event in enumerate(cohort):
            t = event['time_ms']
            slot = bars.slot_of_close(t)
            # Independent map: the hour starting at floor(t/H1) is bar0/forming;
            # the preceding slot is the last closed H1, including equality at t.
            bar0_open = t // HOUR * HOUR
            direct_slot = (bar0_open - bars.origin_ms) // HOUR - 1
            assert slot == direct_slot and 0 <= slot < bars.n
            source_close = bars.close_ms(slot)
            assert source_close == bar0_open and source_close <= t < source_close + HOUR
            age_minutes = (t - source_close) // D.MIN_MS
            complete = bool(bars.complete[slot])
            ema_ok, atr_ok = bool(np.isfinite(ema[slot])), bool(np.isfinite(atr[slot]))
            first_ema_close = bars.close_ms(int(segment_start_slots[slot]) + lookbacks['EMA20']) if complete else None
            first_atr_close = bars.close_ms(int(segment_start_slots[slot]) + lookbacks['ATR14']) if complete else None
            rows.append({'cohort': group, 'event_id': f'{group}_{index+1:03d}',
                'decision_utc': D.iso(t), 'decision_ms': t, 'direction': event['direction'],
                'forming_H1_bar0_open_utc_excluded': D.iso(bar0_open),
                'source_H1_slot': int(slot), 'source_H1_open_utc': D.iso(bars.open_ms(slot)),
                'source_H1_close_utc': D.iso(source_close), 'minutes_since_source_H1_close': int(age_minutes),
                'source_H1_complete': complete, 'source_H1_present_M1': int(bars.m1_count[slot]),
                'consecutive_complete_H1_at_source': int(run_lengths[slot]),
                'segment_start_utc': D.iso(bars.open_ms(int(segment_start_slots[slot]))) if complete else '',
                'EMA20_H1_available': ema_ok, 'ATR14_H1_available': atr_ok,
                'both_available': ema_ok and atr_ok,
                'EMA20_status': 'AVAILABLE' if ema_ok else 'INCOMPLETE_SOURCE_H1' if not complete else 'WARMUP_AFTER_GAP',
                'ATR14_status': 'AVAILABLE' if atr_ok else 'INCOMPLETE_SOURCE_H1' if not complete else 'WARMUP_AFTER_GAP',
                'EMA20_H1': float(ema[slot]) if ema_ok else '', 'ATR14_H1': float(atr[slot]) if atr_ok else '',
                'first_possible_EMA20_close_in_segment_utc': D.iso(first_ema_close) if first_ema_close else '',
                'first_possible_ATR14_close_in_segment_utc': D.iso(first_atr_close) if first_atr_close else '',
                'EMA20_remaining_complete_H1_needed': max(0, lookbacks['EMA20'] + 1 - int(run_lengths[slot])) if complete else '',
                'ATR14_remaining_complete_H1_needed': max(0, lookbacks['ATR14'] + 1 - int(run_lengths[slot])) if complete else ''})
    csv_write(OUT / 'H1_AVAILABILITY_BY_EVENT.csv', rows)
    coverage = {}
    for group in ['V03_CLOSED_ENTRY', 'Q1_RAW_BREAKOUT']:
        cohort = [x for x in rows if x['cohort'] == group]
        coverage[group] = {'events': len(cohort), 'complete_source_H1': sum(x['source_H1_complete'] for x in cohort),
            'EMA20_H1_available': sum(x['EMA20_H1_available'] for x in cohort),
            'ATR14_H1_available': sum(x['ATR14_H1_available'] for x in cohort),
            'both_available': sum(x['both_available'] for x in cohort),
            'EMA20_status_counts': dict(Counter(x['EMA20_status'] for x in cohort)),
            'ATR14_status_counts': dict(Counter(x['ATR14_status'] for x in cohort)),
            'consecutive_complete_H1_distribution': dict(sorted(Counter(x['consecutive_complete_H1_at_source'] for x in cohort).items())),
            'source_age_minutes_min_max': [min(x['minutes_since_source_H1_close'] for x in cohort), max(x['minutes_since_source_H1_close'] for x in cohort)],
            'first_event_utc': min(x['decision_utc'] for x in cohort), 'last_event_utc': max(x['decision_utc'] for x in cohort)}
    # Boundary audit is pure time arithmetic, including a sub-hour observation.
    anchor = int(pd.Timestamp('2021-01-05T10:00:00Z').value // 1_000_000)
    boundary = []
    for t in [anchor - D.MIN_MS, anchor, anchor + 5 * D.MIN_MS]:
        s = bars.slot_of_close(t)
        boundary.append({'decision_utc': D.iso(t), 'last_closed_H1_open_utc': D.iso(bars.open_ms(s)),
            'last_closed_H1_close_utc': D.iso(bars.close_ms(s)), 'bar0_open_utc_excluded': D.iso(t // HOUR * HOUR)})
    write_json(OUT / 'RESULTS.json', {'runtime': runtime, 'coverage': coverage,
        'validated_cache_sha256': digest(CACHE), 'cache_quality': quality,
        'full_grid_H1': {'slots': bars.n, 'complete': int(bars.complete.sum()), 'incomplete': int((~bars.complete).sum()),
            'complete_segments': len(segment_lengths), 'max_consecutive_complete_H1': max(segment_lengths),
            'EMA20_available_slots': int(np.isfinite(ema).sum()), 'ATR14_available_slots': int(np.isfinite(atr).sum())},
        'mapping_boundary_examples': boundary, 'mapping_passed_for_every_event': True,
        'aggregation_crosscheck_passed': True,
        'policy_relation_to_existing_lab': 'Same reset-after-every-incomplete-bar rule; target timeframe changed from M5 to H1, so a single missing M1 resets an entire H1 segment.',
        'closed_market_sessions_skipped': False, 'market_closure_calendar_supplied': False,
        'PnL_columns_loaded_into_feature_rows': False, 'PnL_indicator_join': False,
        'new_market_backtest': False, 'parameter_search': False, 'active_filter_enabled': False,
        'financial_improvement_claimed': False, 'development_only': True})
    for relative, expected in identities.items():
        assert digest(ROOT / relative) == expected, relative
    write_json(OUT / 'MANIFEST_SHA256.json', {p.name: digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'MANIFEST_SHA256.json'})
    print(json.dumps(coverage, indent=2))


if __name__ == '__main__':
    main()
