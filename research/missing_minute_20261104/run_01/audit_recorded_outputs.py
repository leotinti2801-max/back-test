"""Audit already-recorded outputs only. No market loader, simulator or bootstrap call."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
STUDY = OUT.parent
ROOT = STUDY.parents[1]


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ms(text):
    return int(datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp() * 1000)


def iso(t):
    return datetime.fromtimestamp(int(t) / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def close(a, b, tolerance=1e-8):
    assert abs(float(a) - float(b)) <= tolerance, (a, b)


def audit():
    frozen = read(STUDY / 'FREEZE_BEFORE_RESULTS.json')
    file_checks = 0
    for rel, digest in frozen['frozen_files_sha256'].items():
        assert sha(ROOT / rel) == digest, ('frozen', rel)
        file_checks += 1
    for rel, digest in read(OUT / 'MANIFEST_SHA256.json').items():
        assert sha(OUT / rel) == digest, ('result', rel)
        file_checks += 1
    meta = read(OUT / 'POST_RUN_ENVIRONMENT_AND_DRAWS.json')
    assert meta['evaluation_completed_without_exception'] is True
    assert meta['versions_at_invocation'] == meta['versions_after_invocation'] == frozen['runtime']
    assert meta['recomputed_draw_identity'] == frozen['bootstrap_calendar_draws_before_prices']
    assert meta['freeze_sha256_after'] == sha(STUDY / 'FREEZE_BEFORE_RESULTS.json')
    full = read(OUT / 'RESULTS.json')['strategies']
    cells, unique_gaps, compared_witness_rows = [], set(), 0
    totals, envelope_rows = 0, 0
    for name, runs in full.items():
        for label, result in runs.items():
            scenario, costs = label.split('/')
            folder = OUT / name / scenario / costs
            trades = rows(folder / 'TRADES.csv')
            control = rows(folder / 'CONTROL_TRADES.csv')
            evaluation = rows(folder / 'EVALUATION_TRADES.csv')
            assert control + evaluation == trades
            witness = rows(STUDY / f'WITNESS_{name}_{scenario}_{costs}_TRADES.csv')
            assert len(control) == len(witness) == 61
            for actual, expected in zip(control, witness, strict=True):
                for field in expected:
                    try:
                        a, b = float(actual[field]), float(expected[field])
                    except ValueError:
                        assert actual[field] == expected[field], field
                    else:
                        close(a, b)
                compared_witness_rows += 1
            for key, ledger in [('control', control), ('evaluation', evaluation)]:
                block = result[key]
                assert len(ledger) == block['closed_trades']
                assert all(block['start'] <= t['entry_utc'] < block['end_exclusive'] for t in ledger)
                close(sum(float(t['net_eur']) for t in ledger), block['known_closed_net_eur'])
                if block['complete']:
                    close(block['net_eur'], block['known_closed_net_eur'])
                else:
                    assert block['net_eur'] is None
                if ledger:
                    close(sum(float(t['R']) for t in ledger) / len(ledger), block['mean_R_per_closed_trade'])
            summary = result['full_summary']
            assert len(trades) == summary['closed_trades']
            close(sum(float(t['net_eur']) for t in trades), summary['known_closed_net_eur'])
            close(result['control']['known_closed_net_eur'] + result['evaluation']['known_closed_net_eur'], summary['known_closed_net_eur'])
            balance, previous_close, losses, pause_until = 100000.0, 0, 0, 0
            daily_count, daily_risk = Counter(), defaultdict(float)
            by_entry = {}
            for trade in trades:
                entry, closed = ms(trade['entry_utc']), int(trade['closed_at_ms'])
                assert entry >= previous_close and closed >= entry
                if pause_until and entry >= pause_until:
                    losses, pause_until = 0, 0
                assert entry >= pause_until
                risk, net = float(trade['planned_risk_eur']), float(trade['net_eur'])
                assert 0 < risk <= 125 + 1e-8
                close(net / risk, trade['R'])
                daily_count[trade['day']] += 1
                daily_risk[trade['day']] += risk
                balance += net
                close(balance, trade['balance_after_eur'])
                losses = losses + 1 if net < 0 else 0 if net > 0 else losses
                if losses >= 2:
                    pause_until = closed + 86400000
                previous_close = closed
                by_entry[entry] = trade
            assert max(daily_count.values(), default=0) <= 4
            assert max(daily_risk.values(), default=0) <= 500 + 1e-8
            gaps = rows(folder / 'GAPS_ENCOUNTERED.csv')
            absent_envelopes = set()
            for gap in gaps:
                trade = by_entry[int(gap['entry_ms'])]
                first, resume = int(gap['first_missing_ms']), int(gap['resume_ms'])
                assert int(gap['entry_ms']) < first < resume <= int(trade['closed_at_ms'])
                assert resume - first == int(gap['missing_minutes']) * 60000
                assert gap['scenario'] == scenario and gap['resolution'] == 'R1'
                assert 1 <= int(gap['missing_minutes']) <= 5
                if scenario != 'S_CONT':
                    assert int(trade['closed_at_ms']) == resume
                    assert trade['exit_reason'] == 'R1_' + scenario
                for t in range(first, resume, 60000):
                    absent_envelopes.add((trade['entry_utc'], iso(t)))
                unique_gaps.add((first, resume))
            with (folder / 'LIQUIDATION_ENVELOPES.csv').open(newline='') as stream:
                for row in csv.DictReader(stream):
                    assert (row['entry_utc'], row['t_utc']) not in absent_envelopes
                    envelope_rows += 1
            decisions = rows(folder / 'DECISIONS.csv')
            assert sum(d['reason'] == 'ENTERED' for d in decisions) == len(trades)
            r3 = sum('ENTRY_QUOTE_MISSING_REFUSED' in d.get('refusal_reasons', '') for d in decisions)
            cells.append({'strategy': name, 'scenario': scenario, 'costs': costs,
                'closed_trades': len(trades), 'control': len(control), 'evaluation': len(evaluation),
                'exposure_gaps': len(gaps), 'R3_refusals': r3, 'halt': result['halt'], 'status': 'PASS'})
            totals += len(trades)
    inference = read(OUT / 'INFERENCE_AND_VERDICTS.json')
    complete = {name: all(r['halt'] is None for r in runs.values()) for name, runs in full.items()}
    if all(complete.values()):
        raw = {name: inference['diagnostics'][name]['p_raw_user_rule'] for name in full}
        ordered = sorted(raw, key=lambda n: (raw[n], n))
        first = min(1, 2 * raw[ordered[0]])
        adjusted = {ordered[0]: first, ordered[1]: max(first, raw[ordered[1]])}
        for name in full:
            close(inference['diagnostics'][name]['p_adjusted_Holm'], adjusted[name])
            count = raw[name] * 5001 - 1
            close(count, round(count))
            assert 0 <= round(count) <= 5000
    else:
        assert all(inference['diagnostics'][name]['p_adjusted_Holm'] is None for name in full)
    for name, runs in full.items():
        cont = runs['S_CONT/higher_costs']['evaluation']
        pess = runs['S_PESS/higher_costs']['evaluation']
        if not complete[name]:
            expected = 'NON CONCLUANT'
        elif cont['net_eur'] <= 0:
            expected = 'ARRÊT'
        elif cont['closed_trades'] < 100:
            expected = 'NON CONCLUANT'
        elif (all(complete.values()) and cont['mean_R_per_closed_trade'] >= .05
              and inference['diagnostics'][name]['p_adjusted_Holm'] < .05 and pess['net_eur'] > 0):
            expected = 'CANDIDAT À COLLECTE PROSPECTIVE'
        else:
            expected = 'TESTÉ NON VALIDÉ'
        assert inference['verdicts'][name] == expected
    return {'status': 'PASS', 'performed_by': 'Codex; recorded-output audit, not independent strategy validation',
        'hashes_verified': file_checks, 'cells': cells, 'trade_rows_checked_correlated': totals,
        'witness_rows_compared': compared_witness_rows, 'envelope_rows_checked': envelope_rows,
        'unique_exposure_gaps_UTC': [[iso(a), iso(b)] for a,b in sorted(unique_gaps)],
        'frozen_files_unchanged': True, 'runtime_and_draw_fingerprint_match_freeze': True,
        'Holm_and_priority_checked_from_recorded_values': True,
        'new_simulations': 0, 'performance_bootstrap_recomputed': False, 'market_cache_loaded': False,
        'limitations': ['No independent reexecution of bootstrap metrics or tick-path reconstruction',
            'Scenarios are not guaranteed portfolio bounds; data remains previously consulted development']}


if __name__ == '__main__':
    result = audit()
    destination = OUT / 'POST_RUN_AUDIT.json'
    if destination.exists():
        raise RuntimeError('Do not overwrite existing audit')
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ['status','hashes_verified','trade_rows_checked_correlated',
        'witness_rows_compared','envelope_rows_checked','unique_exposure_gaps_UTC']}, indent=2))
