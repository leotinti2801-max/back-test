"""Replay only the chosen EURUSD strategy, without retuning historical rules.

The two execution-cost scenarios are the same strategy, not two candidates.
The currently supported cache is the already-consulted 2021 development history.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT
from backtest_bot.research import code_identity, epoch_ms, write_csv, write_json
from backtest_bot.strategy import build_context, make_params, shared_structures

sys.path.insert(0, str(Path(__file__).resolve().parent))
from focused_diagnostics import run_diagnosed


CHARTER = ROOT / 'research/forex_single_strategy/STRATEGY_CHARTER.json'


def load_focus():
    focus = json.loads(CHARTER.read_text())
    if focus['strategy_count'] != 1 or focus['live_trading_enabled']:
        raise ValueError('This launcher supports one research strategy, with live trading disabled')
    path = ROOT / focus['source_freeze_relative_path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != focus['source_freeze_sha256']:
        raise ValueError('Historical protocol differs from the chosen research charter')
    freeze = json.loads(path.read_text())
    if freeze['source_sha256'] != code_identity():
        raise ValueError('Historical source/configuration changed; a new explicit protocol is required')
    matches = [c for c in freeze['protocol']['candidates'] if c == focus['candidate']]
    if len(matches) != 1 or focus['fixed_controls'] != freeze['protocol']['fixed_controls']:
        raise ValueError('Focused strategy or fixed controls differ from the reviewed version')
    return focus, freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    focus, freeze = load_focus()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    identity = code_identity()
    args.output.mkdir(parents=True)
    write_json(args.output / 'FOCUS_BEFORE_RESULTS.json', {
        'charter': focus, 'charter_sha256': hashlib.sha256(CHARTER.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_sha256': identity,
        'diagnostic_source_sha256': hashlib.sha256(
            (Path(__file__).resolve().parent / 'focused_diagnostics.py').read_bytes()).hexdigest(),
        'new_independent_market_data': False,
    })
    mk, quality = market_from_cache(args.cache)
    reference = json.loads((ROOT / 'config/reference_params.json').read_text())
    structures = shared_structures(mk, reference)
    candidate, controls = focus['candidate'], focus['fixed_controls']
    results, trades, decisions, audits = {}, [], [], {}
    for name, stress in [('base', False), ('higher_costs', True)]:
        params = make_params(reference, controls, candidate, stress=stress,
                             stress_spec=freeze['protocol']['stress'])
        ctx = build_context(mk, params, controls, candidate, structures)
        (summary, ts, ds), audit = run_diagnosed(
            ctx, params, candidate, controls, epoch_ms('2021-01-01T00:00:00Z'),
            mk.end_ms, scenario=name)
        audit.write_outputs(args.output)
        audits[name] = audit.reconciliation
        results[name] = summary
        trades.extend({'candidate': candidate['name'], 'scenario': name, **t} for t in ts)
        decisions.extend({'candidate': candidate['name'], 'scenario': name, **d} for d in ds)
        print(candidate['name'], name, 'trades', summary['closed_trades'], 'net', summary['net_eur'], flush=True)
        print('Diagnostic', name, audit.reconciliation['audit_status'],
              'BOS', audit.reconciliation['bos_rows'],
              'setup outcomes', audit.reconciliation['setup_terminal_states'], flush=True)
    write_json(args.output / 'RESULTS.json', {
        'strategy_count': 1, 'candidate': candidate, 'scenarios': results, 'cache_quality': quality,
        'independent_validation': False, 'live_trading_enabled': False,
        'causal_diagnostics': {name: a['audit_status'] for name, a in audits.items()},
    })
    write_csv(args.output / 'TRADES.csv', trades)
    write_csv(args.output / 'DECISIONS.csv', decisions)
    lines = [
        '# Diagnostic causal de chaque occasion — stratégie unique EUR/USD', '',
        'Les occasions sont les franchissements certifiés par le contexte existant. Des bougies incomplètes peuvent en masquer d’autres ; elles ne sont pas imputées à des absences de signal.', '',
        '## Réconciliation des franchissements', '',
        '| Scénario | Franchissements | Issues |', '| --- | ---: | --- |',
    ]
    for name, a in audits.items():
        outcomes = '; '.join(f'{k}: {v}' for k, v in a['bos_outcomes'].items())
        lines.append(f"| {name} | {a['bos_rows']} | {outcomes} |")
    lines += ['', '## Cycle de vie de chaque setup', '',
              'Voir les fichiers BASE_SETUPS.csv et HIGHER_COSTS_SETUPS.csv pour les dates, raisons et décisions. Les motifs simultanés ne doivent pas être additionnés comme des cas indépendants.', '']
    for name, a in audits.items():
        lines.append(f"- {name} : {a['setups_created']} setups ; {a['setup_terminal_states']}.")
    lines += ['', '## Trades exécutés', '',
              '| Scénario | Entrée UTC | Sortie | Net EUR | R encaissé |', '| --- | --- | --- | ---: | ---: |']
    for t in trades:
        lines.append(f"| {t['scenario']} | {t['entry_utc']} | {t['exit_reason']} | {t['net_eur']:.2f} | {t['R']:.3f} |")
    lines += ['', '## Prochaine action de recherche', '',
              'Qualifier les données H4/M30 et la couverture de l’ATR avant de retoucher les filtres. Examiner ensuite les setups consommés par les horaires et les fins de session à partir des événements, sans supposer que les entrées refusées auraient gagné.', '',
              'Les enveloppes M1 de liquidation sont conservées pour examiner les positions ouvertes. Elles incorporent des coûts de sortie hypothétiques et ne représentent pas automatiquement l’equity contractuelle FTMO. Aucun statut de réussite FTMO n’est attribué sans profil de compte vérifié.', '',
              'Cette exécution réutilise le développement 2021 avec les mêmes règles. Le diagnostic ajoute de la traçabilité, aucune nouvelle hypothèse de trading.']
    (args.output / 'DIAGNOSTIC.md').write_text('\n'.join(lines) + '\n')
    if identity != code_identity():
        raise RuntimeError('Source changed during replay')
    write_json(args.output / 'MANIFEST_SHA256.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.iterdir()) if p.is_file()
    })
    if any(a['audit_status'] != 'PASS' for a in audits.values()):
        raise RuntimeError('Financial outputs saved, but causal diagnostics are incomplete: inspect reconciliation files')


if __name__ == '__main__':
    main()
