# EUR/USD — dossier d'analyse d'une seule stratégie

Date : 3 novembre 2026. Statut : recherche, rentabilité non établie.

## Décision de travail

La recherche se concentre désormais sur **EUR/USD, structure de tendance H4, cassure M30, entrée au premier repli dans la zone d'origine et cible fixe prévue à 2R**. La référence technique est `A_STRUCTURE_FIXED_2R`.

Ce choix privilégie la continuité avec la méthode initiale, une logique explicable et un nombre limité de paramètres. Il ne constitue pas une sélection validée de la variante ayant le meilleur résultat annuel. Les variantes B à E restent archivées avec leurs échecs, mais ne font plus partie de la recherche active. Se concentrer maintenant sur une stratégie n'efface pas les cinq hypothèses déjà essayées ni la consultation de 2021.

La charte machine est `STRATEGY_CHARTER.json`. Les paramètres historiques et les sources exécutées restent à leurs empreintes gelées. Aucun nouveau seuil n'a été choisi à partir des trois trades observés et aucun nouveau calcul financier n'a été lancé pour ce dossier.

## 1. Comprendre l'instrument et le mécanisme recherché

EUR/USD exprime une quantité de dollars pour un euro. Un achat est une exposition longue à l'euro et courte au dollar ; une vente est l'inverse. Un pip vaut 0,0001 sur cette paire ; le tick de prix retenu dans notre moteur est 0,00001. Les unités et le côté bid/ask doivent rester cohérents entre signal, ordre, stop et résultat en euros.

Le contexte économique utile comprend les anticipations relatives de politique monétaire, les surprises d'inflation et d'emploi, les flux de capitaux et l'appétit pour le risque. Le niveau d'un taux directeur, isolément, ne donne pas mécaniquement le sens du prochain mouvement : les prix reflètent aussi les anticipations et leurs changements. Ce cadre général ne fournit pas, à lui seul, un signal intraday.

Notre hypothèse opérationnelle est plus étroite : **après une cassure dans le sens d'une structure H4 connue, un repli observable pourrait offrir un prix d'entrée dont l'espérance nette est favorable**. Cette persistance conditionnelle reste à démontrer. Une zone OHLC dite POI n'est pas une preuve d'ordres institutionnels, d'accumulation ou de « chasse aux stops » : le cache fourni ne contient pas ces informations.

L'analyse doit relier une hypothèse économique à des faits mesurables : structure connue, cassure réellement close, repli, conditions d'exécution et résultats après frais. Aucune étiquette graphique ne remplace cette mesure.

## 2. Ce que signifie « un bon trade » avant son résultat

Avant l'entrée, le résultat futur est inconnu. Une règle utile cherche une espérance conditionnelle positive sous contrainte de risque ; elle ne peut reconnaître à coup sûr tous les futurs gagnants. Des pertes restent compatibles avec une stratégie rentable, et une série de gains reste compatible avec l'absence d'avantage.

Si les gains et pertes sont déjà nets de coûts :

`espérance en R = taux de gains × gain moyen en R − taux de pertes × perte moyenne absolue en R`

Il ne faut pas retrancher ensuite une seconde fois les frais déjà comptabilisés. Une cible prévue à 2R et une perte prévue à 1R donnent un seuil théorique de 33,3 % uniquement dans le cas simplifié où ces deux résultats sont effectivement réalisés. Des sorties horaires, gaps, conversions de devise et exécutions différentes changent la distribution.

Dans notre moteur, le 2R est un rapport prévisionnel en devise de cotation, frais prévus inclus. Le résultat effectivement converti en euros et rapporté au risque prévu peut différer de ce rapport, même à la cible.

## 3. Lecture financière des trois trades existants

Les lignes suivantes proviennent du dernier journal annuel, scénario de coûts de base. Les horaires de marché sont en UTC.

| Entrée | Sens | Durée | Sortie | Résultat net | R réellement encaissé |
| --- | --- | ---: | --- | ---: | ---: |
| 05/01/2021 09:56 | Achat | 120 min | Échéance | +238,54 € | +0,959R |
| 16/07/2021 09:13 | Vente | 31 min | Stop avec ouverture défavorable | −250,02 € | −1,002R |
| 20/07/2021 15:27 | Vente | 33 min | Échéance de 16 h | +212,71 € | +0,854R |

