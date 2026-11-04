# Forex simple — London Range V01, 3 novembre 2026

## Livraison

À la demande directe de simplification, le nouvel axe remplace l'ancienne entrée
H4/M30 : **une seule stratégie EUR/USD, sans indicateur, dont le signal tient
dans un fichier de 40 lignes physiques**. Les coûts, le dimensionnement, la
simulation et les diagnostics sont séparés ; le programme complet comporte
nécessairement davantage de code. Les versions antérieures sont conservées.

Le signal utilise uniquement le range 08–09 h Londres, les clôtures M5 après
09 h et avant midi, et une mémoire de deux sens déjà tentés. Stop de l'autre
côté du range, cible prévue à 2R, sortie forcée à 16 h Londres. Une seule
position ouverte, deux tentatives au plus par jour, une par sens.

Le risque prévu reste de 250 € par position, avec 500 € prévus cumulés au plus
par jour sur 100 000 € simulés. Après deux pertes consécutives, pause de 24 h.
Le risque effectif peut dépasser le risque prévu en présence de gaps ou d'effets
de change. Ces contrôles propres au prototype ne certifient pas les limites FTMO.

## Résultats des calculs effectivement exécutés

Une seule version de règles a été gelée avant les résultats. Les deux scénarios
de coûts ne représentent pas deux stratégies différentes. Le second lancement
vérifie deux corrections de causalité/journalisation, sans aucun changement de
paramètre ; tous les CSV de trades clos sont identiques à ceux du premier.

| Fenêtre | Trades clos | Gains / pertes | Net établi | Avec coûts augmentés | Statut |
| --- | ---: | ---: | ---: | ---: | --- |
| 04/01–18/02/2021, fin exclue, 45 jours | 27 | 13 / 14 | +670,63 € | +603,82 € | Chemins sélectionnés résolus ; marché complet non certifié |
| Année 2021 demandée | 49 avant arrêt | 20 / 29 avant arrêt | Année inconnue | Année inconnue | Exposition non résolue au 1er avril |

Sur les seuls trades clos avant l'arrêt annuel, le net est de **−246,39 €** en
coûts de base et **−382,62 €** en coûts augmentés. Ces nombres ne sont pas des
résultats annuels. Ils excluent notamment le résultat inconnu de la position
ouverte au moment du trou. Sa commission d'entrée établie reste conservée à part.

Sur 45 jours, le profit factor vaut 1,25 et le drawdown sur clôtures 1 044,68 €.
Le gain net représente environ 0,67 % des 100 000 € simulés. Le résultat est trop
limité pour une conclusion de performance et ne valide pas les phases FTMO.

La fenêtre courte est incluse dans l'année : les 27 et 49 trades ne s'ajoutent
pas comme des observations indépendantes. Toutes ces données 2021 ont déjà été
consultées pendant le développement.

## Pourquoi certains trades n'entrent pas

Les journaux enregistrent chaque M5 évaluée et distinguent absence de cassure,
sens déjà consommé, données incomplètes, refus et entrée. Une tentative refusée
n'est pas recyclée sur le même sens.

- Sur 45 jours : quatre refus, tous dus à la pause après deux pertes
  consécutives (6 et 13 janvier, 10 et 17 février).
- Sur le préfixe annuel : dix refus pour cette pause, et un refus le 19 mars
  car la quote d'entrée n'était plus au-delà du range. Un tel refus ne démontre
  pas qu'un gagnant a été manqué.
- Les week-ends sont explicitement hors session. Une journée dont le range
  manque n'est pas appelée « journée sans occasion de marché ».
- Après l'arrêt du 1er avril, les décisions et trades du reste de l'année ne
  sont pas calculés. Ils ne deviennent ni des zéros ni des réussites.

## Pourquoi les pertes se produisent dans le modèle

Sur les 27 trades courts : neuf pertes au stop, cinq pertes à l'échéance,
neuf gains à l'échéance et quatre gains à la cible. Sur les 49 trades clos du
préfixe annuel : quatorze pertes au stop, quinze pertes à l'échéance,
seize gains à l'échéance et quatre gains à la cible.

Le mécanisme observable des stops est une cassure clôturée suivie d'un mouvement
contraire jusqu'au stop opposé. Les pertes horaires indiquent un résultat net
négatif au terme disponible, sans liquidation préalable au stop ou au TP. Aucune
cause macroéconomique de ces mouvements n'est démontrée.

Le fait que 31 des 49 clôtures soient horaires et seulement quatre des TP
souligne le rôle de l'horizon de détention. Ce constat ne justifie pas de choisir
un nouvel objectif ou une nouvelle heure après avoir vu leurs résultats. Aucun
indicateur supplémentaire ni changement de TP n'a été introduit.

## Pourquoi le calcul annuel s'arrête

Une position acheteuse s'ouvre le 1er avril à 08:25 UTC (10:25 Paris). La minute
de **11:40 UTC (13:40 Paris)** manque alors que la position est encore ouverte.
La quote suivante ne permet pas de connaître le parcours manquant. Le portefeuille
continu s'arrête et le résultat total reste null.

Aucune interpolation ni suppression de ce trade n'a été utilisée pour obtenir
un résultat annuel réputé complet. Les enveloppes de liquidation M1 exportées
ne sont pas des chemins tick ni une définition contractuelle de l'equity FTMO.

## Contrôles et revue

**34 tests logiciels exécutés et réussis**, dont 12 propres à cette nouvelle
méthode. Ils couvrent les horloges Londres, la clôture plutôt que la mèche,
la première tentative de chaque sens, l'invariance aux prix futurs et à la fin
future du cache, les données manquantes, les coûts, la taille et la pause.

Une revue indépendante a identifié deux limites corrigées : une fin future de
grille ne doit pas supprimer un signal matinal observable ; l'heure de l'arrêt
et les observations intermédiaires doivent correspondre à la première minute
inconnue, pas seulement à l'heure d'entrée. Ces corrections n'ont changé aucun
trade clos ni aucun PnL clos sur les données utilisées.

Un audit indépendant a recalculé les flux de **152 lignes de trades clos** des
deux fenêtres et deux scénarios : écart monétaire maximal **0 €**. Il vérifie
aussi les quantités, les soldes, la pause et les plafonds de risque prévu. Ces
152 lignes comprennent des fenêtres et scénarios corrélés, pas 152 observations
indépendantes.

## Situation FTMO et prochaine amélioration utile

Le projet vise FTMO 2-Step, 100 000 € en euros, les deux phases en moins d'un
mois si possible. Les règles officielles et leur calcul d'equity restent à
vérifier. Aucun statut de réussite FTMO n'est produit et aucun ordre réel n'est
activé.

Cette version est plus simple et produit davantage d'entrées observées. Sa
rentabilité stable n'est pas établie : le préfixe annuel est déficitaire et le
reste de l'année n'est pas résolu. La prochaine action est de qualifier les
données manquantes et d'obtenir une période encore inutilisée, avant de retoucher
la règle. Le code ne sera pas « perfectionné » en sélectionnant uniquement les
45 jours positifs ou en multipliant les paramètres jusqu'à améliorer 2021.

Pièces : `simple_london_v01_02/FREEZE_BEFORE_RESULTS.json`, `RESULTS.json`,
CSV de décisions/trades/enveloppes et manifestes ;
`simple_london_v01_02/analysis/CASH_AUDIT.json`, `REFUSAL_REASONS.json` et
`TRADE_CASES.csv`. Le premier run et ses sources antérieures restent archivés.
