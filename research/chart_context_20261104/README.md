# Contexte graphique et suivi après2R

Lire d'abord [RAPPORT.md](RAPPORT.md). Le plan gelé définit quatre variantes et
deux coûts sur le trimestre de développement2021 déjà consulté. Il n'ajoute
aucune intégration MT5 ni ordre réel. La référence V03 reste inchangée.

Depuis la racine du dépôt, avec l'environnement isolé contenant TA-Lib0.6.8,
NumPy2.3.5, pandas2.2.3, Python3.12.14 :

```sh
PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/chart_context_20261104/test_context.py -v

PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/chart_context_20261104/continuation/test_continuation.py -v

PYTHONPATH=src:. /workspace/research_envs/indicator_lab/bin/python \
  research/chart_context_20261104/run_study.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output research/chart_context_20261104/run_02
```

Utiliser un nouveau dossier ; `run_01` n'est pas écrasé. Le cache est vérifié
par SHA256/taille/schéma avant désérialisation restreinte. Les tests synthétiques
ne demandent pas l'historique réel. Une exécution identique vérifie la
reproduction, sans ajouter une validation indépendante.

- `context.py` : H1 clôturée, ADX M5, statut des niveaux H1, veto d'entrée.
- `continuation/` : validation des vraisTP2 puis suivi3/4/5, tests et gel propre.
- `run_01/` : huit portefeuilles complets, pertes/refus, enveloppes M1, continuations
  séparées, décomptes et manifestes.
- `target_comparison/` : les61 mêmes entrées2R/3R, quatre cash-flows modifiés,
  contrôle des paramètres de la configuration optionnelle V04.
- `feasibility/` : disponibilité H1 contrôlée avant tout résultat financier.
- `filter_audit/`, `results_audit/`, `methodology/` : revues indépendantes et limites.
- `charts/` : galerie PNG/SVG et provenance, à partir des résultats enregistrés.

La branche TA-Lib C effectivement exécutée est0.6.4 ; compatibilité0 et période
instable ADX0 sont enregistrées dans le gel. Les formules et leurs limites
documentaires restent dans l'étude `../indicator_study_20261104/sources/`.
Le code actif de32 lignes et le moteur partagé ne sont pas modifiés : le
laboratoire injecte seulement un contrôle d'ordre dans un espace privé du
simulateur, et fournit une source de signaux explicite.

La configuration optionnelle `simple_forex/protocol_v04.json` exprime le
candidat2R déjà testé, sans filtre ajouté. Ses métadonnées indiquent qu'il
n'est ni référence active ni validé pour le réel. Son contrôle des paramètres
est conservé après résultats, sans être présenté comme un gel antérieur.

Les scripts d'audit/graphique ajoutés après le calcul ne modifient pas le gel
des sources qui ont produit les résultats. Le manifeste global recense tous
les fichiers livrés. L'archive contient le code et les preuves ; le cache et
l'environnement Python ne sont pas redistribués dans cette petite livraison.