**Aucun TP à 2R n'a été exécuté. Les deux gains proviennent de sorties horaires.** Leur moyenne est de 0,906R ; la perte observée est de 1,002R. Si ces seuls gains/pertes moyens étaient stables, le seuil de réussite correspondant serait environ **52,5 %**, et non 33,3 %. Ce calcul illustre le rôle des sorties : trois observations ne permettent pas d'estimer ces moyennes futures.

Le 20 juillet, l'entrée laisse seulement 33 minutes avant la sortie obligatoire. La cible se trouve à environ 32,4 pips du prix modélisé. Le 5 janvier, la cible est à environ 31,3 pips avec 120 minutes de détention. Une même cible en R peut donc représenter des opportunités temporelles très différentes.

Les excursions favorables connues avant la minute de sortie atteignent environ 1,45R-prix et 1,49R-prix pour les deux gains. Ce sont des enveloppes M1 du côté liquidable, pas des résultats cash garantis ni des mesures tick exactes. Elles ne justifient pas de choisir après coup un TP à 1,4R, 1,5R ou un stop suiveur sur ces seuls cas.

Le libellé `SL_GAP` signifie que la quote d'ouverture modélisée est déjà au-delà du stop. Il ne prouve pas une minute absente. Le budget de risque prévu n'est pas un plafond de perte garanti à l'euro près.

Les commissions totalisent 34,00 € et le glissement modélisé 13,60 €, déjà inclus dans les 201,22 € nets. Le spread est déjà porté par les prix bid/ask ; ces coûts ne doivent pas être déduits une seconde fois.

Les calculs reproductibles et les cas détaillés figurent dans `existing_trade_analysis/FOCUSED_ANALYSIS.json` et `THREE_TRADE_CASES.csv`.

## 4. Coûts, liquidité et qualité des données

Un achat s'exécute à l'ask et se liquide au bid ; une vente fait l'inverse. Une stratégie qui gagne sur un prix mid peut devenir déficitaire une fois appliqués spread, commissions et glissement. Les distances de stop et de cible doivent être comparées aux frictions dans la même unité.

Les frais supportés sur un flux historique ne suffisent pas à connaître ceux d'un compte réel : il faut le type d'instrument exact (spot, CFD, future), les conditions du courtier, les conventions de lot, les commissions, la latence et, si la détention le nécessite, le financement. Notre résultat reste celui du modèle livré, pas un relevé d'exécution réel.

Les créneaux Londres/New York et leurs recouvrements doivent être étudiés avec `Europe/London` et `America/New_York`, puis affichés en Europe/Paris. Les dates de changement d'heure ne coïncident pas toujours entre États-Unis et Europe. La règle actuelle reste toutefois 08–16 h UTC : aucun nouveau filtre de session n'est activé dans ce dossier.

Le marché des changes nécessite de qualifier le flux réellement observé. Une minute absente peut provenir d'une fermeture, de l'absence de cotation ou d'un défaut d'enregistrement. Le fournisseur et son calendrier doivent permettre de distinguer ces cas. Ajouter un calendrier n'invente pas les prix d'une minute absente.

Avec des pivots à cinq H4 complètes consécutives, il faut une fenêtre de vingt heures dont la présence requise des M1 est satisfaite. Une lacune peut empêcher la confirmation de nombreux pivots. Cela peut expliquer une partie de la rareté du biais sans démontrer qu'un assouplissement serait rentable.

Pour notre cas, le premier investissement de recherche est donc un historique bid/ask mieux qualifié : horloge, couverture, événements de qualité et sessions. La reconstruction de signaux sur un flux lacunaire doit rester explicitement partielle.

## 5. Annonces macroéconomiques : un chantier précis

