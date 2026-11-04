# Journal de recherche EURUSD

Mis à jour le4novembre2026. Le code, les rapports et les graphiques sont
synchronisés sur GitHub après chaque étape cohérente terminée. Le cache de
prix et les archives ZIP restent hors du dépôt ; leurs identités sont conservées.
Les copies locales de sources tierces sont remplacées dans le dépôt par leurs
URLs et empreintes, sans prétendre qu'elles sont redistribuées.

## Dernière étape : lecture graphique et poursuite après2R

Étape suivante autorisée : [ICT/SMC](research/ict_smc_20261104/README.md).
Plan et code préparés avant le backtest : sweep→MSS→retourFVG, cible bord opposé
du range, minimum2R prévu,17 tests réussis. Les statistiques antérieures sont
séparées de toute prévision validée ; aucune hausse automatique des mises.
Le plan/code ont été publiés avant calcul au commit `7f7a4f6`.
Résultat ICT : un seul trade le6janvier, +313,51 EUR/+285,62 renforcé,
surQ1 comme sur l'année.735 sweeps→22MSS/FVG→5retours→1entrée.
Aucun paramètre modifié après résultats ; lot non concluant, non promu.

- Comparaison complète sur le4janvier–31mars2021, données de développement.
- Même signal V03 : cible2R, net+839,28 EUR en base/+719,24 renforcé, contre
  +642,37/+504,22 à3R ; mêmes61 entrées et30 pertes.
- Quatre sorties réelles auTP2 : un même trade atteint ensuite3R et4R avant
  16h Londres ; aucun5R. Les trois autres expirent sans3R ; aucun inconnu.
- H1+ADX puis veto de niveaux réduisent le nombre de trades et de pertes,
  sans améliorer le taux de pertes ni le net total face au témoin2R.
- Configuration2R disponible en option : `simple_forex/protocol_v04.json`.
  V03 reste la référence active ; aucun indicateur expérimental n'est adopté.
- Graphiques des quatreTP2 et d'une perte, avec niveaux connus à l'entrée et
  ADX M5. Les continuations sont hypothétiques, pas un portefeuille additionnel.
- Vérification :17 tests synthétiques réussis,8 portefeuilles et36 issues
  de continuation contrôlés ; le témoin3R reproduit les anciens journaux.
- Première synchronisation GitHub publiée sur `main` : commit `e0d9331`.
  Le graphique27janvier est également intégré directement au README.

[Rapport](research/chart_context_20261104/RAPPORT.md) ·
[Galerie](research/chart_context_20261104/charts/INDEX.html) ·
[Plan avant résultats](research/chart_context_20261104/PLAN_BEFORE_RESULTS.json)

## Étapes précédentes conservées

- [Fréquence et levier](research/frequency_leverage_20261104/RAPPORT.md) :
  jusqu'à4 entrées/jour, mais amélioration du net non robuste aux coûts ;
  les plafonds30/100 ne modifient pas les tailles à risque identique.
- [Indicateurs et niveaux](research/indicator_study_20261104/SYNTHESE.md) :
  formules vérifiées ; filtre EMA20/50 M5 défavorable, non adopté.
- [Réarmement et cible3R](reports/RAPPORT_FREQUENCE_ET_R_V03.md) :
  référence V03 et échecs précédents conservés.

## Limites actuelles

2021 a déjà servi au développement, pas à une validation indépendante. Le
résultat annuel reste inconnu à cause du trou actif d'avril. Les règles FTMO
actuelles et les spécifications MT5 ne sont pas certifiées. Aucun accès
courtier, ordre réel, garantie80 % ou passage de challenge n'est activé.
