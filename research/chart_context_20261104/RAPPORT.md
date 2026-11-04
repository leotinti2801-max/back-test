# Lecture du graphique, pertes et poursuite après2R — 4 novembre 2026

**Sur quatre sorties réelles au TP2R dans le nouveau test, un trade atteint
ensuite3R puis4R avant16h Londres ; aucun n'atteint5R.** Les trois autres
n'atteignent pas3R avant la fin de séance. Aucun de ces quatre parcours n'est
inconnu ; aucune atteinte3/4 n'est dans la même M1 que le TP2.

La cible2R améliore le net face à3R sur ce trimestre, sans réduire le nombre
ni le taux de pertes. Les filtres H1/ADX et niveaux testés ne remplissent pas
les critères d'amélioration. Une configuration2R est donc fournie **en option
de recherche** : `simple_forex/protocol_v04.json`. V03 reste la référence
active et ses fichiers gelés restent intacts ; aucun ordre réel n'est ajouté.

## Compte demandé :2R puis3R ou davantage

Le dénominateur est le nombre de **vrais TP2** du portefeuille2R entièrement
rejoué, pas les trades qui ont simplement touché2R sur un graphique après
leur stop. Les sorties horaires gagnantes ne sont pas des sorties au TP2.
Chaque continuation garde la même entrée, le stop initial et les coûts, sans
déplacement au break-even, jusqu'à16h Europe/London.

| Suite du mouvement, version2R sans filtre | Nombre, base | Nombre, coûts renforcés |
| --- | ---: | ---: |
| Sorties effectivement exécutées au TP2 | 4 | 4 |
| Atteint ensuite au moins3R avant stop/fin | 1 | 1 |
| Atteint ensuite au moins4R avant stop/fin | 1 | 1 |
| Atteint ensuite au moins5R avant stop/fin | 0 | 0 |
| N'atteint pas3R avant16h | 3 | 3 |
| Stop avant3R | 0 | 0 |
| Parcours inconnu ou même M1 TP2/3 | 0 | 0 |

Les nombres1 à3R et1 à4R concernent **le même trade**, pas deux trades distincts.
Ce sont quatre observations de développement, pas une probabilité future
établie à25 %. Aucun bénéfice de continuation n'est ajouté au portefeuille.

| Entrée, UTC | Sens | M1 contenant le TP2, base | Suite avant16h Londres |
| --- | --- | --- | --- |
| 25janvier09:05 | Vente | 15:00 | Pas3R |
| 27janvier09:10 | Vente | 12:45 | 3R dans M114:33 ;4R dans M114:36 ; pas5R |
| 2février09:40 | Vente | 14:48 | Pas3R |
| 11février09:10 | Achat | 13:11 | Pas3R |

Les heures sont les débuts des **minutes contenant** l'événement, pas des
heures de fill au tick vérifiées. Le moteur inscrit la clôture à la minute
suivante pour un TP. Le27janvier, cela donne clôture modèle2R12:46,
3R14:34 et4R14:37. En coûts renforcés, les minutes correspondantes sont
12:57,14:35 et14:37. Les seuils incorporent les frais prévus et demandent
un dépassement d'un tick, côté ask pour cette vente.

Dans le témoin actuel3R, le seul TP3 est ce même27janvier. Le mouvement
atteint aussi4R après cette sortie, sous les mêmes conditions de suivi.
Le résultat ne justifie pas de choisir4R après avoir observé cet unique cas.

Les autres variantes ont leur propre dénominateur : H1+ADX compte2TP2,
dont le même trade atteint3R/4R ; H1+ADX+niveaux compte0TP2. Les taux de
continuation de cette dernière sont donc `null`, jamais0 %.
Tous les détails sont dans `run_01/CONTINUATION_COUNTS.json` et les fichiers
`TP2_CONTINUATIONS.csv/json` de chaque variante et coût.

## Comparaison complète des stratégies

