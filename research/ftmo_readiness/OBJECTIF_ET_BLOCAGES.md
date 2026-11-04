# Objectif FTMO et diagnostic obligatoire à chaque backtest

Statut au 3 novembre 2026 : recherche sur une seule stratégie EUR/USD. Après réception du brief, l'utilisateur a confirmé directement **FTMO 2-Step, 100 000 € en euros, moins d'un mois pour Challenge et Vérification réunis, Forex uniquement, objectif sans garantie**. Les règles contractuelles exactes restent à vérifier dans les conditions officielles. La convention de calcul proposée est strictement moins de 30 jours calendaires pour les deux phases, distincte des délais administratifs.

## Ce que le prochain compte rendu devra expliquer

Trois niveaux sont distincts :

1. **Occasion non exécutée** : quelles données et quels critères étaient connus, quelle règle a refusé ou annulé le setup, quels autres critères n'ont pas été évalués. Ne pas transformer rétrospectivement une occasion refusée en « gain manqué ».
2. **Trade exécuté** : pourquoi l'entrée était admissible, sortie et résultat net, excursions observables, frais, qualité des données, éventuel écart d'exécution. Une perte conforme au plan ne prouve pas une erreur de code ou la nécessité d'un filtre supplémentaire.
3. **Challenge non validé** : cible non atteinte, rythme insuffisant, règle de jours, equity/perte journalière ou totale, condition spécifique du produit, ou données insuffisantes. Un résultat annuel positif n'est pas une validation de challenge.

Les motifs simultanés restent séparés et peuvent se chevaucher. Les journées ou minutes absentes ne deviennent pas une preuve d'absence de signal. Chaque backtest doit produire les journaux et une analyse des principaux freins, plutôt qu'une nouvelle copie du seul PnL.

## Écart avec moins d'un mois

Le flux observé de la stratégie A compte trois entrées en 2021. Le post-traitement de la trajectoire annuelle donne 336 fenêtres de 30 jours calendaires entièrement contenues dans 2021, qui se chevauchent :

- au maximum deux entrées dans une fenêtre ;
- meilleur net observé dans une fenêtre : +238,54 €, soit environ +0,239 % des 100 000 € simulés ;
- aucun nouveau challenge remis à zéro n'est simulé par ce calcul ; aucun taux de réussite FTMO n'en est déduit.

Les jours de calendrier restent inclus. Ces observations ne certifient pas la complétude du flux et ne remplacent pas la simulation de contraintes contractuelles.

**Illustration arithmétique conditionnelle, pas une certification des règles FTMO actuelles** : si deux phases demandaient respectivement 10 % puis 5 %, avec 100 000 € par phase, un risque fixe de 250 € et chaque gain effectivement égal à +2R, il faudrait au moins 20 puis 10 gains sans perte. Avec une entrée par jour de semaine, ces 30 journées d'entrée dépassent le maximum de 22 jours lundi–vendredi d'une fenêtre de 30 jours calendaires. Cette borne simplifiée ignore les variations FX et les arrondis ; elle révèle une incompatibilité du rythme/risk budget supposé avec ce délai, pas une stratégie pour augmenter le risque.

Le produit exact peut changer ces contraintes. Les gains actuels ne valent d'ailleurs pas +2R : ils proviennent des sorties horaires. Aucune hausse de risque n'est activée pour masquer le problème de fréquence et l'absence de validation indépendante.

## Règles officielles : vérification encore bloquée

Les accès à `https://ftmo.com/en/trading-objectives/` et à son équivalent `www.ftmo.com` ont renvoyé un refus 403 du proxy. Les deux domaines ont été ajoutés au brouillon réseau en conservant les huit domaines de recherche et les préréglages déjà présents. Le brouillon est enregistré ; les réglages doivent être enregistrés/revus et l'environnement publié pour activation. Aucune règle actuelle n'est présentée comme vérifiée.

Le fichier `ACCOUNT_PROFILE_TO_COMPLETE.json` enregistre désormais le programme 2-Step, le capital 100 000 €, la devise EUR et les deux phases confirmés par l'utilisateur. Il garde les règles inconnues à null : type Standard/Swing, seuils, définition de l'equity et de la perte journalière, fuseau de reset, jours qualifiants, éventuelles règles de concentration et restrictions applicables. Les règles peuvent différer selon le produit et la phase.

## Exigences de l'évaluateur prop firm

- Suivre balance et equity avec positions ouvertes, spread et coûts applicables ; le drawdown sur clôtures ne suffit pas.
- Ne pas confondre l'enveloppe hypothétique de liquidation du moteur, qui incorpore des coûts de sortie, avec la définition contractuelle de l'equity FTMO.
- Respecter le fuseau IANA et les changements d'heure du reset exact, une fois vérifié.
- Modéliser la séquence des phases et leurs réinitialisations, sans compter deux fois le profit d'une première phase.
- Qualifier un objectif seulement avec les conditions contractuelles satisfaites, positions closes si requis et aucune violation préalable.
- Garder INDETERMINATE si les extrêmes M1 permettent plusieurs chronologies de violation/objectif ou si des données actives manquent.
- Évaluer les fenêtres de délai avec chauffe passée, compte initial neuf, état clair des pauses et jours qualifiants, et toutes les journées calendaires.
- Distinguer durée de trading et délais réels de contrôle/activation, non simulables ici.

Les états attendus incluent PASSED, TARGET_NOT_REACHED, FAILED_DAILY_LOSS, FAILED_MAX_LOSS, MIN_DAYS_NOT_MET et INDETERMINATE. Aucun de ces statuts n'est actuellement attribué à une tentative FTMO réelle.

## Travail parallèle

Un agent a audité les occasions non exécutées et livré l'observateur causal intégré au lanceur. Un autre a analysé les exigences de l'évaluateur et les limites d'accès aux règles FTMO. Une seule stratégie reste étudiée ; les agents ne recherchent pas des variantes concurrentes. Le résumé complet reçu apporte le cadre historique, complété par la confirmation directe du profil FTMO ; les règles officielles restent nécessaires avant toute conclusion de conformité.
