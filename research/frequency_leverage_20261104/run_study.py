"""Finite, predeclared frequency/leverage study; no promotion or broker access."""
import argparse
import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT, D, X
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from engine import simulate, parameters
from signals import configured


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_sizing(market, trades, cfg, ref, stress):
    rows, balance = [], cfg['capital_eur']
    for trade in trades:
        i = market.idx(epoch_ms(trade['entry_utc']))
        fx = float(market.px['mid_open'][i])
        params = parameters(ref, cfg, market.t(i + 1), stress)
        direction, entry = trade['direction'], trade['entry_price']
        fee, slip = params['costs']['fee_round_trip_quote'], params['costs']['slip_quote_per_market_execution']
        risk_unit = (direction * (entry - trade['stop']) + fee + slip) / fx
        qty, budget, leverage = X.size_position(params, risk_unit, balance, fx, entry)
        assert qty == trade['qty_eur']
        rows.append({'entry_utc': trade['entry_utc'], 'direction': direction,
            'balance_before_eur': balance, 'entry_fx': fx, 'qty_risk_budget': budget,
            'qty_leverage_cap': leverage, 'qty_executed': qty,
            'leverage_cap_binding_before_rounding': leverage < budget,
            'effective_model_leverage': qty * entry / fx / balance})
        balance += trade['net_eur']
    return rows


def observed_diagnostics(trades, events, summary, cfg):
    entries = Counter(e['day'] for e in events if e['reason'] == 'ENTERED')
    summary.update(observed_closed_win_rate=summary['wins'] / len(trades) if trades else None,
        maximum_executed_entries_per_day=max(entries.values(), default=0),
        days_with_executed_entry=len(entries),
        closed_exits=dict(Counter(t['exit_reason'] for t in trades)),
        negative_exits=dict(Counter(t['exit_reason'] for t in trades if t['net_eur'] < 0)),
        refusal_reasons_nonexclusive=dict(Counter(reason for e in events for reason in e.get('refusal_reasons', []))),
        net_pct_initial_capital=summary['net_eur'] / cfg['capital_eur'] * 100 if summary['net_eur'] is not None else None,
        mean_realized_R=sum(t['R'] for t in trades) / len(trades) if trades else None,
        days_with_more_than_two_entries=sum(count > 2 for count in entries.values()))
    losses = []
    for t in trades:
        if t['net_eur'] >= 0:
            continue
        why = ('Stop range touché selon le moteur ; gap défavorable pris en compte.'
            if t['exit_reason'].startswith('SL') else
            'Sortie à la limite de durée ou de séance : résultat net négatif, coûts inclus.'
            if t['exit_reason'] == 'TIME' else 'Perte nette observée ; consulter les flux.')
        losses.append({**t, 'observed_mechanical_explanation': why,
            'limit': 'No inferred macro cause or hindsight indicator filter'})
    return losses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new directory; previous experiments are immutable')
    here = Path(__file__).resolve().parent
    plan = json.loads((here / 'PLAN_BEFORE_RESULTS.json').read_text())
    original = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
    ref = json.loads((ROOT / 'config/reference_params.json').read_text())
    paths = [*here.glob('*.py'), here / 'PLAN_BEFORE_RESULTS.json',
        ROOT / 'simple_forex/protocol_v03.json', ROOT / 'simple_forex/strategy_rearmed.py',
        ROOT / 'simple_forex/runner.py']
    identity = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    shared = code_identity()
    args.output.mkdir(parents=True)
    write_json(args.output / 'FREEZE_BEFORE_RESULTS.json', {'plan': plan,
        'source_sha256': identity, 'shared_source_sha256': shared,
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
        'active_core_modified': False, 'independent_validation': False, 'FTMO_compliance_verified': False})
    market, quality = market_from_cache(args.cache)
    results, table = {}, []
    for variant in plan['variants']:
        name, results_variant = variant['name'], {}
        cfg = {**original, **variant['overrides'], 'research_max_holding_minutes': variant['max_holding_minutes']}
        assert cfg['max_planned_daily_risk_eur'] == 500 and cfg['max_open_positions'] == 1
        signal = configured(cfg, variant['signal_minutes'])
        for period in [plan['common_period'], *plan['diagnostic_attempts']]:
            results_period = {}
            for costs, stress in [('base', False), ('higher_costs', True)]:
                summary, trades, events, envelopes = simulate(market, cfg, ref,
                    epoch_ms(period['start']), epoch_ms(period['end_exclusive']), stress,
                    signal_source=signal)
                losses = observed_diagnostics(trades, events, summary, cfg)
                sizing = audit_sizing(market, trades, cfg, ref, stress)
                summary.update(leverage_cap_binding_closed_trades=sum(r['leverage_cap_binding_before_rounding'] for r in sizing),
                    maximum_effective_model_leverage=max((r['effective_model_leverage'] for r in sizing), default=None))
                folder = args.output / name / period['name'] / costs
                folder.mkdir(parents=True)
                for suffix, rows in [('TRADES', trades), ('DECISIONS', events),
                    ('LIQUIDATION_ENVELOPES', envelopes), ('LOSSES', losses), ('SIZING_AUDIT', sizing)]:
                    write_csv(folder / (suffix + '.csv'), rows)
                results_period[costs] = summary
                table.append({'variant': name, 'period': period['name'], 'costs': costs,
                    **{k: summary[k] for k in ['closed_trades', 'wins', 'losses', 'observed_closed_win_rate',
                        'known_closed_net_eur', 'net_eur', 'net_pct_initial_capital', 'closed_drawdown_eur',
                        'maximum_executed_entries_per_day', 'days_with_more_than_two_entries']},
                    'halt_reason': summary['halt']['reason'] if summary['halt'] else ''})
                print(name, period['name'], costs, 'N', len(trades), 'net', summary['net_eur'],
                    'max/day', summary['maximum_executed_entries_per_day'],
                    'halt', summary['halt']['reason'] if summary['halt'] else None, flush=True)
            results_variant[period['name']] = results_period
        results[name] = results_variant
    # Reproduction of the baseline, not an additional performance discovery.
    previous = ROOT / 'research/indicator_study_20261104/lab/comparison_01'
    for costs in ['base', 'higher_costs']:
        assert (args.output / 'V03/Q1' / costs / 'TRADES.csv').read_bytes() == (previous / f'V03_{costs}_TRADES.csv').read_bytes()
        assert (args.output / 'V03/Q1' / costs / 'DECISIONS.csv').read_bytes() == (previous / f'V03_{costs}_DECISIONS.csv').read_bytes()
    write_csv(args.output / 'COMPARISON.csv', table)
    write_json(args.output / 'RESULTS.json', {'variants': results, 'cache_quality': quality,
        'winner_selected': None, 'active_strategy_unchanged': True, 'FTMO_pass_claimed': False,
        'independent_validation': False, 'attempts_not_independent_of_Q1': True,
        'annual_total_still_unknown': True})
    for relative, expected in {**identity, **shared}.items():
        assert digest(ROOT / relative) == expected
    write_json(args.output / 'MANIFEST_SHA256.json', {str(p.relative_to(args.output)): digest(p)
        for p in args.output.rglob('*') if p.is_file()})


if __name__ == '__main__':
    main()
