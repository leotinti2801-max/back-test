"""Analyse only strategy A's existing trades; no market replay or optimization.

MFE/MAE are executable-side price excursions before the exit minute, not tick
extrema before the actual exit. Excluding the exit minute avoids inventing the
ordering of its high/low relative to a stop fill.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

from backtest_bot.data import load_cache
from backtest_bot.research import write_csv, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    with (args.results / 'TRADES.csv').open(newline='') as stream:
        rows = [r for r in csv.DictReader(stream)
                if r['candidate'] == 'A_STRUCTURE_FIXED_2R' and r['scenario'] == 'base']
    if not rows:
        raise ValueError('No existing trades for the selected strategy')
    df, _ = load_cache(args.cache)
    cases = []
    for row in rows:
        start, close = pd.Timestamp(row['entry_utc']), pd.Timestamp(row['exit_utc'])
        terminal_open = close if row['exit_reason'] == 'TIME' else close - pd.Timedelta(minutes=1)
        observed = df.loc[(df.index >= start) & (df.index < terminal_open)]
        d, entry, stop = int(row['direction']), float(row['entry_price']), float(row['stop'])
        side = 'bid' if d == 1 else 'ask'
        distance = d * (entry - stop)
        favourable = observed[side + ('_high' if d == 1 else '_low')]
        adverse = observed[side + ('_low' if d == 1 else '_high')]
        mfe = max(0.0, float((d * (favourable - entry)).max())) if len(observed) else None
        mae = max(0.0, float((-d * (adverse - entry)).max())) if len(observed) else None
        cases.append({
            'entry_utc': row['entry_utc'], 'exit_utc': row['exit_utc'],
            'direction': 'BUY' if d == 1 else 'SELL',
            'exit_reason': row['exit_reason'], 'net_eur': float(row['net_eur']),
            'realized_cash_R': float(row['R']), 'planned_quote_target_R': 2.0,
            'duration_minutes': (close - start).total_seconds() / 60,
            'remaining_minutes_to_16utc_at_entry': 960 - start.hour * 60 - start.minute,
            'initial_stop_distance_pips': distance / 0.0001,
            'planned_target_distance_pips': d * (float(row['target']) - entry) / 0.0001,
            'MFE_before_exit_minute_pips': None if mfe is None else mfe / 0.0001,
            'MAE_before_exit_minute_pips': None if mae is None else mae / 0.0001,
            'MFE_before_exit_minute_price_R': None if mfe is None else mfe / distance,
            'MAE_before_exit_minute_price_R': None if mae is None else mae / distance,
        })
    positive_r = [float(r['R']) for r in rows if float(r['net_eur']) > 0]
    negative_r = [-float(r['R']) for r in rows if float(r['net_eur']) < 0]
    average_win = sum(positive_r) / len(positive_r) if positive_r else None
    average_loss = sum(negative_r) / len(negative_r) if negative_r else None
    breakeven = average_loss / (average_win + average_loss) if average_win and average_loss else None
    summary = {
        'strategy': 'A_STRUCTURE_FIXED_2R', 'market_replayed': False, 'parameters_optimized': False,
        'existing_trades': len(rows), 'net_eur': sum(float(r['net_eur']) for r in rows),
        'mean_positive_cash_R': average_win, 'mean_absolute_negative_cash_R': average_loss,
        'illustrative_breakeven_win_rate_if_these_average_payoffs_were_stable': breakeven,
        'breakeven_warning': 'Descriptive calculation from three selected trades; not a population estimate or prediction',
        'exit_reasons': {k: sum(r['exit_reason'] == k for r in rows) for k in sorted({r['exit_reason'] for r in rows})},
        'TP_count': sum(r['exit_reason'] == 'TP' for r in rows),
        'positive_TIME_exit_count': sum(r['exit_reason'] == 'TIME' and float(r['net_eur']) > 0 for r in rows),
        'explicit_commission_eur': sum(float(r['commission_eur']) for r in rows),
        'explicit_slippage_eur': sum(float(r['slippage_eur']) for r in rows),
        'cost_warning': 'Already included in net_eur. Spread is already embedded in bid/ask fills. Do not deduct twice.',
        'excursion_warning': 'Pre-exit-minute M1 price envelopes only; neither tick-accurate MAE/MFE nor EUR cash R',
        'source_trades_sha256': hashlib.sha256((args.results / 'TRADES.csv').read_bytes()).hexdigest(),
    }
    args.output.mkdir(parents=True)
    write_json(args.output / 'FOCUSED_ANALYSIS.json', summary)
    write_csv(args.output / 'THREE_TRADE_CASES.csv', cases)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(cases, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
