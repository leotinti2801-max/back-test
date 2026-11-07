# STRATEGIE_L3_V01 — Données uniquement

Période des prix : du 2020-01-01 00:00 UTC au 2026-10-16 23:59 UTC inclus.
Aucune modification de la fiche gelée ; aucun backtest, rendement, calcul de spread ou statistique liée aux fenêtres de stratégie.

## Prix
`eurusd_m1/` : CSV des seuls mois contenant des ticks effectivement reçus ; les 82 mois demandés ne sont pas tous acquis. Statut INCOMPLET. Refus HTTP 429 du fournisseur avec demande de passer par son export S3 en volume. Aucun accès AWS configuré dans cet environnement. Un CSV vide n'est pas livré comme un historique valide. Les mois non acquis figurent dans `provenance/AVAILABILITY_82_MONTHS.csv`. Schéma, schéma exact de la demande :
`utc_minute,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close,n_ticks`.
Les deux côtés sont agrégés à partir des mêmes ticks journaliers Dukascopy, en UTC. Les jours bruts sont identifiés dans le registre de provenance avec URL et SHA256. La méthode et la version du collecteur sont dans `provenance/PRICE_SOURCE_AND_METHOD.json`.
Aucun prix n'est affiché dans les comptes rendus, aucun spread n'est calculé. Ces cotations Dukascopy ne sont pas présentées comme des cotations FTMO.

`minutes_manquantes/` : un CSV par mois dont l'acquisition a été tentée et auditée énumérant chaque minute UTC sans barre, week-ends et jours fériés compris. `no_source_ticks` indique que les fichiers reçus ne contiennent aucun tick pour la minute ; cela ne certifie pas une fermeture du marché. `source_unavailable_or_invalid` signale une acquisition défaillante et ne signifie jamais zéro tick sur le marché. Pas de forward-fill ni d'interpolation. La synthèse de couverture est strictement mensuelle, sans étude des fenêtres de la stratégie.

## Décisions BCE et FOMC
`calendriers/DECISIONS_BCE_FOMC_2020_2026.csv` : dates de publication des décisions opérationnelles de politique monétaire, y compris décisions extraordinaires de mars 2020 ; pas seulement les variations de taux. Une ligne par banque/date, lien officiel propre à chaque décision. Les dates des comptes rendus et les dates d'entrée en vigueur des taux ne sont pas utilisées.
`DECISIONS_NATURE.csv` distingue réunions et annonces extraordinaires.
Le calendrier FOMC 2020 signale une réunion le 2 mars, mais la décision a été publiée le 3 mars : la date retenue est le 3 mars.
Les votes complémentaires identifiés dans les calendriers FOMC (liquidité et cadre de politique) sont séparés dans `VOTES_COMPLEMENTAIRES_CALENDRIER_FOMC.csv` ; ils ne sont pas assimilés silencieusement à des réunions de taux. Ce fichier n'est pas un inventaire de toutes les annonces de liquidité de la Fed.
Les deux réunions de décembre 2026 encore futures au 7 novembre 2026 sont dans `DECISIONS_PLANIFIEES_FIN_2026.csv`, pas dans les décisions publiées.

## Jours fériés
`calendriers/JOURS_FERIES_US_UK_2020_2026.csv` : colonnes `date,pays,nom`.
US : jours fériés fédéraux OPM, aux dates observées pour un horaire lundi-vendredi. Le jour de l'An 2022 observé le 31 décembre 2021 est rattaché à sa vraie date calendaire. Juneteenth est inclus à partir de 2021. Les Inauguration Days, limités à la région de Washington, figurent dans un CSV distinct. Le périmètre n'inclut pas les fermetures administratives exceptionnelles par décret.
UK : bank holidays GOV.UK des trois régions, désignées dans le nom par `[england-and-wales]`, `[scotland]`, `[northern-ireland]`. Le CSV enrichi de provenance conserve la région et les notes de substitution. Pour Londres, le périmètre applicable est `england-and-wales` ; ne pas assimiler les jours propres à l'Écosse ou à l'Irlande du Nord à des jours fériés londoniens.
Ces listes civiles/bancaires ne constituent pas un calendrier des fermetures de toutes les bourses, du marché Forex ou des horaires FTMO.

## Intégrité et statut
Lire `STATUT_LIVRAISON.json` avant utilisation ; le statut distingue des minutes sans ticks des jours non acquis. `provenance/DATA_VALIDATION.json` ne contient que des contrôles de données.
Les empreintes de tous les fichiers livrés sont dans `MANIFEST_SHA256.json`, sauf celle du manifeste lui-même. L'identité et la vérification du lot gelé reçu sont dans `provenance/FROZEN_LOT_IDENTITY.json`.
Aucun module de stratégie n'a été importé ou exécuté par la collecte. La fiche, ses horaires et ses résultats ne servent pas à sélectionner les données.

## Reprise à débit limité — 7 novembre 2026

Le registre des sources a servi de point de reprise. Une seule requête à la fois, intervalle de 3 à 5 secondes ; après un HTTP 429, aucune nouvelle requête avant une pause de 10 minutes. Les requêtes et leur chronologie figurent dans `provenance/ACQUISITION_REQUEST_LOG.csv`, le checkpoint dans `provenance/ACQUISITION_RESUME_STATE.json`. Deux 429 consécutifs après la pause déclenchent la proposition d’une autre source, sans téléchargement avant accord. Les journées initialement en échec restent dans la file tant qu’elles ne sont pas acquises. Aucun indicateur ni résultat de stratégie n’est produit.
