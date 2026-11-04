"""Explain observed losses and changed entries without imputing refused-trade PnL."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from backtest_bot.research import write_csv, write_json


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def key(row):
    return row['entry_utc'], row['direction']


def main():
    here = Path(__file__).resolve().parent
    source, output = here / 'comparison_01', here / 'diagnostic_01'
    output.mkdir()
    summary, losses = {}, []
    for costs in ['base', 'higher_costs']:
        baseline = {key(row): row for row in read(source / f'V03_{costs}_TRADES.csv')}
        candidate = {key(row): row for row in read(source / f'EMA20_50_{costs}_TRADES.csv')}
        decisions = read(source / f'EMA20_50_{costs}_DECISIONS.csv')
        missing = []
        for event in decisions:
            if event['reason'] == 'FILTER_UNKNOWN_EMA_WARMUP':
                missing.append({**event, 'interpretation': 'Indicator unavailable after incomplete M5; not evidence of bad market direction'})
        write_csv(output / f'{costs}_UNKNOWN_FILTER.csv', missing)
        removed, added = sorted(baseline.keys() - candidate.keys()), sorted(candidate.keys() - baseline.keys())
        write_csv(output / f'{costs}_CHANGED_ENTRIES.csv', [
            {'entry_utc': t, 'direction': d, 'membership': label}
            for label, keys in [('BASELINE_ONLY', removed), ('CANDIDATE_ONLY', added)] for t, d in keys])
        summary[costs] = {'baseline_entries': len(baseline), 'candidate_entries': len(candidate),
            'shared_entries': len(baseline.keys() & candidate.keys()),
            'baseline_only': len(removed), 'candidate_only': len(added),
            'filter_unknown_decisions': len(missing)}
        for strategy, trades in [('V03', baseline), ('EMA20_50', candidate)]:
            negative = [row for row in trades.values() if float(row['net_eur']) < 0]
            summary[costs][strategy + '_losses_by_exit'] = dict(Counter(row['exit_reason'] for row in negative))
            for row in negative:
                reason = row['exit_reason']
                explanation = ('Stop opposé au range atteint selon les cotations et la priorité stop du moteur.'
                    if reason == 'SL' else
                    'Sortie horaire : valeur nette négative à la clôture forcée, coûts inclus.'
                    if reason == 'TIME' else 'Résultat net négatif observé ; consulter le journal de flux.')
                losses.append({'strategy': strategy, 'costs': costs, **row,
                    'observed_explanation': explanation,
                    'limit': 'Cause mécanique constatée ; aucune cause macro ou probabilité de rebond déduite.'})
    write_csv(output / 'EVERY_OBSERVED_LOSS.csv', losses)
    write_json(output / 'SUMMARY.json', summary)
    write_json(output / 'PROVENANCE.json', {'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_manifest_sha256': hashlib.sha256((source / 'MANIFEST_SHA256.json').read_bytes()).hexdigest(),
        'new_simulation': False, 'refused_trade_outcomes_invented': False,
        'removed_baseline_trades_not_summed_as_filter_profit': True})
    write_json(output / 'MANIFEST_SHA256.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.iterdir() if p.is_file()})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
