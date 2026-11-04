"""ONE invocation only after the user's exact GO. Never called by preparation."""
import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from backtest_bot.data import market_from_cache
from backtest_bot.reference import ROOT
from backtest_bot.research import epoch_ms, write_csv
from simple_forex.strategy_rearmed import signals
from common import HERE, START, CONTROL_END, END, SCENARIOS, assert_scope, configs, digest, write_json
from engine import simulate
from statistics_frozen import inference
import json


def block(trades, start, end, complete):
    subset = [t for t in trades if start <= t['entry_utc'] < end]
    known = sum(t['net_eur'] for t in subset)
    return {'start': start, 'end_exclusive': end, 'complete': complete,
        'closed_trades': len(subset), 'known_closed_net_eur': known,
        'net_eur': known if complete else None,
        'mean_R_per_closed_trade': sum(t['R'] for t in subset) / len(subset) if subset else None,
        'trades': subset}


def authorize(go):
    path = HERE / 'FREEZE_BEFORE_RESULTS.json'
    expected = 'GO RUN MISSING_MINUTE_V01 ' + digest(path)
    if go != expected:
        raise ValueError('Exact GO and freeze SHA256 required')
    frozen = json.loads(path.read_text())
    for relative, sha in frozen['frozen_files_sha256'].items():
        if digest(ROOT / relative) != sha:
            raise RuntimeError('Frozen file differs: ' + relative)
    assert_scope()
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go', required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    authorize(args.go)
    out = HERE / 'run_01'
    out.mkdir()  # Atomic one-shot lock, before any financial computation or cache read.
    write_json(out / 'EXECUTION_RECORD.json', {'go': args.go,
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False})
    try:
        mk, quality = market_from_cache(args.cache)
        ref = json.loads((ROOT / 'config/reference_params.json').read_text())
        all_results = {}
        for name, cfg in configs().items():
            all_results[name] = {}
            for scenario in SCENARIOS:
                for cost, stress in [('base', False), ('higher_costs', True)]:
                    folder = out / name / scenario / cost
                    folder.mkdir(parents=True)
                    summary, trades, decisions, envelopes, gaps = simulate(mk, cfg, ref,
                        epoch_ms(START), epoch_ms(END), stress, signal_source=signals, scenario=scenario)
                    halt = summary['halt']
                    control_complete = halt is None or halt['at_utc'] >= CONTROL_END
                    control = block(trades, START, CONTROL_END, control_complete)
                    evaluation = block(trades, CONTROL_END, END, halt is None)
                    all_results[name][scenario + '/' + cost] = {'halt': halt,
                        'control': control, 'evaluation': evaluation, 'full_summary': summary}
                    for label, rows in [('TRADES', trades), ('DECISIONS', decisions),
                        ('LIQUIDATION_ENVELOPES', envelopes), ('GAPS_ENCOUNTERED', gaps),
                        ('CONTROL_TRADES', control['trades']), ('EVALUATION_TRADES', evaluation['trades'])]:
                        write_csv(folder / (label + '.csv'), rows)
                    write_json(folder / 'RESULTS.json', all_results[name][scenario + '/' + cost])
        write_json(out / 'RESULTS.json', {'strategies': all_results, 'cache_quality': quality,
            'independent_validation': False, 'scenario_bounds_guaranteed': False,
            'FTMO_probability': None, 'reference': 'V03'})
        write_json(out / 'INFERENCE_AND_VERDICTS.json', inference(all_results))
        write_json(out / 'MANIFEST_SHA256.json', {str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob('*')) if p.is_file()})
    except Exception as exc:
        write_json(out / 'TECHNICAL_FAILURE_STOP.json', {'error': type(exc).__name__,
            'message': str(exc), 'traceback': traceback.format_exc(), 'automatic_retry': False})
        raise  # Do not erase run_01; no automatic relaunch.


if __name__ == '__main__':
    main()
