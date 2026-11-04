"""One frozen entry method, three predeclared targets; no winner selection."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from simple_forex.runner import simulate
from simple_forex.strategy_v02 import signals

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output exists: use a new directory')
    cfg = json.loads((HERE / 'protocol_v02.json').read_text())
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    paths = [*sorted(HERE.glob('*.py')), HERE / 'protocol_v01.json', HERE / 'protocol_v02.json']
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {
        'protocol': cfg, 'source_sha256': sources, 'shared_source_sha256': code_identity(),
        'principal_target_fixed_before_results': 3.0, 'independent_validation': False,
        'automatic_winner_selection': False,
    })
    mk, quality = market_from_cache(args.cache)
    # Regression is needed because the common replay now accepts an injected signal.
    v1 = json.loads((HERE / 'protocol_v01.json').read_text())
    original = ROOT / 'reports/simple_london_v01_02'
    period = v1['historical_periods'][0]
    regression, ts, _, _ = simulate(mk, v1, reference, epoch_ms(period['start']), epoch_ms(period['end_exclusive']))
    expected = json.loads((original / 'RESULTS.json').read_text())['periods']['D45']['base']
    if regression != expected:
        raise AssertionError('V01 default replay no longer reproduces its reference')
    write_csv(args.output / 'V01_REGRESSION_TRADES.csv', ts)
    if (args.output / 'V01_REGRESSION_TRADES.csv').read_bytes() != (original / 'D45_base_TRADES.csv').read_bytes():
        raise AssertionError('V01 trade ledger changed')
    results = {}
    for rr in cfg['targets_to_compare']:
        target_cfg = copy.deepcopy(cfg)
        target_cfg['planned_quote_reward_risk'] = rr
        label = f'{rr:g}R'
        results[label] = {}
        for period in cfg['historical_periods']:
            results[label][period['name']] = {}
            for cost, stress in [('base', False), ('higher_costs', True)]:
                m, trades, events, envelopes = simulate(
                    mk, target_cfg, reference, epoch_ms(period['start']),
                    epoch_ms(period['end_exclusive']), stress, signal_source=signals)
                n = m['closed_trades']
                m.update(observed_closed_win_rate=m['wins'] / n if n else None,
                         net_zero_trades=n - m['wins'] - m['losses'],
                         sample_sufficient_for_review=n >= cfg['min_closed_trades_for_win_rate_review'],
                         mean_realized_R=sum(t['R'] for t in trades) / n if n else None,
                         observed_80pct_goal_met=(m['wins'] / n >= 0.8) if n else None,
                         win_rate_80pct_validated=False)
                results[label][period['name']][cost] = m
                prefix = label + '_' + period['name'] + '_' + cost
                write_csv(args.output / (prefix + '_TRADES.csv'), trades)
                write_csv(args.output / (prefix + '_DECISIONS.csv'), events)
                write_csv(args.output / (prefix + '_LIQUIDATION_ENVELOPES.csv'), envelopes)
                print(prefix, 'N', n, 'win_rate', m['observed_closed_win_rate'], 'net', m['net_eur'],
                      'known_prefix_net', m['known_closed_net_eur'],
                      'halt', m['halt']['reason'] if m['halt'] else None, flush=True)
    write_json(args.output / 'RESULTS.json', {
        'strategy': cfg['version'], 'principal_target': '3R', 'targets': results,
        'cache_quality': quality, 'V01_regression_passed': True,
        'winner_selected': None, 'FTMO_pass_claimed': False,
        'independent_holdout_available': False,
        'warning': '2021 already consulted. Known-prefix win rates are conditional when a branch halts; no 80% guarantee.',
    })
    if sources != {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}:
        raise RuntimeError('Source changed during replay')
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.iterdir()) if p.is_file()})


if __name__ == '__main__':
    main()
