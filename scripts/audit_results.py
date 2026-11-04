"""Independently recompute annual trade cash flows from the supplied quotes.

Does not call the strategy or execution engine, and does not rerun a backtest.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from backtest_bot.data import load_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--results', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Audit output already exists')
    df, _ = load_cache(args.cache)
    with (args.results / 'TRADES.csv').open(newline='') as stream:
        trades = list(csv.DictReader(stream))
    state, count, largest_difference = {}, 0, 0.0
    for trade in trades:
        candidate, scenario = trade['candidate'], trade['scenario']
        fee = 0.00005 * (1.5 if scenario == 'higher_costs' else 1)
        slip = 0.00001 * (2 if scenario == 'higher_costs' else 1)
        direction, qty = int(trade['direction']), float(trade['qty_eur'])
        entry_time = pd.Timestamp(trade['entry_utc'])
        closed_at = pd.Timestamp(trade['exit_utc'])
        exit_time = closed_at if trade['exit_reason'] == 'TIME' else closed_at - pd.Timedelta(minutes=1)
        entry, exit_row = df.loc[entry_time], df.loc[exit_time]
        modeled_entry = float(entry['ask_open' if direction == 1 else 'bid_open']) + direction * slip
        assert math.isclose(modeled_entry, float(trade['entry_price']), abs_tol=1e-12)
        side = 'bid' if direction == 1 else 'ask'
        stop, target = float(trade['stop']), float(trade['target'])
        if trade['exit_reason'] == 'TP':
            modeled_exit = target
            penetration = exit_row[side + '_high'] >= target + 0.00001 if direction == 1 else exit_row[side + '_low'] <= target - 0.00001
            assert penetration
        elif trade['exit_reason'] in ('SL', 'SL_GAP'):
            opening = float(exit_row[side + '_open'])
            raw = min(opening, stop) if direction == 1 else max(opening, stop)
            modeled_exit = raw - direction * slip
        elif trade['exit_reason'] == 'TIME':
            modeled_exit = float(exit_row[side + '_open']) - direction * slip
            deadline = min(entry_time + pd.Timedelta(minutes=120), entry_time.normalize() + pd.Timedelta(hours=16))
            assert exit_time == deadline
        else:
            raise AssertionError('Unknown exit reason')
        entry_fx, exit_fx = float(entry['mid_open']), float(exit_row['mid_open'])
        expected_net = qty * ((direction * (modeled_exit - modeled_entry) - fee / 2) / exit_fx - fee / 2 / entry_fx)
        difference = abs(expected_net - float(trade['net_eur']))
        largest_difference = max(largest_difference, difference)
        assert difference < 1e-7, (candidate, trade['entry_utc'], difference)
        risk_quote = direction * (modeled_entry - stop) + fee + slip
        assert qty > 0 and qty % 2000 == 0
        assert qty * risk_quote / entry_fx <= 250 + 1e-8
        assert pd.Timestamp(trade['target_known_at_utc']) <= entry_time
        assert float(entry['first_ts']) - entry_time.value // 1_000_000 <= 5000
        group = state.setdefault((candidate, scenario), {'balance': 100000, 'dates': set(), 'streak': 0, 'pause': None})
        date = entry_time.date()
        assert date not in group['dates']
        group['dates'].add(date)
        if group['pause'] is not None:
            assert entry_time >= group['pause']
            group['streak'], group['pause'] = 0, None
        group['balance'] += expected_net
        assert abs(group['balance'] - float(trade['balance_after_eur'])) < 1e-7
        group['streak'] = group['streak'] + 1 if expected_net < 0 else 0 if expected_net > 0 else group['streak']
        if group['streak'] >= 2:
            group['pause'] = closed_at + pd.Timedelta(hours=24)
        count += 1
    report = {
        'annual_trade_rows_checked': count,
        'max_cash_flow_difference_eur': largest_difference,
        'checks': ['bid/ask cash flows and FX', 'commissions and slippage', 'planned risk <=250 EUR',
                   'quantity step', 'one entry per UTC day', '24 h pause after two losses',
                   'target availability', 'entry first tick delay', 'continuous closing balance'],
        'trades_csv_sha256': hashlib.sha256((args.results / 'TRADES.csv').read_bytes()).hexdigest(),
        'status': 'PASS',
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