Les décisions de la Fed/BCE, les publications américaines d'emploi et d'inflation font partie des événements à inventorier pour EUR/USD. Un modèle utilisable doit distinguer l'heure programmée, l'heure de diffusion effective, la valeur alors disponible et les éventuelles révisions. L'information révisée ultérieurement ne doit pas devenir un prédicteur historique.

Un filtre d'annonces ne doit pas être ajouté parce qu'un trade perdant a précédé un événement. Il faut d'abord obtenir un calendrier historique daté, définir avant le calcul les événements concernés et la durée de suspension, puis mesurer son effet sur la même stratégie. Aucun calendrier n'a été inventé ici et aucun filtre macro supplémentaire n'est actuellement actif.

Je ne retiens pas un biais euro/dollar actuel à partir de chiffres non consultés. Les recherches à la BRI, à la Fed, à la BCE et au BLS servent à documenter ce chantier ; leur consultation reste soumise à l'activation réseau décrite plus bas.

## 6. Une règle unique et des degrés de liberté maîtrisés

Le cadre technique conservé est celui de A, avec :

- contexte H4 structurel confirmé et gestion explicite des états neutres/incomplets ;
- première clôture M30 au-delà d'un pivot connu avant son ouverture, corps ≥1 ATR connu à l'ouverture ;
- zone de la dernière bougie opposée dans les six M30 précédentes requises ;
- premier retour M1 observable, close dans la zone, exécution sur la prochaine ouverture admissible ;
- stop au-delà de la POI, marge de 0,10 ATR ; cible prévue à 2R calculable à l'entrée ;
- risque prévu maximal de 250 € sur le capital simulé de 100 000 €, pas de quantité de 2 000 €, levier maximal 10 ;
- une entrée au maximum par jour UTC et pause de 24 h après deux pertes nettes ;
- entrées 08–16 h UTC, exclusion 15:30–17:00 Europe/Paris, sortie après 120 minutes au plus ou à 16 h UTC.

Ces paramètres sont des choix de recherche hérités, pas des constantes financières universelles. La priorité n'est pas de leur attribuer une autorité académique. Elle est de vérifier l'hypothèse avec ces règles explicites, puis de décider s'il faut la conserver ou la rejeter.

Les questions encore ouvertes sont la représentativité du biais H4, la compatibilité distance-objectif/temps restant, les coûts par session et le comportement selon les régimes de marché. Elles ne sont pas déjà transformées en nouveaux filtres.

## 7. Ce que les sources effectivement consultées apportent

### M1 — Rob Carver et contributeurs, guide de backtesting de pysystemtrade

[Guide source](https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md), sections coûts, tests de courbes, optimisation/périodes et cache avancé. Copie et empreinte enregistrées dans `sources/`.

La documentation distingue les coûts calculés par transaction d'une approximation de coût standardisé ; elle souligne l'intérêt des flux monétaires réels pour des positions rares. Elle traite aussi de rotation, de coûts de détention et d'estimation temporelle. Elle avertit sur les hypothèses des tests statistiques et sur le surajustement implicite lors de modifications répétées.

Application à notre travail : conserver le résultat monétaire après frais par trade, ne pas optimiser la distribution sur trois observations et séparer strictement estimation passée et vérification ultérieure. Ce cadre est celui d'un logiciel de trading systématique, notamment sur futures : il n'est pas une preuve de rentabilité de notre stratégie spot/CFD intraday.

### M2 — Kevin Sheppard et contributeurs, documentation des comparaisons multiples de arch

