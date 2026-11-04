# EURUSD : fréquence accrue, levier et limites — 4 novembre 2026

**La fréquence progresse jusqu'à quatre entrées/jour, sans amélioration robuste
du bénéfice net dans les deux hypothèses de coûts.** Le plafond de levier30 ou100
ne change aucun trade à risque identique. Le bot V03 actif reste inchangé ; le
nouveau code paramétrable et tous les résultats sont conservés en recherche.

## Essai annoncé avant calcul

Le même range08–09h Europe/London, les mêmes cassures et réarmements, le stop
opposé au range, la cible prévue3R, une seule position et la pause24h après
deux pertes sont conservés. Les coûts et le change de chaque flux sont ceux
du moteur gelé. Les variations portent sur durée, fin de séance, granularité
de confirmation, plafond d'entrées et plafond de levier, selon le plan.

La fenêtre habituelle finit à14h30, sortie forcée16h. La fenêtre élargie finit
à16h, sortie17h. Les entrées restent strictement avant la fin de fenêtre.
Une durée60min ferme au plus tard60min après l'entrée ou à la fin de séance,
selon la première échéance. M1 signifie une décision après clôture d'une M1,
dès09h01, jamais pendant cette même bougie.

Le risque prévu reste125 EUR/trade et500 EUR cumulés/jour. Pour la variante
destinée à permettre8 entrées à budget quotidien constant, il est62,50 EUR.
Le levier30/100 est testé séparément du risque, sans supposer son autorisation
FTMO. Il ne s'agit ni d'un achat de challenge ni d'un bot branché à MT5.

9 variantes ×4 périodes ×2 coûts =72 simulations. Le trimestre commun va du
4janvier au1eravril2021 exclu. Il a été choisi en connaissance du trou d'avril
et reste du développement. Les trois fenêtres28j commencent le4janvier,
le1erfévrier et le1ermars, avec un compte neuf et des pauses remises à zéro.
Ce sont des diagnostics de rythme, pas des phases FTMO validées.

## Trimestre commun, coûts inclus

| Variante | Trades base | Gagnants nets | Maximum/jour | Net base EUR | Net coûts renforcés EUR | DD solde clôturé EUR, base |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V03 témoin | 61 | 50,8 % | 2 | +642,37 | +504,22 | 420,05 |
| Même bot, plafond levier30 | 61 | 50,8 % | 2 | +642,37 | +504,22 | 420,05 |
| Même bot, plafond levier100 | 61 | 50,8 % | 2 | +642,37 | +504,22 | 420,05 |
| Fenêtre élargie, durée habituelle | 61 | 49,2 % | 2 | −44,46 | +92,29 | 652,17 |
| Durée60min, fenêtre habituelle | 94 | 50,0 % | 3 | +543,20 | +327,72 | 338,78 |
| Fenêtre élargie +60min, cap4 | 108 | 50,9 % | 4 | +685,81 | +444,43 | 338,78 |
| Même variante, cap8, risque125 | 108 | 50,9 % | 4 | +685,81 | +444,43 | 338,78 |
| Même variante, cap8, risque62,50 | 108 | 50,9 % | 4 | +339,44 | +221,42 | 167,92 |
| Même variante62,50, signauxM1 | 117 | 46,2 % | 4 | +138,53 | +33,39 | 172,39 |

En coûts renforcés, la fenêtre élargie habituelle clôture60 trades et le M1
115 ; les autres effectifs sont inchangés. Les montants plus favorables du
scénario renforcé sur la première variante ne signifient pas que des frais
plus élevés améliorent intrinsèquement une stratégie : les parcours divergent
via les pertes nettes, les pauses et les entrées suivantes (voir plus bas).

Le couple fenêtre élargie+60min ajoute47 trades, soit+77 %. Le net de base
augmente seulement de43,45 EUR, alors que le net renforcé baisse de59,78 EUR.
Le drawdown clôturé est plus faible, mais ce résultat ne certifie aucune limite
FTMO d'equity. C'est un compromis fréquence/coûts, pas une domination du témoin.

