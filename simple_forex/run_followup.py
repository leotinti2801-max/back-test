"""Finite follow-up; preserve failures and never choose a winner automatically."""
import argparse
import hashlib
import json
from pathlib import Path

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from simple_forex.runner import simulate
from simple_forex.strategy import signals as old_signal
from simple_forex.strategy_rearmed import signals as rearmed_signal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    here = Path(__file__).resolve().parent
    protocol = json.loads((here / 'followup_protocol.json').read_text())
    paths = [*sorted(here.glob('*.py')), here / 'followup_protocol.json']
    identity = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json',
               {'protocol': protocol, 'source_sha256': identity, 'shared_source_sha256': code_identity()})
    mk, _ = market_from_cache(args.cache)
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    results = {}
    for variant in protocol['variants']:
        cfg, name = variant['config'], variant['name']
        signal = old_signal if variant['signal'] == 'v01' else rearmed_signal
        results[name] = {}
        for period in cfg['historical_periods']:
            results[name][period['name']] = {}
            for cost, stress in [('base', False), ('higher_costs', True)]:
                summary, trades, events, envelopes = simulate(
                    mk, cfg, reference, epoch_ms(period['start']), epoch_ms(period['end_exclusive']),
                    stress, signal_source=signal)
                n = summary['closed_trades']
                summary['observed_closed_win_rate'] = summary['wins'] / n if n else None
                summary['max_real_entries_same_day'] = max((sum(t['day'] == day for t in trades)
                    for day in {t['day'] for t in trades}), default=0)
                results[name][period['name']][cost] = summary
                prefix = name + '_' + period['name'] + '_' + cost
                for suffix, rows in [('TRADES', trades), ('DECISIONS', events), ('LIQUIDATION_ENVELOPES', envelopes)]:
                    write_csv(args.output / (prefix + '_' + suffix + '.csv'), rows)
                print(prefix, 'N', n, 'win', summary['observed_closed_win_rate'],
                      'net', summary['net_eur'], 'known', summary['known_closed_net_eur'], flush=True)
    write_json(args.output / 'RESULTS.json', {'variants': results, 'winner_selected': None,
                '80pct_validated': False, 'independent_validation': False, 'FTMO_pass_claimed': False})
    for name, digest in identity.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Source changed during study')
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.iterdir()) if p.is_file()})


if __name__ == '__main__':
    main()
