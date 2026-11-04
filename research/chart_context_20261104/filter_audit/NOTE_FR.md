# Audit des filtres H1, ADX et niveaux — 4 novembre 2026

**Les deux filtres échouent au critère préannoncé : réduire le taux de pertes et
augmenter le net dans les deux scénarios de coûts.** Les pertes absolues baissent,
mais les trades et les bénéfices conservés baissent aussi. Aucun filtre n'est promu.

Audit en lecture seule des résultats du 4 janvier au 1er avril 2021, fin exclue.
Aucun backtest, calcul de trajectoire, indicateur recalculé ou HTTP. Les sommes
et appartenances ci-dessous proviennent des journaux existants ; ce trimestre
reste du développement déjà consulté.

## Résultats vérifiés

| Portefeuille TP2 | Trades | Gains / pertes | Taux de pertes | Net base | Net stress |
| --- | ---: | ---: | ---: | ---: | ---: |
| V03 témoin | 61 | 31 / 30 | **49,18 %** | **839,28 EUR** | **719,24 EUR** |
| H1 + ADX | 33 | 16 / 17 | **51,52 %** | **582,37 EUR** | **528,28 EUR** |
| H1 + ADX + niveaux | 24 | 12 / 12 | **50,00 %** | **−20,95 EUR** | **−66,44 EUR** |

Les effectifs et signes sont identiques entre coûts pour chaque variante.
La baisse 30 → 17 → 12 des pertes ne démontre donc pas une meilleure probabilité
de gain. H1+ADX supprime 16 pertes du témoin, mais ajoute trois nouvelles pertes :
30 − 16 + 3 = 17. La variante niveaux en supprime 20 et en ajoute deux :
30 − 20 + 2 = 12.

Nuance : H1+ADX améliore le net moyen par trade, de 13,76 à 17,65 EUR en base
et de 11,79 à 16,01 EUR en stress. Sa fréquence diminue cependant, son taux de
pertes augmente et son drawdown de solde clôturé passe de 420,05 à 488,13 EUR
en base, de 431,47 à 511,06 EUR en stress. La variante niveaux réduit ce drawdown
à 311,61 / 314,82 EUR avec seulement 24 trades et un net négatif. Ces drawdowns
ne certifient pas les limites d'equity FTMO.

## Quels gains et pertes disparaissent ?

Appariement par heure d'entrée et direction. Pour les six comparaisons, les
trades communs ont exactement le même net : toute différence vient des trades
propres à chaque parcours, qui incluent leurs coûts déjà déduits.

| Comparaison | Communs / référence seule / nouveaux | Pertes retirées, montant absolu base | Gains sacrifiés base | Net des nouveaux base | Delta net base / stress |
| --- | --- | ---: | ---: | ---: | ---: |
| H1+ADX contre V03 TP2 | 26 / 35 / 7 | 1 339,32 EUR, 16 trades | 1 643,35 EUR, 19 trades | +47,12 EUR | **−256,90 / −190,96 EUR** |
| H1+ADX+niveaux contre V03 TP2 | 19 / 42 / 5 | 1 550,85 EUR, 20 trades | 2 327,89 EUR, 22 trades | −83,19 EUR | **−860,23 / −785,67 EUR** |
| Ajout des niveaux à H1+ADX | 21 / 12 / 3 | 272,73 EUR, 5 trades | 1 032,07 EUR, 7 trades | +156,01 EUR | **−603,33 / −594,72 EUR** |

La formule de rapprochement est :
`delta = différence sur communs + net des nouveaux − net des trades référence seuls`.
Toutes les sommes, y compris gains et pertes stress, figurent dans
`PNL_DECOMPOSITION.csv` et `AUDIT.json`. Résidu maximal inférieur à 1e-8 EUR.

Ces portefeuilles ne sont pas de simples sous-ensembles. Pour H1+ADX, les sept
nouvelles entrées correspondent à cinq pauses et deux positions ouvertes dans
le témoin. Inversement, parmi les 35 entrées retirées du témoin, 32 sont rejetées
par le contexte et trois par une pause propre au nouveau parcours. Après ajout
des niveaux, les trois nouvelles entrées correspondent à deux pauses et une
position ouverte dans H1+ADX. Les journaux expliquent ces états ; aucun refus
non simulé n'a reçu un gain hypothétique.

## Ce que le contexte mesure réellement

Le code filtre la **direction du corps de la dernière H1 complète close**, puis
exige **ADX14 sur M5 ≥ 25**. Il ne calcule pas un ADX H1 et n'utilise pas EMA20
dans cet essai. Sur les 202 cassures communes : 56 passent le contexte,
145 sont rejetées et une est inconnue pour chauffe ADX. Les motifs se répartissent
en 72 ADX seuls, 58 ADX+corps H1, 15 corps H1 seuls et une chauffe inconnue.
Les vérifications du compte ne sont pas exécutées après un rejet de contexte.

L'ajout de niveaux considère des fractales H1 strictes confirmées depuis au
plus 24 heures, au côté exécutable et devant le prix d'entrée jusqu'au TP2.
Un niveau déjà visité n'est pas un veto ; une observation incomplète depuis sa
confirmation produit `FRESHNESS_UNKNOWN`.

Il existe **23 décisions distinctes comportant un motif de niveau** : 22 avec
fraîcheur inconnue et deux avec niveau intact, dont une commune aux deux motifs.
Les motifs ne s'additionnent pas. Parmi les 12 trades H1+ADX absents après
l'ajout des niveaux, dix sont refusés pour fraîcheur inconnue seule, un cumule
inconnu et niveau intact, un est refusé pour niveau intact seul. L'essentiel de
la contraction vient donc d'une incertitude de données, pas d'un obstacle dont
le pouvoir prédictif serait établi.

Les deux TP H1+ADX disparaissent : le 25 janvier 09:05 pour niveau intact
(+244,74 EUR base), le 27 janvier 09:10 pour fraîcheur inconnue
(+245,63 EUR base). Cela explique leur absence sans déduire qu'un niveau intact
garantit un retournement, ni qu'une donnée manquante identifie une mauvaise entrée.

## Vérifications et limites

Les six résumés sont recalculés depuis les clôtures et les six décompositions
se réconcilient. Les 808 contextes journalisés, soit 202 décisions × deux variantes
× deux coûts, respectent les heures connues H1/M5 ; toutes les entrées filtrées
respectent corps H1 aligné et ADX≥25. Les niveaux sérialisés considérés et leurs
motifs concordent avec les règles du code. Les sources gelées sont inchangées.
Ces contrôles ne recalculent pas indépendamment chaque indicateur ou parcours
de pivot ; 808 enregistrements ne sont pas 808 observations indépendantes.

Pièces : `PORTFOLIO_METRICS.csv`, `PNL_DECOMPOSITION.csv`,
`TRADE_MEMBERSHIP.csv`, `CONTEXT_DECISIONS_CHECKED.csv`, `AUDIT.json` et empreintes.
Le résultat des continuations n'intervient dans aucun de ces critères de filtre.
Aucune validation indépendante, conformité FTMO ou rentabilité future n'est établie.
