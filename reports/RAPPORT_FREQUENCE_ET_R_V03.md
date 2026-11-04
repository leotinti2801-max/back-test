# Davantage d'entrées, 3R/4R et objectif de 80 % — résultats du 4 novembre 2026

## Résultat principal

Le code permet maintenant **quatre entrées réelles par jour**, avec un
réarmement après une nouvelle clôture intérieure du range. Le candidat de
recherche V03 utilise un objectif prévu à **3R**, sans indicateur, dans un
signal de 32 lignes. Le risque prévu a été abaissé de 250 € à **125 € par trade**
pour conserver au plus 500 € prévus sur la journée.

Le taux demandé de **80 % n'est pas atteint**. V03 donne 54,8 % sur les 45 jours
et 50,8 % sur le préfixe annuel résolu. Le plafond autorise quatre entrées, mais
les données n'en exécutent jamais plus de deux par jour dans cette configuration.
La réussite FTMO et la rentabilité hors développement ne sont pas validées.

## Ce qui a été fixé avant les calculs

Le premier lot proposait cassure puis retest confirmé sur une M5 ultérieure,
stop derrière la M5 de retest, réarmement après clôture intérieure, 09–14:30 Londres,
125 € par trade et quatre entrées réelles. Trois objectifs avaient été gelés :
2R témoin, 3R principal, 4R comparatif. Cette nouvelle entrée s'est montrée
défavorable sur la fenêtre courte ; les résultats n'ont pas été supprimés.

Un second lot, déclaré après ce constat, répond plus directement à la demande :
augmenter seulement le TP de V01 à 3R/4R, puis examiner une variante réarmée sans
retest à 3R. Ce lot est une exploration supplémentaire sur un historique déjà
consulté. Il n'est pas une validation indépendante ni une sélection statistique.
Il était limité à ces trois diagnostics ; aucune autre grille n'a été testée.

V03 est ce dernier candidat réarmé pour la recherche suivante. Il a été priorisé
après observation des résultats de développement ; sa performance ne doit donc
pas être présentée comme une découverte hors échantillon. Les sélecteurs
automatiques n'ont désigné aucun gagnant et le réel reste désactivé.

## Tous les résultats courts, après frais

Fenêtre : 04/01/2021–18/02/2021, fin exclue, 45 jours. Les lignes partagent des
prix et des règles : ce ne sont pas des échantillons indépendants.

| Version | Risque prévu/trade | Trades | Gains nets | Net observé |
| --- | ---: | ---: | ---: | ---: |
| V01 initiale, 2R | 250 € | 27 | 48,1 % | +670,63 € |
| V01, TP porté à 3R uniquement | 250 € | 27 | 48,1 % | +277,71 € |
| V01, TP porté à 4R uniquement | 250 € | 27 | 48,1 % | +526,90 € |
| Retest V02, 2R | 125 € | 14 | 21,4 % | −624,08 € |
| Retest V02, 3R | 125 € | 14 | 21,4 % | −251,65 € |
| Retest V02, 4R | 125 € | 15 | 6,7 % | −1 647,39 € |
| Réarmement simple V03, 3R | 125 € | 31 | **54,8 %** | **+765,35 €** |

L'augmentation du TP seule ne rend pas V01 meilleure sur cette période. V02
réduit le nombre d'entrées et se montre déficitaire : elle ne répond pas au
résultat recherché et n'est pas retenue comme candidate active.

V03 modifie le réarmement, les horaires et le budget par position ; son écart
avec V01 ne s'attribue donc pas à la seule cible. Le risque divisé par deux
contribue à la réduction du drawdown : la comparaison n'est pas celle de deux
systèmes avec un risque par trade identique.

## V03 : résultats connus, coûts et risques

| Mesure | 45 jours | Préfixe annuel avant le trou |
| --- | ---: | ---: |
| Trades clos | 31 | 61 |
| Gains / pertes | 17 / 14 | 31 / 30 |
| Taux de gains nets | 54,8 % | 50,8 % |
| Net des clôtures connues | +765,35 € | +642,37 € |
| Avec commission ×1,5 et glissement ×2 | +692,72 € | +504,22 € |
| Maximum exécuté le même jour | 2 | 2 |
| Drawdown sur clôtures | 420,05 € | 420,05 € |