Période commune : **4janvier–31mars2021**, déjà consultée en développement.
Les quatre variantes ont été annoncées avant calcul, puis rejouées avec
positions, pauses, tailles, quotas, frais et change. Aucune ligne perdante
n'est retirée rétrospectivement du portefeuille.

| Variante | Trades base | Gagnants / perdants | Taux de pertes | Net base EUR | Net renforcé EUR | DD clôturé base EUR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Référence V03, cible3R | 61 | 31 / 30 | 49,2 % | +642,37 | +504,22 | 420,05 |
| Même signal, cible2R | 61 | 31 / 30 | 49,2 % | +839,28 | +719,24 | 420,05 |
| H1+ADX, cible2R | 33 | 16 / 17 | 51,5 % | +582,37 | +528,28 | 488,13 |
| H1+ADX+niveaux, cible2R | 24 | 12 / 12 | 50,0 % | −20,95 | −66,44 | 311,61 |

La cible2R apporte **+196,91 EUR en base et+215,02 EUR en renforcé** face
à3R, sur exactement les mêmes61 entrées. Le nombre de pertes reste30/61.
Le maximum quotidien reste2 entrées. Ce gain de développement n'est ni une
validation indépendante, ni une preuve de passage FTMO.

Quatre résultats changent en base, les57 autres restent identiques :

| Entrée | Net avec3R EUR | Net avec2R EUR | Différence EUR |
| --- | ---: | ---: | ---: |
| 25janvier | +176,29 | +244,74 | +68,45 |
| 27janvier | +368,95 | +245,63 | −123,32 |
| 2février | +224,66 | +247,99 | +23,33 |
| 11février | +21,02 | +249,47 | +228,45 |

Le11février est particulièrement important : attendre3R rend une grande
partie du mouvement avant la sortie horaire. Le27janvier montre le compromis
inverse : sortir2R abandonne une continuation mesurable. La somme de ces
quatre différences explique l'amélioration ; elle n'autorise pas à identifier
à l'avance lequel de ces cas se reproduira.

## Comment le contexte a été lu

Le signal simple de cassure et réarmement reste inchangé. Les filtres testés
sont séparés, avec une seule valeur annoncée pour chaque réglage :

1. **Sens H1** : dernière H1 attendue déjà clôturée, complète60/60M1 ; corps
   positif pour acheter, négatif pour vendre. Une bougie incomplète est
   inconnue, sans repli sur une vieille H1.
2. **ADX14 surM5 >=25** : force du mouvement, sans lui attribuer une direction.
   La direction vient du corpsH1. L'ADX n'utilise que la dernière M5 clôturée
   et réinitialise son calcul après un trou. Ce seuil est une hypothèse
   descriptive unique, pas un optimum trouvé sur les gains.
3. **Veto de niveau H1** : pivots stricts2H1 à gauche/2 à droite, cinq barres
   complètes, connus à la clôture de la secondeH1 de droite. Seules les
   confirmations des24 dernières heures entrent dans le test. Un niveau
   opposé intact depuis confirmation, situé avant ou au TP2, bloque l'entrée.
   Une fraîcheur inconnue à cause de minutes manquantes a son propre refus.

Le veto se fait à la première quote d'entrée : niveau bid comparé au bid
d'ouverture pour un achat, niveau ask à l'ask pour une vente. La cible vient
du véritable prix d'entrée et des coûts du scénario. Aucun high/low futur de
la M1 d'entrée n'est utilisé pour accepter le trade.

Un niveau revisité est exclu du veto, selon le plan. « Intact » signifie intact
**depuis confirmation**, pas depuis son centre historique. Une formation
incomplète peut cacher un pivot : aucun pivot connu ne prouve donc pas qu'il
n'existe aucun obstacle. Ce sont des règles de recherche à vérifier, pas des
lois de retournement du marché.

