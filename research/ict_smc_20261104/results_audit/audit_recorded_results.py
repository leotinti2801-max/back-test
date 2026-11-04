"""Audit recorded ICT fills and causal prior counts; never call a path simulator."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pandas as pd

from backtest_bot.data import market_from_cache
from backtest_bot.reference import D, ROOT


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
RUN = STUDY / 'run_01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def ms(value):
    return int(pd.Timestamp(value).value // 1_000_000)


def close(actual, expected, tolerance=1e-8):
    assert math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=tolerance), (actual, expected)


def main():
    freeze = json.loads((RUN / 'FREEZE_BEFORE_RESULTS.json').read_text())
    results = json.loads((RUN / 'RESULTS.json').read_text())
    manifest = json.loads((RUN / 'MANIFEST_SHA256.json').read_text())
    for rel, expected in manifest.items():
        assert sha(RUN / rel) == expected, rel
    sources = {**freeze['source_sha256'], **freeze['shared_source_sha256']}
    for rel, expected in sources.items():
        assert sha(ROOT / rel) == expected, rel
    cfg = freeze['cfg_risk_controls']
    assert not freeze['adaptive_sizing_enabled'] and not results['adaptive_risk_enabled']
    market, quality = market_from_cache(ROOT / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl')
    bars = D.make_bars(market, 5, 'M5')
    pivots = {p.pid: p for p in D.find_pivots(bars)}
    records, cells, unique = [], {}, set()
    for period in freeze['plan']['periods']:
        for cost in ['base', 'higher_costs']:
            folder = RUN / period['name'] / cost
            trades, events, prior = (read(folder / f'{name}.csv') for name in ['TRADES', 'DECISIONS', 'PRIOR_AT_ENTRY'])
            summary = results['periods'][period['name']][cost]
            assert summary['halt'] is None and summary['closed_trades'] == len(trades)
            assert len(trades) == 1 and len([e for e in events if e['reason'] == 'ENTERED']) == 1
            assert not read(folder / 'LOSSES.csv')
            assert summary['event_counts'] == dict(Counter(e['reason'] for e in events))
            balance = cfg['capital_eur']
            daily_risk, entries = Counter(), Counter()
            for trade in trades:
                entry_ms, exit_ms = ms(trade['entry_utc']), ms(trade['exit_utc'])
                assert ms(period['start']) <= entry_ms < exit_ms < ms(period['end_exclusive'])
                i, j = market.idx(entry_ms), market.idx(exit_ms) - 1
                d, qty = int(trade['direction']), float(trade['qty_eur'])
                assert trade['exit_reason'] == 'TP' and market.present[i:j + 1].all()
                fee = cfg['fee_round_trip_quote'] * (1.5 if cost == 'higher_costs' else 1)
                slip = cfg['slip_quote_per_market_execution'] * (2 if cost == 'higher_costs' else 1)
                fx_entry, fx_exit = market.px['mid_open'][i], market.px['mid_open'][j]
                entry = market.px['ask_open' if d == 1 else 'bid_open'][i] + d * slip
                stop, target = float(trade['stop']), float(trade['target'])
                close(trade['entry_price'], entry)
                risk_unit = (d * (entry - stop) + fee + slip) / fx_entry
                qty_budget = cfg['risk_budget_per_trade_eur'] / risk_unit
                qty_leverage = cfg['leverage_max'] * balance * fx_entry / entry
                close(qty, math.floor(min(qty_budget, qty_leverage) / cfg['qty_step_eur']) * cfg['qty_step_eur'])
                close(trade['planned_risk_eur'], qty * risk_unit)
                assert qty >= cfg['qty_min_eur'] and float(trade['planned_risk_eur']) <= 125
                ratio = (d * (target - entry) - fee) / (d * (entry - stop) + fee + slip)
                close(trade['planned_net_quote_R'], ratio)
                assert ratio >= 2
                spread = market.px['ask_open'][i] - market.px['bid_open'][i]
                assert spread + fee + 2 * slip <= cfg['friction_max_fraction_of_stop'] * d * (entry - stop)
                assert market.first_ts[i] - entry_ms <= cfg['first_tick_max_delay_ms']
                setup = json.loads(trade['setup_at_entry'])
                assert setup['fvg_low'] <= fx_entry <= setup['fvg_high']
                assert setup['mss_pivot_known_at_ms'] <= setup['sweep_known_at_ms'] < setup['mss_known_at_ms'] < entry_ms
                assert (entry_ms - setup['mss_known_at_ms']) <= 30 * D.MIN_MS
                assert (setup['mss_known_at_ms'] - setup['sweep_known_at_ms']) <= 30 * D.MIN_MS
                pivot = pivots[setup['mss_pivot_id']]
                close(setup['mss_level'], pivot.price)
                assert pivot.known_at_ms == setup['mss_pivot_known_at_ms']
                sweep_end = market.idx(setup['sweep_known_at_ms'])
                executable_stop = (market.px['bid_low'][sweep_end - 5:sweep_end].min() - cfg['tick_quote'] if d == 1
                    else market.px['ask_high'][sweep_end - 5:sweep_end].max() + cfg['tick_quote'])
                close(stop, executable_stop)
                day = pd.Timestamp(entry_ms, unit='ms', tz='UTC').tz_convert('Europe/London').date()
                bound = [ms(pd.Timestamp(f'{day} {clock}', tz='Europe/London')) for clock in ['08:00', '09:00', '14:30', '16:00']]
                a, b = market.idx(bound[0]), market.idx(bound[1])
                assert market.present[a:b].all() and bound[1] < entry_ms < bound[2] and exit_ms <= bound[3]
                expected_target = market.px['bid_high'][a:b].max() if d == 1 else market.px['ask_low'][a:b].min()
                close(target, expected_target)
                extreme = market.px['bid_high' if d == 1 else 'ask_low'][j]
                assert d * (extreme - target) >= cfg['tick_quote'] - 1e-12
                adverse = market.px['bid_low' if d == 1 else 'ask_high'][j]
                assert d * (adverse - stop) > 0 and trade['ambiguous_stop_and_target'] == 'False'
                net = qty * (-0.5 * fee / fx_entry + (d * (target - entry) - 0.5 * fee) / fx_exit)
                close(trade['net_eur'], net)
                close(trade['R'], net / (qty * risk_unit))
                balance += net
                close(trade['balance_after_eur'], balance)
                daily_risk[trade['day']] += float(trade['planned_risk_eur'])
                entries[trade['day']] += 1
                unique.add((trade['entry_utc'], trade['direction']))
                records.append({'period': period['name'], 'costs': cost, 'entry_utc': trade['entry_utc'],
                    'exit_quote_row_utc': D.iso(market.t(j)), 'target': target, 'entry': entry, 'qty_eur': qty,
                    'entry_fx': float(fx_entry), 'exit_fx': float(fx_exit), 'recomputed_net_eur': float(net),
                    'recorded_net_eur': float(trade['net_eur']), 'cash_error_eur': float(net - float(trade['net_eur'])),
                    'observed_target_extreme': float(extreme), 'planned_net_quote_R': ratio})
            assert max(daily_risk.values(), default=0) <= 500 and max(entries.values(), default=0) <= 4
            close(summary['net_eur'], balance - cfg['capital_eur'])
            close(summary['known_closed_net_eur'], sum(float(t['net_eur']) for t in trades))
            for p in prior:
                prior_trades = [t for t in trades if int(t['closed_at_ms']) <= int(p['entry_ms'])]
                wins = sum(float(t['net_eur']) > 0 for t in prior_trades)
                assert int(p['prior_n']) == len(prior_trades) and int(p['prior_wins']) == wins
                close(p['laplace_win_probability_diagnostic'], (wins + 1) / (len(prior_trades) + 2))
                assert p['probability_tradeable'] == 'False' and p['independent_calibration_verified'] == 'False'
                close(p['risk_multiplier'], 1)
                if p['decision'] == 'ENTERED':
                    assert p['prior_n'] == '0' and p['prior_wins'] == '0'
            env = read(folder / 'LIQUIDATION_ENVELOPES.csv')
            assert len({e['t_utc'] for e in env}) == len(env)
            for e in env:
                assert float(e['liquidation_low_eur']) <= float(e['liquidation_mark_eur']) <= float(e['liquidation_high_eur'])
            close(env[-1]['liquidation_mark_eur'], balance)
            cells[f"{period['name']}/{cost}"] = {'status': 'PASS', 'closed_trades': len(trades),
                'net_eur': summary['net_eur'], 'halt': None, 'priors_checked': len(prior),
                'all_observed_exposure_minutes_present': True, 'daily_risk_max': max(daily_risk.values(), default=0)}
    baseline = json.loads((ROOT / 'research/chart_context_20261104/run_01/RESULTS.json').read_text())
    same_period = {cost: {'ICT_Q1_net_eur': results['periods']['Q1'][cost]['net_eur'],
        'range_2R_Q1_net_eur': baseline['variants']['V03_2R'][cost]['net_eur']}
        for cost in ['base', 'higher_costs']}
    payload = {'status': 'PASS', 'cells': cells, 'audited_trade_rows_correlated': len(records),
        'unique_executed_market_entries': len(unique), 'result_files_verified': len(manifest),
        'source_identities_verified': len(sources), 'audit_script_sha256': sha(Path(__file__)),
        'run_manifest_sha256': sha(RUN / 'MANIFEST_SHA256.json'), 'same_period_Q1_comparison_only': same_period,
        'annual_halt_absent_does_not_certify_all_market_opportunities': True,
        'new_financial_backtest': False, 'path_simulator_called': False,
        'cash_audit_method': 'Recompose only recorded TP fill from fixed entry/exit quotes, fee halves and each fill FX; no alternative path generated',
        'limits': ['Four scenario rows represent one unique market entry, not four independent observations',
            'Risk quotas/pause preserved by unchanged core; no two-loss pause exercised by these one-trade outputs',
            'Signal gaps and unavailable ranges mean total market opportunity completeness remains uncertified',
            'No FTMO contractual equity or tick ordering certified']}
    (HERE / 'AUDIT_RESULTS.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    with (HERE / 'RECORDED_FILL_RECONCILIATION.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0]); writer.writeheader(); writer.writerows(records)
    print(json.dumps({'status': 'PASS', 'cells': len(cells), 'unique_entries': len(unique),
        'max_cash_error': max(abs(r['cash_error_eur']) for r in records)}, indent=2))


if __name__ == '__main__':
    main()
