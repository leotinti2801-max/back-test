# Backtest ICT/SMC — 4 novembre 2026

**Cette formalisation est trop restrictive pour notre objectif de fréquence :
un seul trade exécuté sur2021.** Il est gagnant, mais une observation ne permet
ni d'estimer une probabilité fiable, ni d'augmenter les mises. Aucun paramètre
n'a été modifié après les résultats pour fabriquer davantage de trades.

## Résultats après tous les coûts modélisés

| Période | Coûts | Trades | Gains / pertes | Net EUR | Risque prévu du trade EUR |
| --- | --- | ---: | ---: | ---: | ---: |
| 4janvier–31mars | Base | 1 | 1 / 0 | +313,51 | 124,88 |
| 4janvier–31mars | Renforcés | 1 | 1 / 0 | +285,62 | 124,00 |
| 4janvier–31décembre | Base | 1 | 1 / 0 | +313,51 | 124,88 |
| 4janvier–31décembre | Renforcés | 1 | 1 / 0 | +285,62 | 124,00 |

Les lignes concernent le **même trade** et des périodes imbriquées, pas quatre
observations indépendantes. Le maximum effectif est une entrée dans une journée,
avec une seule journée de trading dans l'année. Le net de base représente0,314 %
du capital simulé100000 EUR. La stratégie reste en recherche, non promue.

Sur le même trimestre, le précédent candidat simple2R avait61 trades et
+839,28 EUR en base/+719,24 renforcé. Il ne faut pas comparer une année
partielle de cette ancienne stratégie à l'année de la nouvelle. La comparaison
commune trimestrielle suffit à constater que l'ICT n'améliore pas ici le net
total et réduit fortement l'activité. Zéro perte sur un trade n'établit pas
un risque faible ni un taux de réussite durable.

## L'histoire du trade du6janvier

