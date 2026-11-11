# XAUUSD M1 bid et ask, et fiches FTMO EURUSD / XAUUSD

Demande directe de Léo du 11 novembre 2026, lot `STRATEGIE_TENDANCE_FX_OR_V01`.
Branche dédiée : `data/tendance-fx-or-v01-20261111`.

**Le contrôle croisé Dukascopy obligatoire est bloqué.** Les fichiers ne constituent
pas une livraison entièrement validée : la correction horaire a été appliquée selon
la demande, mais n'a pas pu être confirmée indépendamment sur l'or.
Voir [le compte rendu du contrôle](CONTROLE_DUKASCOPY.md) et
`provenance/CONTROLE_DUKASCOPY.json`.

## Contenu

- `xauusd_m1/` : un CSV par mois UTC, janvier 2020 à octobre 2026, avec arrêt au **16 octobre 2026 à 23:59 UTC inclus**.
- `minutes_manquantes/` : chaque minute sans barre dans la grille UTC complète, un CSV par mois. Les week-ends, jours fériés, pauses de cotation et absences inexpliquées ne sont pas supprimés de cette liste.
- [Fiche FTMO XAUUSD et EURUSD, lue le 11 novembre 2026](FTMO_XAUUSD_EURUSD_2026-11-11.md) : tailles de contrat, points et valeurs, commissions, swaps affichés, leviers et horaires.
- `provenance/` : demande originale, identités SHA-256, journal des sources et contrôles techniques. Le statut d'acquisition et celui du contrôle Dukascopy sont distincts.
- `MANIFEST_SHA256.json` : empreinte de chaque fichier livré dans ce dossier, sauf le manifeste lui-même.

Le format suit `datasets/strategie_l3_v01_histdata`, sur la branche historique
`data/strategie-l3-v01-20261107`. EURUSD étant déjà disponible, aucun nouveau jeu de
prix EURUSD n'est créé et les données historiques existantes restent intactes.

```text
utc_minute,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close,n_ticks
```

Les heures sont exprimées en UTC, au début de l'intervalle `[minute, minute + 60 s)`.
Bid et ask sont agrégés séparément depuis les deux cotations effectivement présentes
dans chaque tick HistData. `n_ticks` compte les enregistrements source. Les valeurs
monétaires sont conservées en décimal exact. Ni ask, ni minute absente ne sont inventés.

## Conversion demandée

1. Interpréter l'étiquette du fichier comme une horloge naïve et lui ajouter 5 heures : `u0`.
2. Si `u0` tombe pendant l'heure d'été de `Europe/Berlin`, retrancher une heure : `u = u0 − 1 h`. Sinon, `u = u0`.
3. Filtrer sur `[2020-01-01T00:00:00Z, 2026-10-17T00:00:00Z)` puis agréger et répartir par mois UTC.

La documentation HistData annonce un EST fixe sans changement d'heure. La
correction supplémentaire est une **consigne empirique explicite du lot**. Elle
ne doit pas être confondue avec une règle officielle HistData ou une correction
déjà validée sur XAUUSD. Les intervalles européens utilisés sont consignés dans
`provenance/EUROPE_BERLIN_DST_INTERVALS.json`.

## Reproduction de la préparation uniquement

Depuis la racine du dépôt, avec Python 3.12, une base zoneinfo et un compilateur C++17 :

```bash
python tools/data_tendance_fx_or_v01/test_prepare.py
python tools/data_tendance_fx_or_v01/collect.py --cache /chemin/cache_xauusd
python tools/data_tendance_fx_or_v01/validate.py
```

Le cache est extérieur aux fichiers livrés. Les ZIP sources s'obtiennent depuis les
formulaires officiels HistData, leurs URLs et empreintes étant conservées. La reprise
réutilise les mois préparés, sans relancer de stratégie.

Les contrôles ci-dessus portent sur le format, le temps, la présence des minutes,
les OHLC et les identités des fichiers. Aucun moteur de stratégie n'est importé,
aucun backtest, rendement, résultat de challenge ou indicateur n'est calculé.

Les prix HistData ne sont pas des cotations FTMO et les swaps FTMO relevés sont une
photographie actuelle, pas une série historique 2020–2026.
