# Pourquoi le scénario coûteux peut finir plus haut — audit du 4 novembre 2026

**L'inversion EXTENDED est expliquée par les journaux : les coûts changent le
signe de petits résultats nets, donc les pauses et les entrées suivantes.**
Le stress ne conserve pas un portefeuille de trades identique. Les cibles de
prix dépendent aussi des coûts prévus dans le moteur. Cette constatation
explique les nombres observés ; elle ne démontre pas un avantage économique
à payer davantage de frais.

Lecture seule de `run_01`, sans nouvel appel au moteur de simulation. Les
sommes des clôtures des **36 paires variante/période** reproduisent les résultats
existants. Les trajectoires EXTENDED et M1 du trimestre sont détaillées ci-dessous.
Les chiffres de trésorerie sont repris des CSV, avec décomposition arithmétique ;
les états pertes/pause sont annotés depuis leurs clôtures selon le code existant.
Tous les horaires de cette note sont UTC.

## Ce que le stress change effectivement

`simple_forex/runner.py` applique une commission aller-retour ×1,5 et un
glissement marché ×2. Il recalcule le prix d'entrée, la distance de risque et
la quantité au même budget monétaire. Il recalcule aussi la cible :

```
cible = entrée + direction × [3 × (distance entrée-stop + commission + glissement) + commission]
```

Sur une entrée commune de même direction et de même stop, ces paramètres
déplacent ici la cible de 0,00017, soit 1,7 pip EURUSD, plus loin dans le sens
du trade. Les différences numériques commencent donc dès le 4 janvier : par
exemple, EXTENDED à 09:20 entre à 1,22921 en base contre 1,22922 en stress,
avec cibles 1,23850 et 1,23867. Le résultat vaut −120,4770 EUR contre
−122,2365 EUR. Ce premier écart de prix ne change pas encore les entrées suivantes.

À la clôture, `close_position` incrémente le compteur pour un net négatif,
le remet à zéro pour un net positif et le conserve pour zéro. Deux pertes nettes
consécutives déclenchent 24 heures de pause depuis la sortie effective. Une
petite variation de frais autour de zéro peut donc modifier le parcours du compte.

## EXTENDED Q1 : de −44,46 à +92,29 EUR

Trois premières divergences doivent être distinguées :

| Nature | Première observation vérifiée |
| --- | --- |
| Prix/coûts | Entrée commune du 4 janvier à 09:20 ; prix, cible et net diffèrent. |
| Signe net et compteur de pertes | Entrée du 21 janvier à 09:30 : +0,8893 EUR base devient −1,1120 EUR stress à la même sortie horaire de 17:00. |
| Heure de sortie | Entrée du 27 janvier à 09:10 : TP base clos à 14:34, TP stress à 14:36. |
| Décision d'entrée/refus | Le 11 mars à 13:15 : base entre, stress refuse pour pause active. |

Le changement de signe du 21 janvier met le compteur stress à une perte ; la
perte du 22 janvier le porte à deux et déclenche une pause jusqu'au samedi
23 janvier à 17:00. Elle expire avant la prochaine séance et ne change aucune
entrée du trimestre. Ce premier changement d'état n'explique donc pas à lui seul
l'écart de nombre de trades.

La chaîne qui change les entrées est celle-ci :

1. Le 9 mars, les deux branches clôturent une perte ; leur compteur est à un.
2. Le 10 mars, entrée commune à 09:10, sortie horaire commune à 17:00 :
   **+0,9075 EUR en base**, mais **−1,1347 EUR en stress**. La base remet son
   compteur à zéro ; le stress compte sa deuxième perte et se met en pause
   jusqu'au **11 mars à 17:00**.
3. Le 11 mars, la base exécute les entrées de 13:15 et 14:45, closes aux stops
   pour **−124,5642** et **−119,0090 EUR**. Le stress les refuse explicitement
   pour `PAUSE_AFTER_TWO_LOSSES`. Les deux stops de base déclenchent sa propre
   pause jusqu'au **12 mars à 16:44**.
4. Le 12 mars à 09:20, base encore en pause, stress disponible : seul le stress
   entre et perd **−122,6644 EUR** au stop à 16:43.
5. Le 15 mars, la perte commune est la première perte de base après expiration
   de sa pause, mais la deuxième du stress après celle du 12. Le stress se
   remet en pause jusqu'au **16 mars à 17:00**.
6. Le 16 mars à 09:10, seul le compte de base entre ; il perd **−123,4026 EUR**
   au stop à 13:48. C'est sa deuxième perte : pause jusqu'au
   **17 mars à 13:48**. Le stress refuse cette entrée pour sa pause active.
7. Le 17 mars à 09:05, seul le stress entre, car la base est encore en pause.
   Il clôture à 17:00 pour **−1,9748 EUR**.

Il y a ainsi **58 entrées communes, trois propres à la base, deux propres au
stress** : 61 contre 60, et non un simple retrait d'un trade. Les 13 divergences
de motifs du trimestre figurent dans `DECISION_DIVERGENCES_Q1.csv`.

