# V03 — réarmement, plafond de quatre entrées et cible prévue à 3R

Le signal reste simple : **32 lignes, aucun indicateur**. Les coûts, le risque et
les journaux sont séparés ; le programme complet ne se limite pas à ces lignes.

## Règles

Figer le range EUR/USD de 08 à 09 h Londres. Après une clôture M5 à l'intérieur
du range, la prochaine clôture strictement extérieure peut produire une entrée.
Une nouvelle clôture intérieure est obligatoire pour réarmer le signal. Une
mèche seule ou plusieurs clôtures restant dehors ne produisent pas d'essais répétés.

Les entrées sont recherchées de 09 à 14:30 Londres, fin exclue. La quote M1
d'entrée doit toujours être au-delà du range. Stop de l'autre côté du range,
cible prévue à 3R frais prévus inclus, clôture forcée à 16 h Londres.

- Maximum **quatre entrées réellement exécutées** par jour ; les refus ne
  consomment pas cette limite.
- Une seule position ouverte. Un nouveau signal pendant une position est refusé.
- Risque prévu maximal **125 € par trade, 500 € cumulés par jour**.
- Pause de 24 h après deux pertes consécutives, depuis la sortie effective.
- Données manquantes pendant une exposition : arrêt et résultat total inconnu.

Le risque effectif peut dépasser le prévu avec un gap ou un effet de change.
Les limites propres au modèle ne certifient pas les clauses FTMO.

## Résultat et limite de la demande

Sur les 45 jours 2021 : 31 trades, **54,8 % de gains nets**, +765,35 € après frais.
Avec coûts augmentés : +692,72 €. Sur le préfixe annuel connu : 61 trades,
50,8 % de gains nets, +642,37 €. L'année reste inconnue à cause de la M1 absente
du 1er avril à 11:40 UTC. Le taux de 80 % n'est ni atteint ni validé.

Le plafond est passé à quatre ; le maximum réellement exécuté dans ces données
reste deux par jour. Les positions déjà ouvertes et la pause après pertes
empêchent une partie des entrées. L'objectif de 3R est un niveau prévu, pas le
gain moyen réalisé : les sorties horaires dominent et les gagnants D45 valent
en moyenne environ 0,90R.

Ce candidat exploratoire suit des essais défavorables conservés dans le rapport.
Les choix et comparaisons portent sur 2021 déjà vu, sans validation indépendante.
Il n'est pas qualifié pour FTMO ou pour le réel.

## Lancer

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m simple_forex.runner \
  --protocol simple_forex/protocol_v03.json \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/simple_rearmed_next_run
```

Utiliser un dossier neuf. Les anciennes comparaisons sont dans
`reports/simple_london_retest_v02_01` et `reports/simple_london_frequency_target_01`.
Le dernier rejeu dédié V03 est `reports/simple_rearmed_v03_01` ; ses CSV de trades
sont identiques à ceux du même candidat dans la comparaison gelée. Les sources
V01 avant adaptation du moteur sont archivées dans `research/source_snapshots/`.