Vente EURUSD, heures UTC (Londres est en heure d'hiver) :

1. Le range08–09h est figé : haut mid1,234045, bas mid1,232220.
2. Le sweep est connu à12h45 : dépassement du haut puis clôture revenue dans
   le range. Le pivot M5 à casser avait déjà été confirmé à12h10.
3. À12h50, clôture sous le niveau MSS1,233355, corps baissier assez grand face
   à l'ATR antérieur, et FVG baissier confirmé entre1,233870 et1,234120.
4. Une nouvelle M5 clôture dans ce FVG ; entrée sur la quote suivante à13h00.
   Prix exécuté de base1,233960 ; stop ask1,234570 ; cible ask1,232230,
   l'autre bord exécutable du range, connu dès09h.
5. Le TP est atteint dans la M1 de13h56 ; clôture modèle13h57. Résultat
   +313,51 EUR, soit environ2,51R encaissés selon le calcul EUR du moteur.

Le risque maximum prévu est125 EUR ; l'arrondi de quantité conduit à124,88.
La quantité modélisée est230000 EUR, contre214000 en coûts renforcés. La
conversion en lots MT5 dépend du contrat du symbole, encore non qualifié.
Ce trade ne résulte pas d'une hausse de mise fondée sur une probabilité.

L'order block est annoté : dernière M5 haussière dans les cinq précédant MSS,
bornes mid1,234120–1,234510. Il n'est pas un filtre et n'est connu comme
annotation de cet événement qu'à12h50. Aucun ordre institutionnel n'est observé.

## Pourquoi presque aucun trade ne passe

Sur l'année, les étapes observées en base sont :

| Étape ou refus | Nombre |
| --- | ---: |
| Sessions au range complet | 257 |
| Sweeps avec pivot MSS disponible, setups commencés | 735 |
| Sweeps sans pivot MSS admissible | 257 |
| Stop touché avant entrée, setup annulé | 394 |
| Première cassure MSS rejetée | 151 |
| Attente MSS expirée | 143 |
| MSS + FVG confirmés | 22 |
| Attente de retour FVG expirée | 13 |
| FVG invalidé par clôture | 2 |
| Setup terminé à la fin de fenêtre | 25 |
| Retours FVG produisant une tentative | 5 |
| Tentatives refusées au contrôle d'ordre | 4 |
| Entrée exécutée | 1 |

Ces lignes mélangent étapes intermédiaires et motifs : elles ne doivent pas
être additionnées. Parmi les151 premières cassures rejetées,105 manquent
d'amplitude face à l'ATR précédent et102 n'ont pas de FVG directionnel valide ;
ces deux motifs peuvent se cumuler.

Le plan impose que le FVG soit **déjà confirmé à la clôture de la première
cassure MSS**. Cette convention exclut une impulsion dont le FVG ne devient
visible que sur la bougie suivante. Le retour doit ensuite clôturer dans le
FVG dans30minutes : une simple mèche ne suffit pas. Ce sont deux restrictions
fortes de cette version, pas la définition universelle d'ICT/SMC.

Les quatre tentatives refusées sont précisément :

| Date | Motif en base | Constat |
| --- | --- | --- |
| 12janvier | Cible structurelle sous2R | Ratio prévu0,453R |
| 24juin | Frais trop grands face au stop | Ratio prévu5,812R mais garde de friction violée |
| 5octobre | Cible structurelle sous2R | Ratio prévu0,262R |
| 18novembre | Frais trop grands face au stop | Ratio prévu3,514R mais garde de friction violée |

Les scénarios renforcés refusent les mêmes tentatives. Aucun de ces refus
n'est présenté comme un gain manqué : leur résultat hypothétique n'a pas été
simulé. Les setups sont consommés à la première tentative, même refusée.
Le stop n'est jamais éloigné pour rendre une entrée possible.

## Probabilités et mises : ce qui est réellement calculé

Avant l'entrée du6janvier, **aucun trade de cette stratégie n'était clôturé**.
La fréquence empirique est donc inconnue. L'éventuelle valeur Laplace0,5
est un a priori mathématique descriptif, pas une probabilité prédictive validée.
Lors des tentatives suivantes, le passé ne contient qu'un gain sur une observation.

`PRIOR_AT_ENTRY.csv` conserve, à chaque tentative, uniquement les clôtures
connues à cet instant : effectif, gains, pertes, fréquence lissée et intervalle
Wilson descriptif. Les résultats ultérieurs ne sont pas lus pour ce calcul.
L'indépendance des observations et la calibration d'un modèle ne sont pas
établies ; une borne Wilson nominale ne les remplace pas.

Le multiplicateur de risque reste donc **1**, budget125 EUR/trade, maximum
500 EUR de risque prévu cumulé/jour,4 entrées et une seule position. L'exigence
de100 observations antérieures est un seuil de revue, pas une preuve suffisante
ni un bouton permettant d'activer les grosses mises. Aucun modèle de probabilité
indépendamment calibré n'a été fourni ou validé dans cet essai.

Les lots peuvent varier avec la distance du stop et les coûts, même à risque
constant. Une confluence FVG/OB/EMA/ADX n'est pas transformée en pourcentage de
réussite et ne déclenche pas d'augmentation de mise.

## Graphiques et indicateurs

Les graphiques distinguent les éléments de décision des aides descriptives :
range Londres, sweep, niveau MSS gelé, FVG et order block avec leurs heures de
confirmation, stop et cible ; EMA20/50 et Bollinger sur le prix, puis ATR,
ADX et RSI en panneaux séparés. Seul l'ATR précédent conditionne ici le
déplacement. Les autres indicateurs ne sont pas des votes indépendants.
La galerie et les empreintes sont conservées sous `charts/`.

## Données et portée du résultat annuel

Les quatre simulations n'ont rencontré aucun trou **pendant une position**.
La stratégie n'était pas exposée au trou d'avril qui bloque l'ancien test
London3R. Elle a toutefois annulé six sessions après données de signal
incomplètes et refusé trois ranges incomplets. Les cases absentes restent
absentes : cet essai n'a pas réparé l'historique ni certifié toutes les
opportunités réelles du marché.

Le total annuel est donc celui de la politique déclarée, qui annule les
sessions en cas de manque de données. Il ne prouve pas qu'une source complète
aurait produit un seul trade. Tous les fichiers2021 ont déjà été consultés
en développement ; le trimestre et l'année ne sont pas un test indépendant.

Les règles FTMO officielles et la définition contractuelle de l'equity
restent non vérifiées. Un drawdown de solde clôturé nul avec une seule clôture
gagnante ne mesure pas l'exposition flottante. Aucun passage de Challenge et
Vérification en moins d'un mois n'est validé.

## Décision

Cette version est conservée comme essai **non concluant et trop peu actif**.
Les anciens résultats et sources restent intacts. Les17 tests synthétiques
passent ; les empreintes des sources sont gelées avant calcul. Aucune période,
aucun seuil ni règle de retour n'a été retouché après ce résultat.

La prochaine hypothèse à définir séparément serait notamment de distinguer
MSS puis confirmation ultérieure du FVG, plutôt que leur simultanéité ; il
faudrait l'annoncer avant un autre essai, garder ce résultat et réserver des
données qualifiées encore inutilisées à la validation.
