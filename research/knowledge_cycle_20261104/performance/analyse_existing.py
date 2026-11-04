"""Descriptive analysis of existing ledgers only; no replay, fit or probability claim."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'reports/simple_london_v01_02'
OUT = Path(__file__).resolve().parent


def read(name):
    with (RUN / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def describe(rows):
    pnl = [float(r['net_eur']) for r in rows]
    wins = [float(r['R']) for r in rows if float(r['net_eur']) > 0]
    losses = [-float(r['R']) for r in rows if float(r['net_eur']) < 0]
    mean_win = sum(wins) / len(wins) if wins else None
    mean_loss = sum(losses) / len(losses) if losses else None
    return {
        'closed_trades': len(rows), 'closed_net_eur': sum(pnl),
        'mean_cash_R': sum(float(r['R']) for r in rows) / len(rows) if rows else None,
        'win_rate': len(wins) / len(rows) if rows else None,
        'mean_positive_R': mean_win, 'mean_absolute_negative_R': mean_loss,
        'descriptive_payoff_breakeven_win_rate': mean_loss / (mean_win + mean_loss) if mean_win and mean_loss else None,
        'exit_reasons': dict(Counter(r['exit_reason'] for r in rows)),
        'first_entry_utc': rows[0]['entry_utc'] if rows else None,
        'last_exit_utc': rows[-1]['exit_utc'] if rows else None,
    }


def main():
    comparisons = {}
    manifests = {}
    for scenario in ('base', 'higher_costs'):
        short = read('D45_' + scenario + '_TRADES.csv')
        prefix = read('Y2021_' + scenario + '_TRADES.csv')
        key = lambda r: (r['entry_utc'], r['direction'])
        short_by_key, prefix_by_key = {key(r): r for r in short}, {key(r): r for r in prefix}
        assert short_by_key.keys() <= prefix_by_key.keys()
        assert all(short_by_key[k]['net_eur'] == prefix_by_key[k]['net_eur'] for k in short_by_key)
        later = [r for r in prefix if key(r) not in short_by_key]
        comparisons[scenario] = {
            'first_45_days': describe(short), 'known_year_prefix': describe(prefix),
            'after_45_days_before_unknown_position': describe(later),
            'short_window_exact_subset_of_prefix': True,
            'year_total_net_eur': None,
        }
        for label in ('D45', 'Y2021'):
            name = label + '_' + scenario + '_TRADES.csv'
            manifests[name] = hashlib.sha256((RUN / name).read_bytes()).hexdigest()
    base = read('Y2021_base_TRADES.csv')
    start, known_end = datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2021, 4, 1, tzinfo=timezone.utc)
    windows = []
    cursor = start
    while cursor + timedelta(days=30) <= known_end:
        end = cursor + timedelta(days=30)
        selected = [r for r in base if cursor <= datetime.fromisoformat(r['entry_utc'].replace('Z', '+00:00')) < end]
        windows.append({'start_utc': cursor.isoformat(), 'end_utc_exclusive': end.isoformat(),
                        'observed_entries': len(selected),
                        'observed_closed_net_eur': sum(float(r['net_eur']) for r in selected)})
        cursor += timedelta(days=1)
    with (OUT / 'OBSERVED_30D_SUBTRAJECTORIES.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(windows[0]))
        writer.writeheader()
        writer.writerows(windows)
    summary = {
        'analysis_date': '2026-11-04', 'analysis_type': 'Existing records, not a new historical backtest',
        'comparisons': comparisons,
        'thirty_day_observed_subtrajectories': {
            'count': len(windows), 'known_end_exclusive_utc': known_end.isoformat(),
            'best_observed_net': max(windows, key=lambda w: w['observed_closed_net_eur']),
            'worst_observed_net': min(windows, key=lambda w: w['observed_closed_net_eur']),
            'max_observed_entries': max(w['observed_entries'] for w in windows),
            'independent_reset_challenges': False, 'FTMO_pass_probability_estimated': False,
            'warning': 'Overlapping subsets of one observed trajectory, with inherited pauses; not fresh accounts or independent samples.',
        },
        'limitations': [
            'All 2021 data were already used for development',
            'The known annual prefix stops at a missing exposure quote; it is not an annual result',
            'No independent-sample or stationary-process assumption is asserted',
            'Empirical averages and breakeven ratios describe these records, not future success probabilities',
            'FTMO contractual rules remain unverified and no challenge was evaluated',
        ],
        'input_trade_sha256': manifests,
        'strategy_or_risk_changed': False, 'new_market_run': False,
    }
    (OUT / 'PERFORMANCE_FACTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
