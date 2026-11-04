# Laboratoire séparé du bot

Les scripts ajoutent des annotations et comparent une seule hypothèse au témoin.
Ils ne changent aucun fichier du bot actif. L'environnement isolé de cette
session est `/workspace/research_envs/indicator_lab` ; le programme n'intègre
aucun courtier. Dépendances : `requirements.txt` dans ce dossier.

Depuis la racine du dépôt, utiliser un Python isolé avec ces versions.
Les dossiers de sortie doivent être nouveaux ; les exemples ci-dessous ne
doivent pas écraser `run_01`, `comparison_01` ou `diagnostic_01`.

```sh
PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python -m unittest discover \
  -s research/indicator_study_20261104/lab -p 'test_*.py' -v

PYTHONPATH=src /workspace/research_envs/indicator_lab/bin/python \
  research/indicator_study_20261104/lab/run_annotations.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output research/indicator_study_20261104/lab/run_02

PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/indicator_study_20261104/lab/run_comparison.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output research/indicator_study_20261104/lab/comparison_02
```

`run_annotations.py` utilise les journaux V03 de `reports/simple_rearmed_v03_01`
et le cache reconnu par SHA256/taille/schéma, sans nouvelle simulation.
`run_comparison.py` rejoue complètement le témoin et le filtre EMA, sur le
trimestre et avec les deux coûts du plan gelé.
`diagnose_comparison.py` analyse seulement `comparison_01` et crée
`diagnostic_01`, sans nouveau calcul de marché ; son entrée/sortie sont fixes.

- `run_01/` :204 décisions annotées (61 closes,1 inconnue,142 refus),
  couverture, version effective et manifeste.
- `comparison_01/` : plan/code gelés, quatre simulations, trades, décisions,
  enveloppes de liquidation et manifeste. Résultat EMA défavorable conservé.
- `diagnostic_01/` : chaque perte observée, changements d'entrées,
  décisions privées d'EMA et provenance.

Le plan initial d'annotations disait « pas de nouveau backtest » pour cette
première étape, qui est restée descriptive. L'essai suivant possède son propre
plan `SINGLE_COMPARISON_PLAN.json` et son gel avant résultats ; il n'altère
ni le plan initial ni ses fichiers de sortie.
Les nouveaux fichiers ajoutés ensuite ne sont pas rétroactivement inclus dans
les gels précédents. Le manifeste de l'étude recense l'ensemble livré.

Le cache complet, l'environnement Python et les copies des sources tierces
ne sont pas redistribués dans la petite archive de cette étude. Elle contient
les scripts propres, résultats et URLs/empreintes. Le code réutilisé du dépôt
reste nécessaire pour reproduire les calculs ; aucune dépendance n'est cachée.