Le préfixe annuel s'arrête le **1er avril 2021 à 11:40 UTC (13:40 Paris)**, pendant
une position. Le résultat annuel est null. Les 31 trades courts font partie
des 61 : ils ne s'additionnent pas. Après les 45 jours, les 30 autres clôtures
connues totalisent environ −122,98 € ; cela limite encore la conclusion de stabilité.

Les autres prototypes s'arrêtent eux aussi sur des expositions non résolues.
V02 retest rencontre un trou le 14 juin ; les versions V01 à 3R/4R et V03 le
1er avril. Leurs préfixes annuels n'ont pas tous la même durée et ne sont pas
comparés comme des performances annuelles complètes.

## Pourquoi quatre entrées autorisées n'en donnent pas quatre exécutées

La simulation V03 refuse **58 signaux sur les 45 jours** parce qu'une position
est encore ouverte et 20 à cause de la pause après deux pertes. Une autre
entrée est refusée car le prix est revenu dans le range à la quote d'ouverture.
Le plafond de quatre n'est pas le frein actif dans ces journées.

Sur le préfixe annuel : 105 refus pour position ouverte, 33 pour la pause,
2 pour prix revenu dans le range et 2 pour premier tick trop tardif. Les motifs
peuvent se chevaucher et ne doivent pas être ajoutés à des trades supposés gagnants.

Chaque nouvelle cassure requiert une clôture M5 intérieure réellement observée.
Plusieurs clôtures restant dehors ne déclenchent pas des entrées répétées. Les
refus et signaux bloqués ne sont pas comptés dans les quatre entrées exécutées.
La règle garde une seule position ouverte, sans empilement d'expositions EUR/USD.

## Pourquoi 3R prévu ne signifie pas une moyenne de gains de 3R

V03 a seulement un TP atteint dans le préfixe connu de 61 clôtures ; 48 sorties
sont horaires et 12 sont des stops. Sur les 45 jours : un TP, 23 sorties horaires
et 7 stops. Les gagnants D45 valent en moyenne environ 0,90R cash et ceux du
préfixe environ 0,71R. Le taux de gains compte toutes les positions closes nettes
positives, pas seulement les TP et pas des fractions d'une même position.

Les pertes ont pour mécanismes observés la liquidation au stop après une cassure
qui s'inverse, ou un prix/coût net défavorable à l'échéance. Aucune cause macro
n'a été attribuée sans calendrier historique. Les anciens parcours s'arrêtaient
à leurs TP : leurs seules excursions ne permettent pas d'inventer le résultat
qu'aurait eu un objectif plus éloigné.

## Contrôles réalisés

**47 tests exécutés, 47 réussis, zéro échec et zéro ignoré.** Ils couvrent
notamment causalité, retest sur une barre ultérieure, réarmement, stop côté
bid/ask, refus ne consommant pas le quota d'entrées, cinquième entrée refusée,
absence de chevauchement, pause et données incomplètes.

Le moteur commun accepte désormais une source de signal explicite. Une
régression financière V01 a reproduit son résumé D45 et son CSV de trades à
l'octet. Les anciennes sources sont conservées dans `research/source_snapshots/`.
Le rejeu dédié V03 reproduit exactement les CSV du candidat identique du second lot.

Un audit indépendant de 960 lignes de trades clos, incluant fenêtres, variantes
et rejeux corrélés, recalcule les flux monétaires directement depuis les quotes :
écart maximal **0 €**. Il contrôle aussi tailles, budgets prévus, maximum d'entrées,
soldes, absence de chevauchement et pause de 24 h. Ce ne sont pas 960 observations
indépendantes et ce contrôle ne certifie pas FTMO.

## Décision

Conserver V03 comme **candidat exploratoire non qualifié**, archiver l'échec de
V02 et les comparaisons de TP. Ne pas augmenter le risque ou multiplier encore
les seuils jusqu'à afficher 80 % sur 2021. Les règles officielles FTMO restent
non vérifiées et le trou M1 identifié reste à qualifier. Une période bid/ask
encore inutilisée est nécessaire pour tester la stabilité de ce résultat.

Pièces : `simple_london_retest_v02_01/`, `simple_london_frequency_target_01/`,
`simple_rearmed_v03_01/`, leurs gels et manifestes, et
`PERFORMANCE_REQUEST_CASH_AUDIT.json`. L'actif V03 est défini par
`simple_forex/protocol_v03.json` ; aucun ordre réel n'est autorisé ou envoyé.
