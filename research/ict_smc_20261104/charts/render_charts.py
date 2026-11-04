"""Render existing ICT decisions only; never replay a trading/execution path."""
import csv
import hashlib
import html
import importlib.util
import json
import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/ict_chart_matplotlib')
os.environ['XDG_CACHE_HOME'] = '/tmp/ict_chart_cache'
Path('/tmp/ict_chart_cache').mkdir(parents=True, exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

from backtest_bot.data import market_from_cache, CACHE_SHA256
from backtest_bot.reference import D, ROOT


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
RUN = STUDY / 'run_01'
spec = importlib.util.spec_from_file_location('ict_chart_strategy', STUDY / 'strategy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def stamp(ms):
    return pd.Timestamp(int(ms), unit='ms', tz='UTC').tz_convert('Europe/London')


def xdate(ms):
    return mdates.date2num(stamp(ms).to_pydatetime())


def artifact_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(mk, ict, execution_bars, event, trade, name, description):
    setup = json.loads(event['setup'])
    d, day = setup['direction'], event['day']
    side = 'BID' if d == 1 else 'ASK'
    entered = event['reason'] == 'ENTERED'
    decision = int(event['decision_ms'])
    start = int(pd.Timestamp(f'{day} 08:00', tz='Europe/London').value // 1_000_000)
    end = int(pd.Timestamp(f'{day} 16:00', tz='Europe/London').value // 1_000_000)
    first = (start - ict.bars.origin_ms) // ict.bars.period_ms
    last = (end - ict.bars.origin_ms) // ict.bars.period_ms
    slots = np.arange(first, last, dtype=int)
    mids = [ict.bars.open_ms(s) + ict.bars.period_ms // 2 for s in slots]
    xs = np.array([xdate(t) for t in mids])
    bars = execution_bars['bid' if d == 1 else 'ask']
    color_up, color_down = '#008879', '#cf5151'
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True,
        gridspec_kw={'height_ratios': [3.8, 1, 1.1]})
    ax, atr_ax, oscillator_ax = axes
    fig.subplots_adjust(left=.07, right=.85, top=.85, bottom=.23, hspace=.16)
    for axis in axes:
        axis.set_facecolor('#fbfcff')
        axis.grid(color='#e5eaf1', linewidth=.7)
        axis.set_axisbelow(True)
    width = 3.5 / 1440
    for s, x in zip(slots, xs, strict=True):
        if not bars.complete[s]:
            ax.axvspan(x - 2.5 / 1440, x + 2.5 / 1440, color='#ffdddd', alpha=.5)
            continue
        o, c, lo, hi = (getattr(bars, field)[s] for field in ['open', 'close', 'low', 'high'])
        color = color_up if c >= o else color_down
        ax.vlines(x, lo, hi, color=color, linewidth=.7, zorder=3)
        ax.add_patch(Rectangle((x - width / 2, min(o, c)), width, max(abs(c - o), .000002),
            facecolor=color, edgecolor=color, linewidth=.5, zorder=4))
    values = ict.values
    ax.plot(xs, values['ema20'][slots], color='#3762a5', linewidth=1, label='EMA20 milieu · descriptif')
    ax.plot(xs, values['ema50'][slots], color='#b56b22', linewidth=1, label='EMA50 milieu · descriptif')
    ax.plot(xs, values['bb_upper'][slots], color='#8c9bb0', linewidth=.7, linestyle='--')
    ax.plot(xs, values['bb_lower'][slots], color='#8c9bb0', linewidth=.7, linestyle='--')
    ax.fill_between(xs, values['bb_lower'][slots], values['bb_upper'][slots],
        color='#c7d3e5', alpha=.18, label='Bollinger20 ±2σ milieu · descriptif')
    nine = int(pd.Timestamp(f'{day} 09:00', tz='Europe/London').value // 1_000_000)
    for level, label in [(setup['range_high'], 'Haut range milieu'), (setup['range_low'], 'Bas range milieu')]:
        ax.hlines(level, xdate(nine), xdate(end), color='#76818d', linestyle=':', linewidth=1)
    ax.axvspan(xdate(start), xdate(nine), color='#e7eff8', alpha=.4)
    ax.text(xdate(start) + .003, .98, 'Formation du range 08–09 h', transform=ax.get_xaxis_transform(),
        va='top', color='#63758c', fontsize=9)
    mss_known = setup['mss_known_at_ms']
    ax.hlines(setup['mss_level'], max(xdate(start), xdate(setup['mss_pivot_known_at_ms'])),
        xdate(mss_known), color='#a06c19', linestyle='--', linewidth=1.3, label='Pivot MSS déjà confirmé · milieu')
    fvg_end = max(decision, mss_known + D.MIN_MS)
    ax.add_patch(Rectangle((xdate(mss_known), setup['fvg_low']), xdate(fvg_end) - xdate(mss_known),
        setup['fvg_high'] - setup['fvg_low'], facecolor='#9bd9c9', edgecolor='#16816a',
        alpha=.42, zorder=2, label='FVG connu après MSS'))
    ob = setup.get('order_block')
    if ob:
        ax.add_patch(Rectangle((xdate(ob['known_at_ms']), ob['low']), xdate(fvg_end) - xdate(ob['known_at_ms']),
            ob['high'] - ob['low'], facecolor='#edca9b', edgecolor='#be842c',
            alpha=.24, zorder=1, label='Order block annoté · connu au MSS'))
    stop, target = setup['stop'], setup['structural_target']
    for price, label, color in [(stop, 'Stop initial' if entered else 'Stop prévu', '#c23b43'),
                               (target, 'Cible structurelle', '#047e6b')]:
        ax.hlines(price, xdate(decision), xdate(end), color=color, linestyle='--', linewidth=1.2)
        ax.text(1.01, price, f'{label}\n{price:.5f}', transform=ax.get_yaxis_transform(),
            va='center', color=color, fontsize=9)
    sweep = setup['sweep_known_at_ms']
    sweep_slot = setup['sweep_slot']
    sweep_y = bars.low[sweep_slot] if d == 1 else bars.high[sweep_slot]
    ax.annotate(f'Balayage confirmé\n{stamp(sweep):%H:%M}', (xdate(sweep), sweep_y),
        xytext=(-75, -42 if d == 1 else 32), textcoords='offset points',
        arrowprops={'arrowstyle': '->', 'color': '#62566d'},
        bbox={'boxstyle': 'round,pad=.25', 'facecolor': 'white', 'edgecolor': '#d7d0e0', 'alpha': .95}, fontsize=9)
    mss_y = float(ict.bars.close[setup['mss_slot']])
    ax.annotate(f'MSS + FVG connus\n{stamp(mss_known):%H:%M}', (xdate(mss_known), mss_y),
        xytext=(25, -60), textcoords='offset points',
        arrowprops={'arrowstyle': '->', 'color': '#0b8572'},
        bbox={'boxstyle': 'round,pad=.25', 'facecolor': 'white', 'edgecolor': '#beddd5', 'alpha': .95}, fontsize=9)
    if event.get('entry_price'):
        decision_y = float(event['entry_price'])
    else:
        decision_y = float(ict.bars.close[ict.bars.slot_of_close(decision)])
    decision_label = ('Entrée SELL' if d == -1 else 'Entrée BUY') if entered else (
        'Retour FVG · REFUSÉ' if event['reason'] == 'REFUSED' else 'Retour expiré · AUCUNE ENTRÉE')
    ax.scatter([xdate(decision)], [decision_y], marker='v' if d == -1 and entered else '^' if entered else 'D',
        s=65, color='#24578b' if entered else '#7a588a', edgecolor='white', zorder=8)
    ax.annotate(f'{decision_label}\n{stamp(decision):%H:%M}', (xdate(decision), decision_y),
        xytext=(40, 35 if d == -1 else -42), textcoords='offset points',
        arrowprops={'arrowstyle': '->', 'color': '#24578b'},
        bbox={'boxstyle': 'round,pad=.25', 'facecolor': 'white', 'edgecolor': '#cedceb', 'alpha': .95}, fontsize=9)
    later = decision
    if trade:
        closed = int(trade['closed_at_ms'])
        later = closed
        ax.scatter([xdate(closed)], [float(trade['target'])], marker='X', s=70, color='#007e6c', edgecolor='white', zorder=8)
        row_start = closed - D.MIN_MS
        ax.annotate(f'TP réel · M1 {stamp(row_start):%H:%M}–{stamp(closed):%H:%M}\nclôture modèle',
            (xdate(closed), float(trade['target'])), xytext=(20, 28), textcoords='offset points',
            arrowprops={'arrowstyle': '->', 'color': '#047e6b'}, fontsize=9,
            bbox={'boxstyle': 'round,pad=.25', 'facecolor': 'white', 'edgecolor': '#beddd5', 'alpha': .95})
    for axis in axes:
        axis.axvline(xdate(decision), color='#b2c7e0', linewidth=.8)
        axis.axvspan(xdate(later), xdate(end), color='#e8ebf1', alpha=.42)
    ax.text(.99, .98, 'Après la clôture : prix observés' if entered else 'Après décision : aucun trade exécuté',
        transform=ax.transAxes, ha='right', va='top', fontsize=9, color='#5e6979')
    atr_ax.plot(xs, values['atr14'][slots] * 10000, color='#b77e26', linewidth=1.2)
    atr_ax.scatter([xdate(mss_known)], [setup['atr_previous'] * 10000], marker='o', s=35, color='#8a5d13', zorder=5)
    atr_ax.annotate(f'ATR précédent utilisé : {setup["atr_previous"] * 10000:.2f}pips',
        (xdate(mss_known), setup['atr_previous'] * 10000), xytext=(20, 15), textcoords='offset points', fontsize=9)
    atr_ax.set_ylabel('ATR14 M5\n(pips)')
    oscillator_ax.plot(xs, values['adx14'][slots], color='#7952af', linewidth=1.2, label='ADX14 descriptif')
    oscillator_ax.plot(xs, values['rsi14'][slots], color='#3b8199', linewidth=1, label='RSI14 descriptif')
    oscillator_ax.set_ylim(0, 100)
    oscillator_ax.set_ylabel('ADX / RSI\n0–100')
    oscillator_ax.legend(loc='upper left', ncol=2, fontsize=8)
    oscillator_ax.xaxis.set_major_locator(mdates.HourLocator(tz=stamp(start).tzinfo))
    oscillator_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=stamp(start).tzinfo))
    oscillator_ax.set_xlim(xdate(start), xdate(end))
    oscillator_ax.set_xlabel('Heure de Londres · bougies08:00–16:00')
    ax.set_ylabel(f'Prix {side} · USD par EUR\nEMA/Bollinger sur milieu')
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower left', bbox_to_anchor=(.07, .858),
        ncol=3, fontsize=8, framealpha=.96)
    for axis in axes:
        for label in axis.texts:
            label.set_zorder(12)
    fig.text(.07, .95, f'EURUSD · {pd.Timestamp(day):%d/%m/%Y} · {"BUY" if d == 1 else "SELL"} · {description}',
        fontsize=19, fontweight='bold', color='#18314f')
    detail = (f'Entrée réelle {stamp(decision):%H:%M} · net observé {float(trade["net_eur"]):+.2f}EUR · '
              f'R prévu {float(trade["planned_net_quote_R"]):.2f}' if entered else
              f'Décision {stamp(decision):%H:%M} · ' + (
                  f'refus : cible prévue {float(event["planned_net_quote_R"]):.2f}R <2R' if event['reason'] == 'REFUSED'
                  else 'expiration du délai de retour FVG, aucune position'))
    fig.text(.07, .918, detail, fontsize=11, color='#526579')
    fig.text(.07, .15, 'ATR précédent : seule condition de force testée. EMA20/50, Bollinger, ADX et RSI sont descriptifs, sans probabilité de gain.',
        fontsize=9.3, color='#526579')
    fig.text(.07, .12, 'Range et MSS sur milieu ; stop/cible sur côté exécutable. FVG et order block ne sont dessinés qu’à partir de leur confirmation.',
        fontsize=9.3, color='#526579')
    fig.text(.07, .09, 'Sélection des illustrations après résultats ; aucune sélection de stratégie par les images. Historique2021 déjà utilisé en développement.',
        fontsize=9.3, color='#6d7d91')
    fig.text(.07, .06, 'Bougies M5 et événements M1 du modèle : aucun ordre exact des ticks n’est déduit. Aucune simulation de trade ou de continuation relancée.',
        fontsize=9.3, color='#6d7d91')
    for ext in ['png', 'svg']:
        fig.savefig(HERE / f'{name}.{ext}', dpi=140, facecolor='white')
    plt.close(fig)
    return {'name': name, 'day': day, 'reason': event['reason'], 'direction': d,
        'decision_ms': decision, 'setup': setup, 'description': description,
        'actual_trade': entered, 'actual_net_eur': float(trade['net_eur']) if trade else None}


def main():
    mk, quality = market_from_cache(ROOT / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl')
    ict = module.ICT(mk)
    execution_bars = {}
    for side in ['bid', 'ask']:
        px = {**mk.px, **{f'mid_{field}': mk.px[f'{side}_{field}'] for field in ['open', 'close', 'high', 'low']}}
        execution_bars[side] = D.make_bars(replace(mk, px=px), 5, 'M5_' + side)
    q1 = read(RUN / 'Q1/base/DECISIONS.csv')
    year = read(RUN / 'Y2021/base/DECISIONS.csv')
    trades = read(RUN / 'Q1/base/TRADES.csv')
    selected = [
        (next(r for r in q1 if r['reason'] == 'ENTERED'), trades[0], '01_2021-01-06_SELL_ENTERED', 'Trade réellement exécuté'),
        (next(r for r in q1 if r['reason'] == 'REFUSED'), None, '02_2021-01-12_BUY_REFUSED', 'Proposition refusée'),
        (next(r for r in year if r['reason'] == 'SETUP_EXPIRED_RETURN'), None, '03_2021-02-08_BUY_EXPIRED', 'Setup expiré sans entrée')]
    cases = [render(mk, ict, execution_bars, *case) for case in selected]
    sources = [Path(__file__), STUDY / 'strategy.py', STUDY / 'PLAN_BEFORE_RESULTS.json',
        RUN / 'RESULTS.json', RUN / 'Q1/base/DECISIONS.csv', RUN / 'Q1/base/TRADES.csv', RUN / 'Y2021/base/DECISIONS.csv',
        ROOT / 'research/indicator_study_20261104/lab/features.py']
    provenance = {'purpose': 'Render three existing ICT decisions; no execution or strategy replay',
        'selection_post_hoc': 'Unique entered trade; first refused Q1; first annual return expiry',
        'strategy_selection_from_images': False, 'execution_paths_recomputed': False,
        'indicators_recomputed_for_display_with_same_ICT_class': True,
        'only_previous_ATR_is_strength_gate': True, 'other_indicators_not_probabilities': True,
        'source_sha256': {str(p.relative_to(ROOT)): artifact_hash(p) for p in sources},
        'cache_sha256': CACHE_SHA256, 'cache_quality': quality,
        'runtime': {'matplotlib': matplotlib.__version__, 'numpy': np.__version__, 'pandas': pd.__version__},
        'cases': cases, 'visual_inspection': 'Pending assistant image inspection; not an execution validation'}
    (HERE / 'PROVENANCE.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    cards = ''.join(f'<article><h2>{html.escape(c["description"])} · {c["day"]}</h2><a href="{c["name"]}.svg"><img src="{c["name"]}.png" alt="{html.escape(c["description"])}"></a><p><a href="{c["name"]}.png">PNG</a> · <a href="{c["name"]}.svg">SVG</a></p></article>' for c in cases)
    (HERE / 'INDEX.html').write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><title>ICT/SMC — trois décisions auditées</title><style>body{font:16px system-ui;margin:2rem auto;max-width:1400px;color:#18314f}img{width:100%;height:auto}article{margin:3rem 0}p{line-height:1.5}</style><h1>ICT/SMC EURUSD — trade, refus, expiration</h1><p>Illustrations après résultats, données2021 de développement. Un seul trade ne démontre aucune probabilité de gain. Seul l’ATR précédent filtre la force du MSS ; les autres indicateurs sont descriptifs. Aucun trade supplémentaire n’est simulé.</p>' + cards + '</html>\n')
    (HERE / 'MANIFEST_SHA256.json').write_text(json.dumps({p.name: artifact_hash(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'MANIFEST_SHA256.json'}, indent=2) + '\n')
    print(json.dumps({'charts': len(cases), 'new_trade_simulations': False, 'output': str(HERE)}, indent=2))


if __name__ == '__main__':
    main()