Les critères préannoncés exigeaient une différence de net positive dans les
deux coûts pour soutenir une amélioration de développement. Aucune variante
ne satisfait ce critère. Aucune promotion ni retouche de seuil après résultats.

## Quatre trades maximum ne signifie pas quatre par jour

Sur63 séances lundi–vendredi :

| Nombre d'entrées dans une séance | V03 | Fenêtre élargie+60min | M1 à62,50 EUR |
| --- | ---: | ---: | ---: |
| 0 | 9 | 5 | 9 |
| 1 | 47 | 18 | 13 |
| 2 | 7 | 32 | 27 |
| 3 | 0 | 6 | 6 |
| 4 | 0 | 2 | 8 |

La moyenne est0,97 puis1,71 puis1,86 entrée/séance respectivement.
Augmenter le cap de4 à8 ne crée aucune entrée dans le brasM5 testé.
Diviser le risque par deux ne crée pas non plus de cassures ; cela réduit
les tailles et les montants, avec arrondis. Le M1 ajoute des décisions et
davantage de refus, sans augmenter le maximum quotidien observé.

## Pourquoi les trades sont refusés et pourquoi ils perdent

| Motif non exclusif, trimestre base | V03 | Élargie+60min | M1 à62,50 EUR |
| --- | ---: | ---: | ---: |
| Position déjà ouverte | 104 | 67 | 218 |
| Pause après deux pertes nettes | 33 | 56 | 190 |
| Ouverture plus au-delà du range | 2 | 4 | 5 |
| Première cotation trop tardive | 2 | 4 | 2 |

Les refus peuvent se cumuler. Un signal refusé n'est pas un gain manqué établi.
La durée plus courte libère le compte mais les pertes nettes déclenchent
toujours les pauses. Le M1 ajoute de nombreuses cassures alors que le compte
est occupé ou en pause ; le plafond de levier ne lève aucune de ces règles.

Les journaux `LOSSES.csv` expliquent **chaque perte exécutée**, sans lui
inventer une cause économique. En base :

- V03 :30 pertes, dont12 au stop et18 à la sortie horaire ;
- élargie+60min :53 pertes, dont1 au stop et52 à l'horaire ;
- M1 à62,50 :63 pertes, dont4 au stop et59 à l'horaire.

Sur108 trades de la variante élargie+60min,107 finissent à l'horaire,1 au stop
et **aucun au TP3R**. Le rendement moyen réalisé est environ0,052R/trade contre
0,085R pour V03. Le prix peut avancer sans atteindre3R dans le temps imparti.
Plus de sorties courtes augmente la place des coûts dans les gains encaissés.
Tous les nets publiés incluent déjà ces coûts ; ils ne sont pas retirés deux fois.

## Levier : le plafond n'était pas le frein

L'audit des61 trades V03 de chaque coût reproduit exactement tailles, prix,
risque et soldes à partir du cache qualifié. En base, les tailles vont de30k
à150k EUR et le levier effectif maximal du modèle vaut1,4894×. Le plafond10
ne contraint **aucun** des61 trades ; en coûts renforcés, aucun non plus.

Passer ce plafond à30 ou100, avec le budget125 EUR/trade, ne modifie aucune
taille observée. Les nouvelles simulations reproduisent également les mêmes
trades, décisions et résultats pour ces bras. La taille est déterminée par
le risque au stop avant d'atteindre le plafond de levier. Accroître les tailles
demanderait donc de changer le budget de risque, avec des pertes potentielles
plus fortes ; cela ne démontre aucun avantage prédictif supplémentaire.

La marge calculée dans `leverage_audit/` est un proxy du modèle. Les règles
du symbole, le contrat et les conditions de marge MT5/FTMO ne sont pas vérifiés.
Les scénarios30/100 ne sont pas présentés comme des leviers autorisés du compte.

## Coûts et changement de parcours

Sur la fenêtre élargie habituelle, le10mars un petit gain net de+0,91 EUR en
base devient−1,13 EUR en renforcé, après la perte du9mars. Le renforcé déclenche
une pause jusqu'au11mars17hUTC. Il retire alors deux entrées du11mars qui
perdent−124,56 et−119,01 EUR en base. Les pauses des jours suivants changent
aussi. Ce mécanisme explique pourquoi le total renforcé peut dépasser le total
de base bien que les frais unitaires soient plus élevés.