L'EMA20 H1 a été écartée pour une raison de disponibilité, avant lecture des
résultats financiers : **0/61 entrées et0/202 cassures** ont20H1 consécutives
utilisables après remise à zéro. Les dernières H1 attendues sont complètes,
mais leur historique consécutif est trop court. Aucun indicateur n'est rempli
artificiellement pour contourner ce problème. Les anciens résultats défavorables
de l'EMA20/50 M5 restent dans l'étude précédente, sans réglage opportuniste.

## Pourquoi moins de pertes ne suffit pas ici

H1+ADX retire beaucoup d'entrées :17 pertes au lieu de30, mais16 gains au
lieu de31. Le taux de pertes monte à51,5 %. Le bénéfice moyen par trade
augmente (environ17,65 EUR contre13,76), mais le net total baisse et le
drawdown clôturé augmente. Ce compromis ne remplit pas le critère annoncé
de taux de pertes plus faible **et** de net plus élevé dans les deux coûts.

Ajouter le veto de niveaux conduit à12 pertes et12 gains, avec un net négatif.
Il est surtout limité par les observations :22 motifs de fraîcheur inconnue,
contre2 motifs de niveau intact identifié, dont un se cumule avec une
incertitude sur un autre niveau. Une indisponibilité de donnée n'est pas la
preuve qu'un trade aurait été mauvais. Les deuxTP de H1+ADX disparaissent.

Les autres motifs signal sont non exclusifs : ADX sous25 sur130 cassures,
corps H1 opposé ou nul sur73, ADX indisponible sur1. Les contrôles du compte
ne sont pas évalués après un refus de contexte et ce statut est inscrit.
Les refus de position, pause, cotation tardive et ouverture revenue dans le
range restent journalisés séparément. Les audits comparent aussi les entrées
nouvelles rendues possibles par les changements de pauses/occupation.

Chaque perte exécutée est expliquée dans `LOSSES.csv`. Pour la version2R :
12 stops et18 sorties horaires négatives ; H1+ADX :5 et12 ; avec niveaux :
4 et8. Le constat est mécanique, sans cause macroéconomique inventée.

## Graphiques et utilisation du code

Les graphiques des quatreTP2 et d'une perte filtrée sont dans
[la galerie](charts/INDEX.html). Les courbes utilisent les vraies données,
le côté bid/ask approprié et l'ADX M5. Les niveaux représentés sont ceux qui
étaient connus à l'entrée ; la zone après sortie est un suivi historique,
pas une information disponible pour décider de l'entrée. Les exemples sont
choisis après résultats pour illustrer les mécanismes, pas pour régler le bot.

La nouvelle configuration optionnelle conserve le signal de32 lignes,
zéro indicateur actif et les budgets125 EUR/trade,500 EUR/jour. Elle ne change
que la cible et les métadonnées/période du rejeu. Les filtres expérimentaux
restent dans ce laboratoire et ne sont pas adoptés par V04.

```sh
PYTHONPATH=src python -m simple_forex.runner \
  --protocol simple_forex/protocol_v04.json \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/simple_v04_next_run
```

Ce serait une reproduction sur les mêmes données, pas un nouvel échantillon.
Le chargeur exige l'identité du cache et les sorties doivent être nouvelles.
Commandes de l'étude : [README.md](README.md).

## Limites conservées

Les17 tests synthétiques (6 contexte,11 continuation) passent. Les continuations
sont des hypothèses par trade qui peuvent se chevaucher ; leurs résultats ne
se somment pas en equity de portefeuille. Stop et cible atteignables dans la
mêmeM1 restent traités stop d'abord, avec ambiguïté signalée. Une minute active
absente produit un inconnu, jamais une perte ou un zéro inventé.

Ce trimestre ne complète pas l'année2021 et ne remplace pas l'historique neuf
nécessaire pour valider le candidat. Les règles contractuelles FTMO et les
spécifications MT5 restent à vérifier. Aucun taux80 %, passage des deux phases
en moins d'un mois ou rentabilité future n'est certifié.
