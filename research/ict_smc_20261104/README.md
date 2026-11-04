# ICT/SMC : balayage, MSS et retour FVG

Hypothèse unique annoncée dans [PLAN_BEFORE_RESULTS.json](PLAN_BEFORE_RESULTS.json).
Le code formalise des termes ICT/SMC dont les définitions ne sont pas universelles.
Il ne détecte pas les ordres institutionnels réels. Aucun réglage ne sera changé
après lecture des résultats de ce lot.

Avant calcul :9 tests de stratégie/exécution et8 tests de probabilité passent.
La revue indépendante a fait ajouter le rejet explicite d'un doji au MSS même
si ATR vaut zéro. Les données2021 sont déjà du développement ; aucune calibration
indépendante ne permet d'augmenter les mises. Risque125EUR, plafond prévu500/jour.

```sh
PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/ict_smc_20261104/test_ict.py -v
PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/ict_smc_20261104/run_study.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output research/ict_smc_20261104/run_01
```

Python3.12.14, NumPy2.3.5, pandas2.2.3, TA-Lib Python0.6.8/C0.6.4.
Le cache est vérifié par taille/SHA/schéma avant lecture restreinte. Utiliser
un nouveau dossier pour toute reproduction. Le signal et l'ordre sont isolés
dans ce laboratoire ; les anciennes sources et résultats restent intacts.

Les indicateurs graphiques descriptifs ne sont pas des preuves indépendantes
de probabilité. Seul l'ATR antérieur conditionne le déplacement. FVG/OB et
références H1 seront tracés avec leur disponibilité réelle ; jamais décalés
vers une date où leur confirmation n'était pas encore connue.