[Référence du module](https://github.com/bashtage/arch/blob/main/doc/source/multiple-comparison/multiple-comparison-reference.rst), [bibliographie du module](https://github.com/bashtage/arch/blob/main/doc/source/multiple-comparison/background.rst).

La documentation présente SPA/Reality Check, StepM et Model Confidence Set et la prise en compte de la dépendance entre modèles. Sa bibliographie référence notamment White (2000), Hansen (2005), Romano/Wolf (2005) et Hansen/Lunde/Nason (2011). Les articles originaux n'ont pas été lus ici ; la lecture porte sur la documentation et sa bibliographie.

Application : conserver l'historique des variantes essayées et ne pas confondre le meilleur résultat parmi plusieurs essais avec une découverte validée. Aucun de ces tests n'a été exécuté pour nos trois trades ; aucune p-value n'est revendiquée.

### Sources financières primaires encore à consulter

Le registre `SOURCE_REGISTER.json` distingue explicitement ces références de celles déjà lues. Les recherches prévues couvrent : BRI (structure du Forex et travaux de momentum), Fed/BCE/BLS (annonces et politique monétaire), AQR (travaux de momentum et limites de transfert entre horizons), NBER (recherche académique), David Bailey (surajustement), Global Foreign Exchange Committee (pratiques d'exécution).

L'existence de travaux sur le momentum de devises ou de futures à d'autres horizons ne démontrerait pas l'efficacité d'un repli H4/M30. Il faudra vérifier l'univers, les dates, les horizons, les coûts et les résultats effectivement décrits avant d'en tirer une conséquence.

L'accès BRI testé via le proxy a été refusé. Le brouillon réseau inclut désormais les huit domaines nécessaires, en conservant les préréglages existants. Son enregistrement est confirmé ; son activation n'est pas confirmée. L'outil indique de revoir/enregistrer les réglages de l'environnement puis de publier l'environnement. Ces publications primaires ne sont pas présentées comme consultées.

## 8. Protocole de recherche pour cette seule stratégie

1. Obtenir un historique bid/ask qualifié et identifier les périodes encore inutilisées. Toute l'année 2021 reste du développement déjà consulté.
2. Refaire l'audit des bougies, de la disponibilité des pivots et des indicateurs sans résultat financier pour réparer les prérequis de données.
3. Geler les règles, les coûts, le calendrier, la séparation chronologique et les conditions de rejet avant d'observer le nouvel échantillon.
4. Mesurer l'espérance nette, la distribution de R, les types de sorties, le risque intra-position, les drawdowns, la concentration temporelle et les frictions. Un nombre de trades plus élevé n'est pas un critère suffisant.
5. Vérifier la sensibilité aux coûts et à une exécution moins favorable, sur le même signal. Conserver les échecs et états inconnus.
6. Quand l'échantillon le permet, estimer l'incertitude avec une méthode respectant la dépendance temporelle, et tenir compte des essais déjà effectués. Cent trades est un plancher exploratoire hérité, pas une garantie de puissance statistique.
7. Étudier une seule modification justifiée à la fois, versionnée avant son test. Un nouveau filtre réinitialise le besoin de validation ; il ne transforme pas le même 2021 en données indépendantes.
8. Ne qualifier le passage en simulation de suivi/paper trading qu'après des résultats indépendants suffisamment stables ; les frais, les écarts de remplissage et les conditions d'arrêt doivent ensuite être surveillés.

Le benchmark comptable sans position du moteur reste à résultat nul hors rémunération de trésorerie. Il ne représente pas nécessairement le rendement réel d'un placement en euros. Aucune comparaison avec une stratégie concurrente n'est ajoutée à ce programme de recherche.

## 9. Livrables et fonctionnement

- `STRATEGY_CHARTER.json` : une seule stratégie active en recherche, paramètres inchangés, réel désactivé.
- `SOURCE_REGISTER.json` : sources lues, sources non lues, limites et état réseau.
- `existing_trade_analysis/` : analyse des trois trades sans nouveau backtest.
- `sources/` : copies des documentations effectivement récupérées et journaux d'accès.
- `scripts/analyse_focused_strategy.py` : reproduction de l'analyse locale.
- `scripts/run_focused_backtest.py` : futur lanceur limité à A, avec les deux scénarios de coûts existants. Les autres variantes ne sont pas relancées par cette commande.

La conformité du lanceur et son aide ont été vérifiées. Il n'a pas exécuté de nouveau backtest dans cette phase de recherche documentaire. Le chargeur disponible n'accepte actuellement que le cache 2021 identifié : il faudra intégrer explicitement et qualifier toute autre donnée.

La recherche est désormais cadrée sur un seul mécanisme. Sa validation économique et la consultation des sources financières primaires restent ouvertes et nommées comme telles.
