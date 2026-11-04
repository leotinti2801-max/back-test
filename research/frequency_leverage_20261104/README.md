# Plus d'entrées et levier : code et preuves

Ce laboratoire étudie la demande de davantage de trades/jour ou de levier.
Il reste sur EURUSD et la cassure du même range Londres08–09h, avec réarmement
par clôture intérieure. Aucun indicateur, aucun accès courtier. MT5 reste la
plateforme confirmée ; les spécifications contractuelles restent à vérifier.

Le [plan](PLAN_BEFORE_RESULTS.json) précède les résultats :9 variantes,
4 périodes,2 hypothèses de coûts, soit72 simulations finies. Ces périodes de2021
sont déjà utilisées en développement. Les diagnostics28j sont imbriqués dans
le trimestre et ne forment pas des échantillons indépendants.

- [Rapport et décision](RAPPORT.md).
- `signals.py` : signal simple paramétrable M5/M1, horaire de fin et sortie.
- `engine.py` : copie fonctionnelle du moteur gelé, avec le seul changement
  de durée maximale injecté dans son espace de paramètres privé.
- `run_study.py` : lanceur du lot annoncé, journaux complets et audit des tailles.
- `test_study.py` :6 tests ciblés, tous réussis avant les simulations.
- `run_01/COMPARISON.csv` et `RESULTS.json` : résultats de tous les scénarios.
- Sous chaque variante/période/coût : trades, décisions, pertes expliquées,
  tailles budget/levier et enveloppes M1 de liquidation.
- `leverage_audit/` : effet du levier sur les anciennes tailles, sans simulation.
- `design_audit/` et `cost_path_audit/` : revues indépendantes et causes des
  changements de parcours entre coûts.

Depuis la racine du dépôt :

```sh
PYTHONPATH=src:. python research/frequency_leverage_20261104/test_study.py -v

PYTHONPATH=src:. python research/frequency_leverage_20261104/run_study.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output research/frequency_leverage_20261104/run_02
```

Python3.12.14, NumPy2.3.5, pandas2.2.3 ; dépendances identiques à celles du dépôt.
Le cache reconnu par SHA256/taille/schéma reste nécessaire. Une autre source
doit d'abord être qualifiée, jamais renommée pour contourner cette vérification.
`run_02` doit être un nouveau dossier ; les sorties antérieures ne sont pas
écrasées. Un rejeu identique est une vérification de reproduction.

Le moteur gelé n'est ni réécrit ni modifié globalement : le clone conserve son
code, ses valeurs par défaut et ses fonctions comptables. Son dictionnaire
privé remplace seulement la fabrique de paramètres pour rendre60min effectif.
Le lanceur impose toujours une source de signaux explicite, sans repli V01.
Le code V03 actif demeure inchangé ; les variantes restent en recherche.

La petite archive de livraison contient code et résultats, sans le cache ni
l'environnement Python. Les règles FTMO, la marge et les fills MT5 réels ne
sont pas certifiés par ces simulations. Le résultat annuel reste inconnu au
trou d'avril ; le test trimestriel ne l'efface pas.
