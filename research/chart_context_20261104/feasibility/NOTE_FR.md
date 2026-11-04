# Faisabilité du contexte H1 avant tout filtre

**EMA20 H1 n'est disponible à aucune des 61 entrées V03 ni aux 202 cassures du
trimestre**, avec les données et la politique de trous actuelles. ATR14 H1 est
disponible à 0/61 entrées et 3/202 cassures. Leurs H1 sources sont pourtant
toutes complètes : c'est l'historique consécutif nécessaire à l'initialisation
qui manque.

| Cohorte, 4 janvier–31 mars 2021 inclus | Événements | Dernière H1 complète | EMA20 H1 | ATR14 H1 | Les deux |
| --- | ---: | ---: | ---: | ---: | ---: |
| Entrées des positions clôturées V03 | 61 | 61 | 0 | 0 | 0 |
| Cassures brutes avant contrôles de compte | 202 | 202 | 0 | 3 | 0 |

Les 61 entrées sont incluses dans les 202 cassures. Ces cohortes ne sont pas à
additionner. La position inconnue d'avril est hors de cette fenêtre commune.
Aucune nouvelle simulation, aucun PnL joint aux indicateurs et aucune période
recherchée pour obtenir un meilleur résultat.

## Construction et remise à zéro

Le cache est chargé par `market_from_cache`, qui vérifie taille, SHA256, schéma
et règles de qualité existantes. `D.make_bars(market, 60, 'H1')` conserve une H1
seulement si ses **60 M1** sont présentes. Ses OHLC midpoint sont recoupés avec
une agrégation indépendante des minutes; les bougies incomplètes restent NaN.

Comme dans le précédent laboratoire `features.indicators`, toute bougie
incomplète sépare deux segments et réinitialise la graine TA-Lib. La règle
était appliquée aux M5; elle l'est ici aux H1 : **une seule M1 absente rend sa
H1 incomplète et relance le warm-up H1**. Aucun remplissage, transport de valeur
ancienne ou saut d'heures supposées fermées n'est introduit. Aucun calendrier
sourcé de fermetures n'est fourni; on ne classe pas les trous comme fermetures
normales du marché.

Le runtime effectivement exécuté est TA-Lib Python 0.6.8 / C 0.6.4,
compatibilité 0, périodes instables EMA et ATR à 0. EMA20 commence à l'indice 19
du segment, soit après 20 H1 complètes consécutives; ATR14 à l'indice 14, soit
après 15 H1 complètes. Aux 61 entrées, il n'y en a que 2 à 14; aux cassures,
1 à 15. Cela explique les valeurs indisponibles sans modifier les fenêtres.

Exemple : le 4 janvier à 09:20 UTC, la source est la H1 08:00–09:00. Le segment
complet commence le 3 janvier à 23:00 UTC et contient 10 H1. Sans nouvelle
coupure, ATR14 ne pourrait apparaître qu'à 14:00 et EMA20 à 19:00 ce jour-là.
Les colonnes `first_possible_*` du CSV sont cette borne théorique sous
continuation sans trou, pas la promesse d'une valeur effectivement future.

## Source H1 clôturée et exclusion de la bougie en formation

Le mapping `Bars.slot_of_close(t)` donne
`floor((t−origine)/1 heure)−1`. Avec une origine UTC alignée, la H1 retenue clôture
à `floor(t/1 heure)×1 heure`, donc au plus tard à la décision. La bougie qui
s'ouvre à cette borne est la H1 en formation, appelée ici `bar0`, et reste
exclue.

| Décision UTC | H1 retenue | H1 en formation exclue |
| --- | --- | --- |
| 09:59 | 08:00–09:00 | 09:00–10:00 |
| 10:00 | 09:00–10:00 | 10:00–11:00 |
| 10:05 | 09:00–10:00 | 10:00–11:00 |

Aux frontières exactes, la bougie venant de clôturer est utilisable, pas celle
qui vient de s'ouvrir. Les 263 lignes de cohortes passent le recoupement
arithmétique indépendant, avec un âge de source entre 0 et 55 minutes. Ce
mapping décrit notre grille UTC; il ne vérifie pas les horodatages ni les
conventions de calcul du serveur MT5 réel.

## Conséquence pour un préenregistrement

Un filtre exigeant EMA20 H1 sous cette politique disposerait de **zéro contexte
connu** sur les cassures étudiées. Rejeter les valeurs inconnues éliminerait
donc tous ces candidats. Cela ne mesure pas l'avantage d'EMA20 et ne démontre
pas qu'un graphique H1 MT5 serait dépourvu d'EMA; le résultat concerne cette
grille de données avec remise à zéro stricte.

Raccourcir la période ou conserver silencieusement la graine au-delà des trous
changerait l'expérience. Aucun de ces changements n'est effectué. Une autre
politique demanderait une qualification des fermetures et des données, puis une
définition préalable distincte. La comparaison EMA20/50 M5 déjà défavorable
reste archivée et le bot V03 reste inchangé.

Les [résultats JSON](RESULTS.json), les
[disponibilités par événement](H1_AVAILABILITY_BY_EVENT.csv) et le
[gel avant disponibilité](SPEC_BEFORE_AVAILABILITY.json) conservent versions,
règle, sources et empreintes. Le script est reproductible avec l'environnement
isolé indiqué dans la demande; il refuse d'écraser son gel précédent. Les
contrôles d'agrégation, de temporalité, de warm-up et de conservation des hashes
sources sont passés. Ces contrôles ne valident ni performance financière ni
passage FTMO.
