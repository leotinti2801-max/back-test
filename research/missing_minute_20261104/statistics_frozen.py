"""Frozen user-specified resampling/verdict; no market reads or simulator imports."""
import hashlib
import numpy as np
import pandas as pd

SEED, B, BLOCK = 20261104, 5000, 5
EVAL_START, END = '2021-04-01T00:00:00Z', '2022-01-01T00:00:00Z'


def sessions():
    return pd.date_range(EVAL_START, END, freq='B', inclusive='left')


def draw_sessions(n, *, seed=SEED, draws=B):
    if n < BLOCK:
        raise ValueError('Need at least five sessions')
    starts = np.random.Generator(np.random.PCG64(seed)).integers(0, n - BLOCK + 1,
        size=(draws, n // BLOCK + 1))
    return (starts[:, :, None] + np.arange(BLOCK)).reshape(draws, -1)[:, :n]


def draw_identity():
    draws = draw_sessions(len(sessions()))
    return {'sessions': len(sessions()), 'shape': list(draws.shape), 'generator': 'numpy.PCG64',
        'sha256_little_endian_int64': hashlib.sha256(draws.astype('<i8').tobytes()).hexdigest()}


def bootstrap_metrics(day_sum_r, day_n, indices):
    sums = np.asarray(day_sum_r, dtype=float)[indices].sum(axis=1)
    counts = np.asarray(day_n, dtype=int)[indices].sum(axis=1)
    return np.divide(sums, counts, out=np.zeros_like(sums), where=counts != 0)


def holm_two(p_values):
    if set(p_values) != {'V03', 'V04'}:
        raise ValueError('Exactly V03 and V04 required')
    order = sorted(p_values, key=lambda name: (p_values[name], name))
    first = min(1.0, 2 * p_values[order[0]])
    return {order[0]: first, order[1]: max(first, p_values[order[1]])}


def inference(strategies):
    """Strategies map to six run records with halt/evaluation/trades; call only after GO."""
    complete = {name: all(run['halt'] is None for run in runs.values()) for name, runs in strategies.items()}
    raw, diagnostic, means = {}, {}, {}
    if all(complete.values()):
        calendar = sessions()
        indices = draw_sessions(len(calendar))  # SAME draws for both strategies.
        for name in ['V03', 'V04']:
            trades = strategies[name]['S_CONT/higher_costs']['evaluation']['trades']
            totals, counts = np.zeros(len(calendar)), np.zeros(len(calendar), dtype=int)
            lookup = {stamp.strftime('%Y-%m-%d'): k for k, stamp in enumerate(calendar)}
            for trade in trades:
                k = lookup[trade['entry_utc'][:10]]
                totals[k] += trade['R']
                counts[k] += 1
            values = bootstrap_metrics(totals, counts, indices)
            raw[name] = (1 + int(np.count_nonzero(values <= 0))) / (B + 1)
            diagnostic[name] = {'p_raw_user_rule': raw[name],
                'lower_percentile_unilateral95_unadjusted_descriptive': float(np.quantile(values, .05, method='linear')),
                'zero_trade_resamples': int(np.count_nonzero(counts[indices].sum(axis=1) == 0)),
                'bootstrap_draws': B}
            means[name] = float(totals.sum() / counts.sum()) if counts.sum() else None
        adjusted = holm_two(raw)
        for name in adjusted:
            diagnostic[name]['p_adjusted_Holm'] = adjusted[name]
    else:
        adjusted = None
        diagnostic = {name: {'p_adjusted_Holm': None, 'reason': 'R2 prevents complete joint inference'} for name in strategies}
    verdicts = {}
    for name, runs in strategies.items():
        cont = runs['S_CONT/higher_costs']['evaluation']
        pess = runs['S_PESS/higher_costs']['evaluation']
        if not complete[name]:
            verdict = 'NON CONCLUANT'
        elif cont['net_eur'] <= 0:
            verdict = 'ARRÊT'
        elif cont['closed_trades'] < 100:
            verdict = 'NON CONCLUANT'
        elif (means.get(name) is not None and means[name] >= .05
              and adjusted is not None and adjusted[name] < .05 and pess['net_eur'] > 0):
            verdict = 'CANDIDAT À COLLECTE PROSPECTIVE'
        else:
            verdict = 'TESTÉ NON VALIDÉ'
        verdicts[name] = verdict
    return {'diagnostics': diagnostic, 'verdicts': verdicts,
        'joint_inference_complete': all(complete.values()), 'reference_remains': 'V03',
        'p_value_caveat': 'User-defined sign-count bootstrap rule; not an independently established calibration or FTMO probability'}
