# Revue du code avant historique

**Verdict : aucun défaut matériel bloquant trouvé après correction du corps
MSS non directionnel.** Revue en lecture seule de `strategy.py`, `engine.py`
et `PLAN_BEFORE_RESULTS.json`, sans charger le cache ni lancer de simulation.
Ce verdict porte sur la conformité examinée, pas sur la rentabilité.

Le plan résout les choix auparavant ouverts : un seul setup en attente,
conservation du premier et nouveaux balayages ignorés, six barres pour le MSS,
puis six nouvelles barres pour le retour. Une barre d'expiration/invalidation
n'est pas réutilisée pour créer un nouveau setup. Le premier retour consomme
l'occasion, même si les règles du compte ou la quote refusent ensuite l'entrée.

Points vérifiés dans le code :

- Pivot strict déjà confirmé à l'heure du balayage, identité gelée et recherche
  bornée aux centres des douze précédentes casesM5. Aucun pivot futur admis.
- MSS sur barre ultérieure, premier franchissement seulement, ATR de la barre
  précédente et FVG de trois barres consécutives complètes.
- Stop exécutable figé ; toucher pendant l'attente traité avant MSS/retour.
  Deux côtés balayés dans une mêmeM5 rejetés comme ambigus.
- Bornes FVG figées au MSS ; retour sur nouvelle clôture, invalidation du FVG
  avant entrée et annulation de séance sur trou de signal.
- Order block descriptif, dernière bougie strictement opposée des cinqM5
  précédentes, zone complète high/lowmid et disponibilité au MSS.
- Entrée sur première quote suivante encore dans le FVG, côtés bid/ask et
  cible exécutable opposée du range, minimum2R net prévu après les coûts.
- Clone du simulateur dans un dictionnaire global privé : seule la fonction
  `order` est remplacée ; le moteur initial n'est pas modifié globalement.

Une condition limite a été signalée : si ATR était zéro, le seul test
`corps < ATR` admettait un corps nul. Le code exige maintenant explicitement
un corps directionnel strictement positif et consigne
`DISPLACEMENT_NON_DIRECTIONAL`. Le parent rapporte neuf tests synthétiques
réussis après cette correction, dont le cas doji/ATR zéro, la symétrie vendeuse
et l'expiration du retour. Cette revue n'a pas relancé ces tests.

Les limites restent explicites : le niveau opposé n'est pas une preuve de
liquidité intacte ; l'exécution n'est pas une limite au milieu du FVG ; les
OHLC ne fournissent pas l'ordre exact des ticks ; le risque adaptatif reste
désactivé faute de calibration indépendante. Les vingt-huit tests du premier
document restent des propositions plus larges, pas vingt-huit tests exécutés.
