"""Plot frozen financial results; never simulate an execution or continuation path."""
import csv
import hashlib
import html
import json
import os
import platform
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(OUT / '.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FormatStrFormatter
import numpy as np
import pandas as pd
import talib

from backtest_bot.data import market_from_cache
from backtest_bot.reference import D, ROOT
STUDY = ROOT / 'research/chart_context_20261104'
sys.path.insert(0, str(STUDY))
from context import ChartContext

LONDON = ZoneInfo('Europe/London')
RUN = STUDY / 'run_01'
CACHE = ROOT / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl'
CONT = RUN / 'V03_2R/base/TP2_CONTINUATIONS.json'
TP_TRADES = RUN / 'V03_2R/base/TRADES.csv'
LOSS_TRADES = RUN / 'H1_ADX_LEVEL_2R/base/TRADES.csv'
COLORS = {'up': '#008575', 'down': '#c95151', 'entry': '#174ea6', 'stop': '#bd353b',
          'target': '#0e715f', 'adx': '#7151a3', 'pivot': '#ac7314'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_trades(path):
    with path.open(newline='') as stream:
        records = list(csv.DictReader(stream))
    for record in records:
        for field in ['direction', 'closed_at_ms']:
            record[field] = int(record[field])
        for field in ['entry_price', 'stop', 'target', 'net_eur', 'R', 'planned_risk_eur']:
            record[field] = float(record[field])
    return records


def millis(value):
    return int(pd.Timestamp(value).value // 1_000_000)


def local(t):
    return pd.Timestamp(t, unit='ms', tz='UTC').tz_convert(LONDON)


def xdate(t):
    return mdates.date2num(local(t).to_pydatetime())


def frnum(value, decimals=2):
    return f'{value:,.{decimals}f}'.replace(',', ' ').replace('.', ',')


def status_fr(value):
    return {'VISITED': 'déjà revisité', 'INTACT_OBSERVED': 'intact observé',
            'UNKNOWN_SINCE_CONFIRMATION': 'inconnu depuis confirmation'}[value]


def plot_case(market, context, trade, continuation, index, fee, slip):
    entry_t, d = millis(trade['entry_utc']), trade['direction']
    exit_t = trade['closed_at_ms']
    day = local(entry_t).date()
    begin = millis(pd.Timestamp(f'{day} 08:00', tz=LONDON))
    finish = millis(pd.Timestamp(f'{day} 16:00', tz=LONDON))
    side = 'bid' if d == 1 else 'ask'
    # Aggregation uses the exact executable exit-side arrays, no midpoint candles.
    side_px = {**market.px, **{'mid_' + field: market.px[side + '_' + field]
                              for field in ['open', 'high', 'low', 'close']}}
    candles = D.make_bars(replace(market, px=side_px), 5, 'M5_' + side.upper())
    slots = np.arange(candles.n)
    selected = (candles.origin_ms + slots * candles.period_ms >= begin) & (candles.origin_ms + slots * candles.period_ms < finish)
    complete_slots = slots[selected & candles.complete]
    missing_slots = slots[selected & ~candles.complete]
    assert len(complete_slots) + len(missing_slots) == 96
    snapshot = context.snapshot(entry_t, d)
    assert snapshot['H1_known_at_ms'] <= entry_t and snapshot['M5_known_at_ms'] == entry_t
    levels = sorted(snapshot['levels'], key=lambda level: (abs(level['executable_price'] - trade['entry_price']), level['id']))[:3]
    assert all(level['known_at_ms'] <= entry_t for level in levels)
    if continuation:
        targets = {2: continuation['original_2R']['target'],
                   **{int(name[0]): result['target'] for name, result in continuation['thresholds'].items()}}
        assert continuation['original_2R']['validated_actual_TP']
        assert abs(targets[2] - trade['target']) < 1e-12
        exit_price = trade['target']
        exit_price_source = 'Frozen actual TP target; timestamp is the model M1-end close, not a tick fill time'
        outcome = '3R et 4R atteints ensuite; 5R non atteint' if continuation['thresholds']['3R']['reached'] else '3R, 4R et 5R non atteints avant 16 h'
        label = 'Tous les TP2 V03_2R / base'
    else:
        assert trade['exit_reason'] == 'SL', 'Only the frozen non-gap SL illustration is supported'
        distance = d * (trade['entry_price'] - trade['stop'])
        targets = {r: trade['entry_price'] + d * (r * (distance + fee + slip) + fee) for r in [2, 3, 4, 5]}
        assert abs(targets[2] - trade['target']) < 1e-12
        exit_price = trade['stop'] - d * slip
        exit_price_source = 'Recorded SL reason, unchanged stop and existing base market-exit slippage; no execution path recomputed'
        outcome = 'Pire perte nette de H1_ADX_LEVEL_2R / base'
        label = 'Illustration de perte sélectionnée après résultats'
    fig, (price_ax, adx_ax) = plt.subplots(2, 1, figsize=(15.8, 9.7), sharex=True,
        gridspec_kw={'height_ratios': [4.1, 1.15], 'hspace': 0.09})
    fig.patch.set_facecolor('#ffffff')
    for ax in [price_ax, adx_ax]:
        ax.set_facecolor('#fcfdff')
        ax.grid(axis='y', color='#e7ebf0', linewidth=.7)
        ax.spines[['top', 'right']].set_visible(False)
        ax.spines[['bottom', 'left']].set_color('#c7d0da')
        ax.tick_params(colors='#425466', labelsize=9)
    fig.subplots_adjust(left=.075, right=.885, top=.845, bottom=.135)
    action = 'BUY' if d == 1 else 'SELL'
    title_date = local(entry_t).strftime('%d/%m/%Y')
    fig.suptitle(f'EURUSD  ·  {title_date}  ·  {action}  ·  bougies M5 {side.upper()}',
                 x=.075, y=.963, ha='left', fontsize=21, fontweight='bold', color='#182b45')
    observed_label = f'{trade["net_eur"]:+.2f} €'.replace('.', ',')
    fig.text(.075, .919, f'{label}  |  Entrée {local(entry_t):%H:%M}  ·  Sortie {local(exit_t):%H:%M}  ·  Net observé {observed_label}',
             fontsize=11, color='#425466')
    fig.text(.075, .886, outcome, fontsize=12, fontweight='bold', color='#0e715f' if continuation else '#bd353b')
    candle_width = 3.55 / (24 * 60)
    for s in complete_slots:
        t = candles.open_ms(int(s))
        x = xdate(t + candles.period_ms // 2)
        o, h, lo, c = [float(getattr(candles, name)[s]) for name in ['open', 'high', 'low', 'close']]
        color = COLORS['up'] if c >= o else COLORS['down']
        price_ax.vlines(x, lo, h, color=color, linewidth=.85, zorder=3)
        height = max(abs(c - o), .000005)
        price_ax.add_patch(Rectangle((x - candle_width / 2, min(o, c)), candle_width, height,
                                    facecolor=color, edgecolor=color, linewidth=.5, zorder=4))
    for s in missing_slots:
        price_ax.axvspan(xdate(candles.open_ms(int(s))), xdate(candles.close_ms(int(s))),
                         facecolor='#f9d8d8', alpha=.55, hatch='//', edgecolor='#dfb0b0', linewidth=0, zorder=0)
    if continuation:
        price_ax.axvspan(xdate(exit_t), xdate(finish), color='#8e99aa', alpha=.13, zorder=0)
        price_ax.text(.985, .975, 'Après TP2 : prix observés\ncontinuations hypothétiques, pas un trade ouvert',
                      transform=price_ax.transAxes, ha='right', va='top', fontsize=9, color='#56616e',
                      bbox={'facecolor': '#f0f2f5', 'edgecolor': 'none', 'alpha': .93, 'pad': 5})
    else:
        price_ax.axvspan(xdate(exit_t), xdate(finish), color='#8e99aa', alpha=.10, zorder=0)
        price_ax.text(.985, .975, 'Après SL : prix observés uniquement\naucune continuation de position calculée',
                      transform=price_ax.transAxes, ha='right', va='top', fontsize=9, color='#56616e',
                      bbox={'facecolor': '#f0f2f5', 'edgecolor': 'none', 'alpha': .93, 'pad': 5})
    for level_index, level in enumerate(levels):
        color = COLORS['pivot']
        start = max(begin, level['known_at_ms'])
        price_ax.hlines(level['executable_price'], xdate(start), xdate(finish), colors=color,
                        linestyles=':', linewidth=1.0, alpha=.8, zorder=2)
    price_ax.axhline(trade['stop'], color=COLORS['stop'], linewidth=1.2, linestyle='--', zorder=2)
    price_ax.text(1.01, trade['stop'], f'Stop initial  {trade["stop"]:.5f}',
                  transform=price_ax.get_yaxis_transform(), va='center', color=COLORS['stop'], fontsize=9, clip_on=False)
    for r, value in targets.items():
        price_ax.hlines(value, xdate(entry_t), xdate(finish), colors=COLORS['target'],
                        linestyles='-' if r == 2 else '--', linewidth=1.2 if r == 2 else .85,
                        alpha=1 if r == 2 else .65, zorder=2)
        price_ax.text(1.01, value, f'{r}R  {value:.5f}', transform=price_ax.get_yaxis_transform(),
                      va='center', color=COLORS['target'], fontsize=9, clip_on=False,
                      fontweight='bold' if r == 2 else 'normal')
    price_ax.scatter([xdate(entry_t)], [trade['entry_price']], s=75, marker='^' if d == 1 else 'v',
                     color=COLORS['entry'], edgecolor='white', linewidth=.9, zorder=7)
    price_ax.annotate(f'Entrée {action}\n{local(entry_t):%H:%M}', (xdate(entry_t), trade['entry_price']),
                      xytext=(12, 32 if d == 1 else -42), textcoords='offset points', fontsize=9,
                      color=COLORS['entry'], arrowprops={'arrowstyle': '-', 'color': COLORS['entry']},
                      bbox={'boxstyle': 'round,pad=.35', 'facecolor': 'white', 'edgecolor': '#d9e3ef', 'alpha': .95}, zorder=8)
    price_ax.scatter([xdate(exit_t)], [exit_price], s=85, marker='X', color=COLORS['target'] if continuation else COLORS['stop'],
                     edgecolor='white', linewidth=.8, zorder=7)
    price_ax.annotate(f'Sortie réelle {"TP2" if continuation else "SL"}\n{local(exit_t):%H:%M} (modèle)',
                      (xdate(exit_t), exit_price), xytext=(-100, 32 if d == -1 else -47), textcoords='offset points',
                      fontsize=9, color='#26384c', arrowprops={'arrowstyle': '-', 'color': '#64748b'},
                      bbox={'boxstyle': 'round,pad=.35', 'facecolor': 'white', 'edgecolor': '#d9e3ef', 'alpha': .95}, zorder=8)
    hits = []
    if continuation:
        for r, offset in [(3, (-106, 22)), (4, (-106, -34))]:
            result = continuation['thresholds'][f'{r}R']
            if result['reached'] is not True:
                continue
            row_start, row_end = result['event_row_open_ms'], result['event_row_end_exclusive_ms']
            # Marker denotes the recorded M1 interval, never an invented tick fill.
            t = (row_start + row_end) // 2
            price_ax.scatter([xdate(t)], [result['target']], marker='*', s=155, color='#be7900',
                             edgecolor='white', linewidth=.6, zorder=8)
            price_ax.annotate(f'{r}R : M1 {local(row_start):%H:%M}–{local(row_end):%H:%M}',
                (xdate(t), result['target']), xytext=offset, textcoords='offset points', fontsize=9,
                fontweight='bold', color='#825300', arrowprops={'arrowstyle': '-', 'color': '#ac7314'},
                bbox={'boxstyle': 'round,pad=.35', 'facecolor': '#fff8e8', 'edgecolor': '#ead6aa', 'alpha': .95}, zorder=9)
            hits.append({'threshold': f'{r}R', 'recorded_M1_start_utc': D.iso(row_start),
                         'recorded_M1_end_exclusive_utc': D.iso(row_end), 'exact_tick_time_claimed': False})
    yvals = [trade['entry_price'], trade['stop'], *targets.values(),
             *candles.low[complete_slots], *candles.high[complete_slots], *[v['executable_price'] for v in levels]]
    ymin, ymax = min(yvals), max(yvals)
    margin = (ymax - ymin) * .075
    price_ax.set_ylim(ymin - margin, ymax + margin)
    price_ax.yaxis.set_major_formatter(FormatStrFormatter('%.5f'))
    price_ax.set_ylabel(f'Prix {side.upper()} · USD par EUR', fontsize=10, color='#425466')
    price_ax.legend(handles=[Line2D([0], [0], color=COLORS['up'], lw=4, label='M5 haussière'),
                             Line2D([0], [0], color=COLORS['down'], lw=4, label='M5 baissière'),
                             Line2D([0], [0], color=COLORS['pivot'], linestyle=':', label='Pivot H1 connu à l’entrée')],
                    loc='lower left', ncol=3, fontsize=8, framealpha=.93)
    mx = [xdate(context.m5.close_ms(int(s))) for s in slots[selected]]
    adx_values = context.adx[slots[selected]]
    adx_ax.plot(mx, adx_values, color=COLORS['adx'], lw=1.5)
    adx_ax.axhline(25, color='#8794a6', lw=1, linestyle='--')
    adx_ax.text(1.01, 25, 'Seuil 25', transform=adx_ax.get_yaxis_transform(), va='center', fontsize=9, color='#66758a')
    adx_ax.set_ylabel('ADX14 M5\n(midpoint)', fontsize=10, color='#425466')
    adx_ax.set_ylim(0, max(55, float(np.nanmax(adx_values)) + 7))
    adx_ax.set_xlim(xdate(begin) - 3/(24*60), xdate(finish) + 5/(24*60))
    adx_ax.xaxis.set_major_locator(mdates.HourLocator(tz=LONDON))
    adx_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=LONDON))
    adx_ax.set_xlabel('Heure de Londres · bougies 08:00–16:00', fontsize=10, color='#425466')
    for ax in [price_ax, adx_ax]:
        ax.axvline(xdate(entry_t), color=COLORS['entry'], alpha=.25, linewidth=.8)
        ax.axvline(xdate(exit_t), color='#64748b', alpha=.35, linewidth=.8)
    levels_note = 'Aucun pivot H1 opposé connu à l’entrée dans la fenêtre de 24 h.' if not levels else 'Pivots H1 figés à l’entrée : ' + ' ; '.join(
        f'{v["executable_price"]:.5f} — {status_fr(v["freshness"])} (confirmé {local(v["known_at_ms"]):%d/%m %H:%M})' for v in levels)
    fig.text(.075, .075, levels_note, fontsize=8.1, color='#56616e', wrap=True)
    adx_at_entry = snapshot['ADX14_M5']
    h1_desc = 'inconnue' if snapshot['H1_body'] is None else 'haussière' if snapshot['H1_body'] > 0 else 'baissière' if snapshot['H1_body'] < 0 else 'plate'
    context_note = f'À l’entrée : ADX {adx_at_entry:.1f}' if adx_at_entry is not None else 'À l’entrée : ADX inconnu'
    context_note += f' · dernière H1 clôturée {local(snapshot["H1_known_at_ms"]):%H:%M} : {h1_desc}. '
    context_note += 'Entrée au prix exécuté; bougies du côté de sortie. Cibles en R net prévu de cotation, pas en R EUR réalisé.'
    fig.text(.075, .045, context_note, fontsize=8.2, color='#56616e')
    fig.text(.075, .018, 'Sélection d’illustrations après résultats. Historique 2021 déjà étudié. Les minutes M1 ne prouvent pas l’ordre exact des ticks.',
             fontsize=8.2, color='#697789')
    slug = f'{index:02d}_{day}_{action}_{"TP2" if continuation else "LOSS"}'
    files = {'png': slug + '.png', 'svg': slug + '.svg'}
    fig.savefig(OUT / files['png'], dpi=160, facecolor=fig.get_facecolor(), metadata={'Title': f'EURUSD {day} {action}'})
    fig.savefig(OUT / files['svg'], facecolor=fig.get_facecolor(), metadata={'Date': None, 'Title': f'EURUSD {day} {action}'})
    plt.close(fig)
    return {'id': slug, 'entry_utc': trade['entry_utc'], 'direction': d, 'actual_exit_utc': trade['exit_utc'],
            'actual_exit_reason': trade['exit_reason'], 'actual_net_eur': trade['net_eur'],
            'selection': 'All four actual V03_2R/base TP exits, no winner subsampling' if continuation else 'Minimum observed net_eur among H1_ADX_LEVEL_2R/base trades; post-hoc illustration only',
            'candle_side': side, 'observed_complete_M5': len(complete_slots), 'incomplete_M5_not_drawn': len(missing_slots),
            'displayed_target_prices': targets, 'actual_exit_price_displayed': exit_price,
            'actual_exit_price_source': exit_price_source, 'recorded_later_threshold_hits': hits,
            'H1_levels_displayed': levels, 'full_entry_snapshot': snapshot,
            'files': files, 'description': outcome,
            'post_exit_region_is_observational': True, 'new_execution_path_computed': False}


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none', 'svg.hashsalt': 'EURUSD-chart-context-20261104',
                         'axes.titleweight': 'bold', 'axes.labelsize': 10})
    inputs = [CONT, TP_TRADES, LOSS_TRADES, RUN / 'FREEZE_BEFORE_RESULTS.json',
              STUDY / 'context.py', ROOT / 'src/backtest_bot/data.py',
              ROOT / 'vendor/h4m30_v01/h4m30_data.py', ROOT / 'vendor/h4m30_v01/h4m30_execution.py']
    identities = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    frozen = json.loads((RUN / 'FREEZE_BEFORE_RESULTS.json').read_text())
    for rel, expected in {**frozen['source_sha256'], **frozen['shared_source_sha256']}.items():
        assert digest(ROOT / rel) == expected, rel
    continuations = json.loads(CONT.read_text())
    assert len(continuations) == 4
    source_trades = read_trades(TP_TRADES)
    tp_trades = [t for t in source_trades if t['exit_reason'] == 'TP']
    assert len(tp_trades) == 4
    keyed = {(t['entry_utc'], t['direction']): t for t in tp_trades}
    assert set(keyed) == {(r['entry_utc'], r['direction']) for r in continuations}
    loss = min(read_trades(LOSS_TRADES), key=lambda t: t['net_eur'])
    market, quality = market_from_cache(CACHE)
    context = ChartContext(market)
    protocol = frozen['baseline_protocol']
    cases = [plot_case(market, context, keyed[(r['entry_utc'], r['direction'])], r, i+1,
              protocol['fee_round_trip_quote'], protocol['slip_quote_per_market_execution'])
             for i, r in enumerate(continuations)]
    cases.append(plot_case(market, context, loss, None, 5,
              protocol['fee_round_trip_quote'], protocol['slip_quote_per_market_execution']))
    cards = []
    for case in cases:
        title = f'{local(millis(case["entry_utc"])):%d/%m/%Y %H:%M} · {"BUY" if case["direction"] == 1 else "SELL"}'
        cards.append(f'''<article id="{case['id']}"><h2>{html.escape(title)}</h2><p class="caption">{html.escape(case['description'])} · Net réellement clôturé : {frnum(case['actual_net_eur'])} €.</p><figure><a href="{case['files']['svg']}"><img loading="lazy" src="{case['files']['png']}" alt="Chandeliers EURUSD M5, entrée, stop, cibles et ADX du {html.escape(title)}"></a></figure><p class="downloads"><a href="{case['files']['png']}">PNG</a><a href="{case['files']['svg']}">SVG vectoriel</a></p></article>''')
    page = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURUSD — cinq lectures de graphique</title><style>body{margin:0;background:#eef2f6;color:#182b45;font:16px/1.6 system-ui,sans-serif}main{max-width:1420px;margin:0 auto;padding:36px 20px 60px}h1{font-size:clamp(27px,4vw,42px);line-height:1.15;margin:0 0 16px}header{max-width:1050px;padding:10px 0 26px}.lead{font-size:20px}.note{background:#fff8e8;border-left:4px solid #ad7415;padding:15px 20px}article{background:white;margin:28px 0;padding:22px;border:1px solid #dce3ec;border-radius:10px;box-shadow:0 3px 12px #14263b08}h2{margin:0;font-size:23px}.caption{margin:5px 0 14px;color:#425466}figure{margin:0}img{display:block;width:100%;height:auto}.downloads{display:flex;gap:20px;margin-bottom:0}a{color:#174ea6;text-underline-offset:3px}.methods{background:#fff;border-radius:10px;padding:22px}li{margin:8px 0}.badge{display:inline-block;background:#e6f1ed;color:#0e715f;padding:4px 12px;border-radius:30px;font-size:13px;font-weight:700}footer{font-size:14px;color:#64748b;padding-top:25px}</style><main><header><p class="badge">EURUSD · données 2021 · lecture descriptive</p><h1>Quatre sorties à 2R, et une perte après filtre</h1><p class="lead">Parmi les quatre TP2 de V03_2R au coût standard, le short du 27 janvier atteint ensuite 3R puis 4R avant 16 h. Les trois autres n’atteignent pas 3R; aucun des quatre n’atteint 5R.</p><div class="note">Tous les quatre TP2 sont montrés. La cinquième image est la pire perte nette de H1_ADX_LEVEL_2R au coût standard. Ce choix d’illustrations est fait après résultats; il ne sélectionne ni stratégie ni filtre. Les continuations hypothétiques ne sont pas des gains réellement encaissés ni un portefeuille additionnable.</div></header>'''
    page += '\n'.join(cards)
    page += '''<section class="methods"><h2>Conventions de lecture</h2><ul><li>Chandeliers réels M5 de 08 h à 16 h, heure de Londres : BID pour un achat, ASK pour une vente, soit le côté utilisé pour sortir. L’entrée reste le prix exécuté, avec spread et slippage du modèle.</li><li>ADX14 calculé sur les M5 midpoint clôturées, avec remise à zéro après toute M5 incomplète; seuil 25 dessiné. L’ADX indique une intensité, pas une direction.</li><li>Au maximum trois pivots opposés H1, confirmés et connus avant l’entrée, sont dessinés. Leur statut depuis confirmation est évalué et figé à l’entrée. Aucun pivot confirmé plus tard n’est ajouté.</li><li>La zone grisée commence après la clôture réelle du modèle. Les étoiles 3R/4R viennent exclusivement des résultats de continuation déjà produits; elles représentent des intervalles M1, pas des instants de fill au tick.</li><li>Les cibles sont celles du R net prévu en devise de cotation; ce R n’est pas exactement le R monétaire réalisé en euros. Les niveaux supérieurs sur l’exemple perdant sont seulement des repères géométriques, sans nouvelle simulation.</li><li>Aucune EMA20 H1 inventée : sa faisabilité était nulle aux entrées avec la politique de données retenue. Ces images n’établissent aucune rentabilité future ni réussite FTMO.</li></ul><p><a href="PROVENANCE.json">Provenance et cas sélectionnés</a> · <a href="MANIFEST_SHA256.json">Empreintes des fichiers</a></p></section><footer>Galerie autonome, sans service distant ni script externe. Ouvrir INDEX.html avec les PNG et SVG dans le même dossier. Les figures sont exportées pour lecture et partage.</footer></main></html>'''
    (OUT / 'INDEX.html').write_text(page)
    provenance = {'purpose': 'Scientific/financial plotting of existing results only',
        'selection_post_hoc': True, 'strategy_selection_from_images': False,
        'all_four_actual_TP2_cases_included': True, 'loss_selection': 'Worst net H1_ADX_LEVEL_2R/base trade',
        'read_existing_continuations_only': True, 'execution_or_continuation_paths_recomputed': False,
        'EMA20_H1_displayed': False, 'source_sha256': identities, 'cache_sha256': digest(CACHE),
        'cache_quality': quality, 'runtime': {'python': platform.python_version(), 'matplotlib': matplotlib.__version__,
            'numpy': np.__version__, 'pandas': pd.__version__, 'talib_wrapper': talib.__version__, 'talib_C': talib.__ta_version__.decode()},
        'cases': cases, 'visual_inspection': 'Pending inspection of at least one rendered image'}
    (OUT / 'PROVENANCE.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    for rel, expected in identities.items():
        assert digest(ROOT / rel) == expected, rel
    (OUT / 'MANIFEST_SHA256.json').write_text(json.dumps({p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST_SHA256.json'},indent=2)+'\n')
    print(json.dumps({'charts': len(cases), 'index': str(OUT/'INDEX.html'),
                      'worst_loss': loss['entry_utc'], 'net_eur': loss['net_eur']},indent=2))


if __name__ == '__main__':
    main()
