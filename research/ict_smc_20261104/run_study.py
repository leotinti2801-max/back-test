"""Execute the one frozen ICT hypothesis, both costs, without probability tuning."""
import argparse
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import talib
from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT, D
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from strategy import ICT
from engine import simulate
from probability import summarize_prior


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    here = Path(__file__).resolve().parent
    plan = json.loads((here / 'PLAN_BEFORE_RESULTS.json').read_text())
    cfg = json.loads((ROOT / 'simple_forex/protocol_v04.json').read_text())
    cfg.update(version=plan['study'], live_trading_enabled=False)
    ref = json.loads((ROOT / 'config/reference_params.json').read_text())
    paths = [*here.glob('*.py'), *here.glob('probability/*.py'), here / 'PLAN_BEFORE_RESULTS.json',
        ROOT / 'research/indicator_study_20261104/lab/features.py', ROOT / 'simple_forex/protocol_v04.json',
        ROOT / 'simple_forex/runner.py']
    identity = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    shared = code_identity()
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {'plan': plan, 'cfg_risk_controls': cfg,
        'source_sha256': identity, 'shared_source_sha256': shared,
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
            'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode(),
            'ATR_unstable': talib.get_unstable_period('ATR'), 'compatibility': talib.get_compatibility()},
        'independent_validation': False, 'adaptive_sizing_enabled': False})
    mk, quality = market_from_cache(args.cache)
    model = ICT(mk)
    results, comparisons = {}, []
    for period in plan['periods']:
        results[period['name']] = {}
        for costs, stress in [('base', False), ('higher_costs', True)]:
            summary, trades, events, envelopes = simulate(mk, cfg, ref, epoch_ms(period['start']),
                epoch_ms(period['end_exclusive']), stress, signal_source=model.signals)
            n = len(trades)
            summary.update(observed_closed_win_rate=summary['wins'] / n if n else None,
                mean_net_eur_per_closed_trade=summary['known_closed_net_eur'] / n if n else None,
                mean_realized_R=sum(t['R'] for t in trades) / n if n else None,
                closed_exits=dict(Counter(t['exit_reason'] for t in trades)),
                negative_exits=dict(Counter(t['exit_reason'] for t in trades if t['net_eur'] < 0)),
                account_refusals_nonexclusive=dict(Counter(r for e in events for r in e.get('refusal_reasons', []))),
                MSS_rejections_nonexclusive=dict(Counter(r for e in events for r in e.get('rejection_reasons', []))),
                max_executed_entries_per_day=max(Counter(e['day'] for e in events if e['reason'] == 'ENTERED').values(), default=0),
                probability_forecast_calibrated=False, risk_multiplier=1)
            folder = args.output / period['name'] / costs
            folder.mkdir(parents=True)
            prior = [{'entry_utc': D.iso(e['decision_ms']), 'decision': e['reason'],
                'direction': e['direction'], **summarize_prior(trades, e['decision_ms'])}
                for e in events if e['reason'] in ('ENTERED', 'REFUSED')]
            losses = [{**t, 'mechanical_loss_reason': 'ORIGINAL_STOP_TOUCHED' if t['exit_reason'].startswith('SL')
                else 'NEGATIVE_NET_AT_16_LONDON', 'causal_limit': 'No inferred institutional or macro cause'}
                for t in trades if t['net_eur'] < 0]
            for label, rows in [('TRADES', trades), ('DECISIONS', events), ('LOSSES', losses),
                ('PRIOR_AT_ENTRY', prior), ('LIQUIDATION_ENVELOPES', envelopes)]:
                write_csv(folder / (label + '.csv'), rows)
            results[period['name']][costs] = summary
            comparisons.append({'period': period['name'], 'costs': costs, **{k: summary[k] for k in
                ['closed_trades', 'wins', 'losses', 'observed_closed_win_rate', 'known_closed_net_eur',
                 'net_eur', 'closed_drawdown_eur', 'mean_realized_R', 'max_executed_entries_per_day']},
                'halt': summary['halt']})
            print(period['name'], costs, 'N', n, 'wins', summary['wins'], 'net', summary['net_eur'],
                'known', summary['known_closed_net_eur'], 'halt', summary['halt'], flush=True)
    write_json(args.output / 'RESULTS.json', {'periods': results, 'cache_quality': quality,
        'FTMO_pass_claimed': False, 'independent_validation': False, 'adaptive_risk_enabled': False,
        'strategy_promoted': False, 'stop_after_this_batch': True})
    write_csv(args.output / 'COMPARISON.csv', comparisons)
    for relative, expected in {**identity, **shared}.items():
        assert digest(ROOT / relative) == expected
    write_json(args.output / 'MANIFEST_SHA256.json', {str(p.relative_to(args.output)): digest(p)
        for p in args.output.rglob('*') if p.is_file()})


if __name__ == '__main__':
    main()