Sur le trimestre,58 entrées sont communes,3 sont propres à la base et2 au
renforcé. La décomposition exacte du différentiel renforcé−base est :
−105,59 EUR sur les entrées communes, +366,98 EUR provenant de l'absence
des3 entrées de base, puis−124,64 EUR pour les2 entrées propres au renforcé,
soit+136,75 EUR. Cette identité comptable explique le total sans présenter
les trois refus comme un avantage prédictif validé.

SurM1, le18janvier13h34UTC, +0,86 EUR devient−1,04 EUR ; la pause renforcée
retire deux entrées le19janvier. Il faut comparer les parcours complets et
leurs trades propres, sans supposer des calendriers identiques entre coûts.
Les événements et la décomposition sont dans `cost_path_audit/`.
Les cibles de prix intègrent aussi les coûts prévus : sur le short du27janvier,
le TP survient à14h34 en base contre14h36 en renforcé, confirmé par les quotes
ask. Ces différences ne sont pas une nouvelle simulation inventée après coup.

## Trois diagnostics28jours, comptes remis à zéro

Chaque cellule donne **net base / net renforcé en EUR**.

| Variante | 4jan–1fév exclu | 1fév–1mars exclu | 1mars–29mars exclu |
| --- | ---: | ---: | ---: |
| V03, levier10/30/100 | +396,54 / +358,37 | +518,77 / +462,53 | −235,07 / −270,54 |
| Fenêtre élargie habituelle | −135,57 / −158,96 | +591,53 / +542,95 | −380,77 / −166,14 |
| Durée60min habituelle | +19,66 / −42,28 | +464,06 / +386,60 | +60,39 / +0,56 |
| Élargie+60min, cap4 ou8 à125 EUR | +19,66 / −42,28 | +488,97 / +405,86 | +178,09 / +98,02 |
| Élargie+60min à62,50 EUR | +12,92 / −15,79 | +239,79 / +196,58 | +87,73 / +49,80 |
| Même varianteM1 | −18,80 / −22,10 | +107,70 / +59,54 | +84,32 / +41,83 |

Ces fenêtres se trouvent dans le même trimestre ; ce ne sont pas de nouvelles
preuves indépendantes et leur somme ne doit pas être assimilée au portefeuille
continu. Les pauses repartent de zéro dans chaque tentative. Le meilleur net
observé dans cette petite série vaut591,53 EUR, soit0,592 % du capital100000.
Ce constat ne justifie pas d'annoncer le passage des deux phases en moins d'un
mois. Aucun évaluateur de cibles FTMO non vérifiées n'a été appliqué.

## Qualité, vérification et suite

Les72 simulations n'ont rencontré aucune exposition inconnue sur leurs
périodes respectives. Cela ne certifie pas toutes les cotations du marché.
Le moteur conserve son arrêt avec résultat total inconnu en cas de trou actif,
vérifié par un nouveau test. L'année2021 entière reste inconnue à cause de
la position du1eravril et de la minute11h40UTC manquante.

Les6 nouveaux tests vérifient la reproduction du signal, l'isolation du moteur,
la causalitéM1, le réarmement, la sortie60min et la réutilisation du compte,
le maintien des pauses et l'arrêt sur données inconnues. Les sources gelées
et le témoin sont contrôlés par empreintes ; l'audit indépendant complète les
tests :72 cellules et3014 lignes de trades vérifiées, aucun écart de cash
recomposé. La parité des bras levier30/100 est vérifiée à l'octet sur les journaux
comparables. Aucun indicateur ajouté, aucun ordre réel, aucune réussite80 % affirmée.

La prochaine preuve utile reste un historique bid/ask qualifié et encore
inutilisé, puis une validation de la robustesse aux coûts avec les conditions
officielles du compte. Le code permet désormais d'évaluer la fréquence sans
confondre plafond d'entrées, marge disponible et risque monétaire. Les variantes
sont conservées ; aucune combinaison supplémentaire n'est choisie après ce lot.