La différence totale stress moins base se réconcilie exactement :

| Élément comptable | Contribution à l'écart stress − base |
| --- | ---: |
| Différence nette sur les 58 entrées communes | −105,587979 EUR |
| Trois trades propres à la base, total −366,975866 EUR, absents du stress | +366,975866 EUR |
| Deux trades propres au stress, total −124,639168 EUR | −124,639168 EUR |
| **Écart total** | **+136,748720 EUR** |

Ce sont des résultats observés dans deux parcours déjà simulés, avec leurs
règles préannoncées. Les refus du stress ne sont pas qualifiés de gains possibles.

## La cible du 27 janvier : effet distinct et vérifié

Le short commun du 27 janvier vise 1,20913 en base et 1,20896 en stress.
Le moteur exige un dépassement d'un tick : `ask_low <= cible − 0,00001`.
La lecture directe de trois minutes du cache validé donne :

| Minute de cotation | Ask low observé | TP base admissible | TP stress admissible |
| --- | ---: | --- | --- |
| 14:33 | 1,20905 | oui | non |
| 14:34 | 1,20903 | oui | non |
| 14:35 | 1,20866 | oui | oui |

Cela correspond aux clôtures comptabilisées en fin de minute à 14:34 et 14:36.
Les nets du journal sont **+368,9528 EUR base** et **+370,2520 EUR stress**.
Le stress vise ici un prix plus favorable après frais et dimensionne une taille
différente : cette ligne n'est pas une soustraction de frais à une sortie fixe.
Aucune décision d'entrée/refus ne diverge à cause de ces deux minutes : la
première divergence de motifs reste celle du 11 mars. Les valeurs de quotes
et les seuils sont sauvegardés dans `JAN27_TARGET_QUOTE_EVIDENCE.csv`.

## M1 Q1 : pourquoi 117 trades deviennent 115

Variante exacte : `EXTENDED_HOLD60_8SMALL_M1`, budget prévu 62,50 EUR par
position. Le premier changement de signe porte sur l'entrée du
**18 janvier à 13:34**, close à 14:34 : **+0,8621 EUR base** contre
**−1,0359 EUR stress**. Le trade précédent, entré à 11:01 et clos à 12:01,
avait déjà perdu −3,3151 EUR en base et −4,9727 EUR en stress.

La base remet donc le compteur à zéro ; le stress atteint deux pertes et
se met en pause jusqu'au **19 janvier à 14:34**. Première divergence de motif
dès le 18 à 14:45 : la base refuse parce que le prix n'est plus au-delà du
range, le stress refuse pour pause. Aucun des deux n'entre à cet instant.

Les deux seules entrées qui diffèrent sont ensuite celles du 19 janvier :

| Entrée UTC | Base | Stress |
| --- | --- | --- |
| 09:16 | Stop à 09:43, −61,7237 EUR | Refus pour pause |
| 09:48 | Sortie horaire à 10:48, +27,0090 EUR | Refus pour pause |

Leur total de base est **−34,714712 EUR**. Les **115 autres entrées sont
communes** ; aucune de leurs heures ou catégories de sortie ne change.
Sept décisions ont des motifs différents, tous expliqués par la pause stress.

| Élément comptable | Contribution à l'écart stress − base |
| --- | ---: |
| Différence sur les 115 entrées communes | −139,852872 EUR |
| Absence du lot de deux trades propres à la base | +34,714712 EUR |
| **Écart total** | **−105,138160 EUR** |

Le net passe ainsi de **+138,528317** à **+33,390157 EUR**, en accord avec
les résultats enregistrés. Les frais pèsent sur les entrées communes ; l'effet
de pause compense une partie de cet écart sur cette période précise.

## Portée et preuves

Les 36 décompositions comptables et effectifs concordent avec `RESULTS.json`.
Pour les deux trajectoires détaillées, chaque refus divergent invoquant une
pause correspond à une pause encore active reconstruite depuis les clôtures.
Cette vérification explique les divergences étudiées ; elle ne certifie pas
tout le modèle d'exécution ni les règles FTMO.

Les journaux persistés ne contiennent pas de liste détaillée de fills. Cet
audit utilise les prix/cibles/heures de `TRADES.csv`, les décisions, le code
gelé et les trois minutes de quotes explicitement relevées. Aucun fill manquant
n'a été inventé, aucune trajectoire financière n'a été relancée.

Pièces : `TRADE_COMPARISON_Q1.csv`, `LOSS_PAUSE_STATE_Q1.csv`,
`DECISION_DIVERGENCES_Q1.csv`, `PERIOD_COST_COMPARISON.csv`,
`JAN27_TARGET_QUOTE_EVIDENCE.csv`, `AUDIT_SUMMARY.json` et empreintes des sources.
Les scénarios de coûts et les périodes qui se chevauchent ne sont pas des
échantillons indépendants. Aucun résultat, fichier gelé ou paramètre n'a été modifié.
