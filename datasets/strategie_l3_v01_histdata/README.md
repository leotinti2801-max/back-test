# STRATEGIE_L3_V01 — HistData EUR/USD M1 bid et ask

Jeu distinct autorisé par Léo le 7 novembre 2026, après le maintien des HTTP 429 Dukascopy. Les données Dukascopy déjà livrées, les calendriers et la fiche gelée restent intacts. Aucun remplacement silencieux entre fournisseurs.

## Fichiers

- `eurusd_m1/` : 82 CSV, du 2020-01-01 00:00 UTC au 2026-10-16 23:59 UTC inclus.
- Schéma exact : `utc_minute,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close,n_ticks`.
- `minutes_manquantes/` : chaque minute UTC sans barre, un CSV par mois. Les week-ends et jours fériés restent dans cette grille.
- `provenance/monthly_source_ledger.csv` : URLs, identités et SHA256 des ZIP et CSV sources, nombre de ticks et contrôles de format par archive.
- `provenance/monthly_coverage.csv` : contrôle de couverture strictement mensuel, sans calcul lié aux fenêtres de stratégie.
- `MANIFEST_SHA256.json` : tous les fichiers livrés, sauf le manifeste lui-même.
- `STATUT_LIVRAISON.json` : acquisition complète ou incomplète explicitement indiquée ; une absence de tick n'est pas une preuve de fermeture du marché.

## Conversion

HistData publie ces ticks en EST fixe UTC−05:00, sans heure d'été. Le passage en UTC ajoute exactement 5 heures toute l'année. Les archives locales de décembre 2019 à octobre 2026 sont nécessaires aux bornes et à la période demandée. Les données hors période sont écartées avant agrégation.
Les quatre OHLC sont calculés séparément sur bid et ask reçus. `n_ticks` compte les enregistrements source, pas la colonne volume. Les horodatages égaux conservent tous les ticks et leur ordre source. Les ouvertures/fermetures suivent le premier/dernier horodatage de la minute ; les éventuels retours arrière de la source sont consignés. Aucune interpolation, aucun ask fabriqué, aucune soustraction de bid et ask.

## Calendriers et gel

Les calendriers officiels sont conservés dans [le dossier déjà livré](../strategie_l3_v01/calendriers/). Leurs empreintes et l'identité du gel sont référencées dans `provenance/EXISTING_DATASET_REFERENCES.json`.
Les prix HistData ne sont pas présentés comme des cotations FTMO.

Aucun rendement, spread, indicateur horaire ou statistique liée aux fenêtres de la fiche n'est calculé. Aucun backtest. Aucun fichier de stratégie n'est importé ni exécuté.

Les [83 archives originales](provenance/ARCHIVES_ORIGINALES.md) sont conservées dans 8 conteneurs annuels, avec leurs liens de récupération et empreintes.
