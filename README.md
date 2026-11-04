# Forex EUR/USD — stratégie simple de cassure du range de Londres

Le [journal de recherche](JOURNAL_RECHERCHE.md) suit chaque étape publiée sur
GitHub : code, résultats, graphiques et limites. Le cache de prix et les ZIP
restent hors du dépôt ; les URLs/empreintes des sources restent consultables.

La recherche actuelle utilise une méthode sans indicateur, avec **réarmement des
cassures, objectif prévu à 3R et plafond de quatre entrées réelles par jour**.
Le [signal V03](simple_forex/strategy_rearmed.py) tient en 32 lignes. Le risque
prévu est de 125 € par trade, au maximum 500 € par jour. Le taux de 80 % demandé
n'est pas atteint : 54,8 % sur les 31 trades des 45 jours observés.

Voir le [mode d'emploi V03](simple_forex/README_V03.md) et le
[rapport complet, échecs inclus](reports/RAPPORT_FREQUENCE_ET_R_V03.md).
Le protocole courant est `simple_forex/protocol_v03.json`. Les versions V01, V02
et les éléments H4/M30 sont conservés comme archives reproductibles.

La [nouvelle étude d'indicateurs et de supports/résistances](research/indicator_study_20261104/SYNTHESE.md)
annote les entrées sans information future et teste un unique filtre EMA20/50.
Sur le trimestre de développement commun, le filtre dégrade le net et le taux
de réussite ; il est écarté. MT5 est confirmé, sans intégration courtier.

L'[étude suivante sur la fréquence et le levier](research/frequency_leverage_20261104/RAPPORT.md)
teste9 variantes annoncées, avec deux coûts et trois diagnostics28j. Les sorties
60min et une séance élargie atteignent108 trades trimestriels, jusqu'à4/jour,
mais le gain net supplémentaire ne résiste pas aux coûts renforcés. Les plafonds
de levier30/100 ne changent aucune taille à risque identique. V03 reste le témoin.

La [lecture graphique et le suivi après2R](research/chart_context_20261104/RAPPORT.md)
rejouent une cible2R et deux filtres de contexte. Parmi4TP2, un seul atteint
ensuite3R et4R avant16h, aucun5R. Les filtres ne réduisent pas le taux de pertes.
Le [candidat2R optionnel](simple_forex/protocol_v04.json) donne+839,28 EUR contre
+642,37 EUR à3R sur le trimestre, avec les mêmes30 pertes/61trades. Il reste
en recherche ; V03 et ses gels sont conservés.

Le [cycle de recherche du 4 novembre](research/knowledge_cycle_20261104/SYNTHESE.md)
documente les limites des preuves, l'archive brute d'avril manquante et les
22 trades suivants qui perdent 917,02 € après les 45 jours initialement positifs.
La file de recherche permet de reprendre sur des données ou accès nouveaux,
sans modifier les paramètres ni relancer les mêmes calculs sans raison.

```sh
PYTHONPATH=src python -m simple_forex.runner \
  --protocol simple_forex/protocol_v03.json \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/simple_rearmed_next_run
```

## Archive H4/M30 V02

Version expérimentale issue du dossier H4/M30 fourni le 3 novembre 2026.
Elle débloque des entrées mais **aucune variante n'est qualifiée pour le réel**.
Il n'existe aucune garantie de trades uniquement gagnants. Aucun accès courtier,
envoi d'ordre, déploiement ou activation automatique n'est implémenté.

## Ancien axe H4/M30 : une seule stratégie archivée

La recherche précédente portait sur **A_STRUCTURE_FIXED_2R** : EUR/USD,
structure H4, cassure M30, entrée sur repli, cible prévue à 2R. Les variantes B–E
restent archivées pour la traçabilité. Ce choix n'est pas une qualification de A,
qui ne compte que trois trades et dont les deux gains viennent de sorties horaires.

Lire le [dossier d'analyse Forex](research/forex_single_strategy/DOSSIER_ANALYSTE_FOREX.md)
et la [charte de recherche](research/forex_single_strategy/STRATEGY_CHARTER.json).
Le registre distingue les documentations consultées des publications financières
primaires encore inaccessibles. Aucun nouveau seuil ni filtre macro n'est activé.

Pour reproduire cet ancien axe uniquement, avec paramètres historiques
inchangés et deux scénarios de coûts :

```sh
PYTHONPATH=src python scripts/run_focused_backtest.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/focused_next_run
```

Cette commande reste un rejeu archivé du développement 2021. Les commandes historiques
ci-dessous rejouent les cinq anciens candidats pour reproduire leurs archives ;
elles ne constituent plus le workflow de recherche actif.

Chaque nouveau lancement dédié produit aussi un **diagnostic causal automatique** :
franchissements acceptés/refusés/non évalués, cycle de vie de chaque setup,
motifs d'entrée et de sortie, couverture des bougies et enveloppes de liquidation
M1. Lire `DIAGNOSTIC.md` et les CSV préfixés `BASE_`/`HIGHER_COSTS_` dans la sortie.
L'observateur est validé sur les empreintes des sources gelées ; il n'exécute pas
des trades refusés et conserve les mêmes résultats financiers. Ses enveloppes
M1 ne certifient pas l'equity contractuelle d'une prop firm.

L'objectif de qualification FTMO en moins d'un mois est documenté dans
[l'analyse des contraintes](research/ftmo_readiness/OBJECTIF_ET_BLOCAGES.md).
L'utilisateur a confirmé FTMO 2-Step, 100 000 € en euros, moins d'un mois pour les
deux phases réunies, sur le Forex uniquement. Les règles contractuelles exactes
restent à vérifier. Le brief historique reçu et ses écarts avec la variante 2R
sont documentés dans `research/brief_reconciliation_20261103/`. Aucun succès FTMO
n'est revendiqué à partir du seul PnL annuel.

## Résultats et état

Lire [le rapport](reports/RAPPORT_V02.md) et [l'état du bot](reports/BOT_STATUS.json).
Le moteur de référence est reproduit : 12 setups et zéro trade en 2021.
Cinq variantes ont été définies avant leurs nouveaux résultats. La plus active
prend 20 trades, mais perd de l'argent après frais. La seule variante annuelle
positive n'a que trois trades et n'est pas sélectionnée.

## Installation et contrôles

Python 3.12, numpy 2.3.5 et pandas 2.2.3 ont été utilisés.

```sh
cd /workspace/back-test
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

Dans l'environnement cloud courant, ces dépendances sont déjà disponibles.
Les tests utilisent des données synthétiques, sans connexion réseau.

## Rejouer la recherche

Le cache original identifié est conservé dans `data/` dans l'environnement et
dans l'archive de livraison. Il est exclu de Git. Le chargeur contrôle son SHA256,
limite les objets désérialisables et vérifie son schéma ; il refuse les autres
pickle. Les minutes absentes et la quarantaine d'horloge restent absentes.

```sh
PYTHONPATH=src python -m backtest_bot.research \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/replay_v02

PYTHONPATH=src python scripts/verify_annual.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --freeze reports/replay_v02/FREEZE_BEFORE_RESULTS.json \
  --output reports/replay_annual_v02
```

Les dossiers de sortie doivent être nouveaux : les expériences précédentes ne
sont pas écrasées. `FREEZE_BEFORE_RESULTS.json` conserve les paramètres et les
empreintes du code avant le calcul. Les résultats, décisions, trades et
manifestes restent consultables, y compris lorsqu'ils sont défavorables.

Les résultats de la version finale sont dans `reports/run_v02_02` et
`reports/annual_v02_02`. Les premiers calculs restent conservés ; aucun seuil n'a
été réajusté entre les deux exécutions. Un audit indépendant des flux monétaires
des 110 lignes de trades annuels est également fourni :

```sh
PYTHONPATH=src python scripts/audit_results.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --results reports/annual_v02_02 \
  --output reports/audit_replay.json
```

## Règles nouvelles et contrôles communs

- Cible fixe en R déterminée à l'ouverture d'entrée, coûts prévus inclus, ou cible
  structurelle déjà connue et non revisitée à la cassure. Aucun pivot futur.
- Variante de contexte H4 : sens du corps de la dernière H4 complète attendue,
  corps/range ≥25 %, sans maintien d'une vieille H4 à travers une lacune.
- Corps M30 ≥1 ATR ou ≥0,5 ATR selon la variante ; cassure et POI de référence
  conservées. Les noms de certains motifs dans le module hérité mentionnent
  encore « 1 ATR » ; le seuil effectif est celui du paramètre gelé.
- Risque prévu maximal de 250 € par position, capital initial 100 000 €, une entrée
  par jour UTC, pause de 24 h après deux pertes, levier maximal 10.
- Entrées 08–16 h UTC, interdiction 15 h 30–17 h Europe/Paris, sortie au plus tard
  à 16 h UTC ou après 120 minutes. Les horaires sont des choix de recherche,
  explicitement différents du témoin original.
- Spread bid/ask réel du cache, commission et glissement ; priorité au stop en
  cas d'ambiguïté M1. Aucun deuxième essai sur un premier retour refusé.
- Arrêt de la branche continue si une entrée cachée ou une exposition inconnue
  est possible. Le résultat total devient alors inconnu, jamais zéro.

Le calcul ne certifie pas que le flux historique contient toutes les cotations.
Les diagnostics par journée indépendante ne représentent pas un portefeuille
annuel et ne servent pas à choisir la variante. La sélection utilise uniquement
le premier semestre ; les autres périodes restent des vérifications sur une
année déjà consultée, pas une validation indépendante.

## Origine et limites

`vendor/h4m30_v01` contient cinq fichiers fournis, conservés à l'octet avec leurs
empreintes dans `ORIGIN_SHA256.json`. Les nouveaux modules sont dans
`src/backtest_bot`. Les pièces jointes originales restent intactes hors du dépôt.
La stratégie, les horaires et les cibles V02 sont de nouvelles hypothèses,
pas des corrections dont la rentabilité aurait été démontrée.

La suite utile est un historique bid/ask qualifié et encore inutilisé, puis des
tests sur des périodes et régimes supplémentaires. Ne pas multiplier les essais
sur 2021 jusqu'à fabriquer une courbe positive. L'environnement cloud est déjà
isolé : réutiliser ce checkout ; ne pas créer de worktree sans demande explicite.
