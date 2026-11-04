# Cassure Londres EURUSD : preuves consultées et limites

Lecture du 4 novembre 2026. Hypothèse unique : protocole
[`simple_forex/protocol_v01.json`](../../../simple_forex/protocol_v01.json).
Aucun paramètre changé, aucune grille, aucun nouveau backtest.

## Conclusion utile

Aucune des sept sources effectivement lues dans ce cycle ne démontre un avantage
net de la spécification EURUSD suivante : range 08–09 Europe/London, première
clôture M5 au-delà du range entre 09 et 12, stop opposé, cible prévue 2R et sortie
16 heures. Les sources apportent des méthodes de contrôle et un exemple de
breakout dont les instruments, l'horizon et les sorties diffèrent. Elles ne
permettent pas de promettre le passage FTMO en un mois. Cette recherche ciblée
ne démontre pas qu'aucune étude pertinente n'existe ailleurs.

## Ce que les auteurs permettent réellement de retenir

| Source effectivement lue | Apport vérifié | Limite pour notre stratégie |
| --- | --- | --- |
| [Carver : présentation de pysystemtrade](https://github.com/robcarver17/pysystemtrade/blob/master/README.md) | Le projet se présente comme un moteur de trading systématique sur futures. La copie locale explique le transfert vers l'organisation pst-group détenue par Rob Carver et Andy Geach en janvier 2026. | Un framework de futures et ses exemples ne constituent pas une étude de rentabilité sur EURUSD spot/CFD chez une prop firm. |
| [Carver : guide de backtest, coûts](https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md#costs) | Distingue coûts par transaction et approximation par turnover; juge les coûts monétaires par transaction plus précis pour des positions clairsemées. Inclut spread/slippage, commissions et coûts de détention. | Les paramètres de coût d'un autre instrument ou courtier ne se transfèrent pas automatiquement. La convention Carver « demi-spread » n'est pas un supplément à ajouter à nos exécutions qui emploient déjà bid et ask : cela compterait le spread deux fois. |
| [Carver : périodes d'estimation](https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md#time-periods) et [cache](https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md#advanced-caching-when-backtesting) | Préfère estimation expanding ou rolling à l'in-sample; avertit explicitement du surajustement implicite après modifications répétées. | Relire ou retester 2021 ne rend pas 2021 indépendant. Une règle simple reste sélectionnée si ses choix résultent de résultats déjà vus. |
| [Carver/pst-group : code breakout](https://github.com/pst-group/pysystemtrade/blob/master/systems/provided/rules/breakout.py) | La docstring indique `Lookback in days`. Le code prend le min/max glissant, place le prix par rapport à leur milieu puis lisse un forecast. | Ce code ne définit ni plage 08–09 Londres, ni déclenchement M5, ni stop opposé, ni cible 2R, ni sortie 16 heures. La ressemblance du mot « breakout » ne transmet aucune performance à notre protocole. Le code accepte une série pandas générique : la docstring en jours n'est pas une preuve d'exécution intraday. |
| [arch : comparaisons multiples](https://github.com/bashtage/arch/blob/main/doc/source/multiple-comparison/multiple-comparison-reference.rst) | Décrit SPA/Reality Check, StepM et MCS pour tenir compte de plusieurs modèles et de la dépendance des pertes. | La présence d'un outil statistique n'est pas un résultat statistique. Aucun test SPA/MCS n'a été exécuté ici; les papiers cités par cette documentation n'ont pas été lus dans ce cycle. |
| [arch : bootstraps de séries temporelles](https://github.com/bashtage/arch/blob/main/doc/source/bootstrap/timeseries-bootstraps.rst) | Décrit des rééchantillonnages par blocs. Indique que les variantes standard visent des données stationnaires; la variante locale suppose une évolution lente et des choix de blocs/localité. | Mélanger librement des trades n'établit ni leur indépendance, ni la stabilité des régimes, ni la probabilité de passage. Notre pause de 24 heures, les séances, les frais et les règles d'évaluation rendent l'ordre temporel pertinent. Aucun bootstrap n'a été calculé. |

Les deux autres fichiers arch du registre sont la page d'entrée et sa
bibliographie, pas deux études financières indépendantes. Le registre contient
sept documents, provenant de deux familles documentaires d'auteurs.

## Connaissances directement applicables

1. **Garder une hypothèse précise.** La continuation après cassure est une
   hypothèse mesurable, pas un fait acquis. L'heure de Londres, la définition des
   bougies complètes, le côté bid/ask, l'expiration et l'ordre d'exécution doivent
   rester fixés avant de lire le prochain échantillon indépendant. Les sources
   consultées ne démontrent pas que 08–09 est la meilleure plage ou que 2R est
   optimal; aucune nouvelle recherche de seuils n'est justifiée par ces lectures.
2. **Mesurer l'argent réalisé.** Un objectif de prix 2R ne donne pas une moyenne
   de gains égale à 2R. Les sorties à 16 heures peuvent être positives ou
   négatives; coûts et conversion en euros interviennent également. La formule
   scolaire de seuil de réussite de 1/3 ne s'applique que si chaque gain net vaut
   exactement +2R et chaque perte nette exactement −1R. Si le ratio est exprimé
   avant frais, les coûts doivent d'abord être intégrés. Ces hypothèses de gains
   et pertes fixes ne décrivent pas nos sorties observées. Ce point est une déduction
   arithmétique, pas une performance issue d'un article.
3. **Conserver l'ordre et les inconnues.** Une minute manquante pendant une
   position empêche d'en connaître le résultat; un bootstrap ne restaure pas le
   chemin. Des refus peuvent préserver une limite de risque et ne sont pas, à
   eux seuls, des gains manqués. Lire davantage ne change pas ces états observés.
4. **Distinguer trois preuves.** Un signal causal correctement implémenté, une
   espérance nette positive hors développement, puis le respect chronologique
   des deux phases FTMO sont trois questions différentes. Ni une documentation
   de moteur de trading, ni un test logiciel, ni une hausse de risque n'apporte
   à elle seule les deux dernières preuves.

## Confrontation aux résultats déjà produits

Les chiffres ci-dessous sont uniquement relus dans
[`reports/simple_london_v01_02/RESULTS.json`](../../../reports/simple_london_v01_02/RESULTS.json),
sans relance ni calcul d'une nouvelle performance.

- D45 : 27 trades clôturés, net connu **+670,63 €**, dont 14 sorties à l'heure,
  9 stops et seulement 4 objectifs atteints. Le nombre de gains n'identifie donc
  pas le nombre d'objectifs 2R atteints.
- Demande annuelle 2021 : 49 trades clôturés avant interruption, net des seules
  clôtures connu **−246,39 €**. Le résultat annuel reste **inconnu**. La position
  du 1er avril devient non résolue à la minute absente de **11:40 UTC**.
- D45 appartient à 2021 : les 27 et 49 trades ne sont pas deux échantillons
  indépendants à additionner. Tout 2021 est déjà du développement.
- Les chiffres publiés indiquent eux-mêmes `independent_validation: false` et
  `FTMO_pass_claimed: false`. La littérature lue n'autorise pas à modifier ces
  conclusions.

La prochaine preuve utile reste un historique bid/ask qualifié permettant de
résoudre la branche interrompue, puis une évaluation sur une période jamais
consultée avec la règle figée et les clauses FTMO actuelles vérifiées. Ce sont
des prérequis d'évaluation, pas une prévision de rentabilité. Aucun retrait de
trades perdants, ajout d'indicateurs ou hausse de risque ne découle de ce cycle.

## Traçabilité et bornes de la lecture

Les copies locales et leurs SHA256 sont dans
[`SOURCE_REGISTER.json`](SOURCE_REGISTER.json) et [`SHA256SUMS`](SHA256SUMS).
Les URLs sur des branches `master`/`main` sont mutables : les empreintes fixent
les octets réellement lus, pas un commit historique supposé. Deux nouveaux
fichiers ont été obtenus directement des dépôts officiels d'auteurs sur GitHub,
par le proxy hérité avec TLS vérifié. Les autres proviennent des copies locales
déjà archivées; leurs empreintes ont été revérifiées avant réutilisation.

Les articles financiers BIS, Fed et AQR mentionnés ailleurs dans le dépôt n'ont
pas été lus dans ce cycle : leurs destinations restent non activées. Aucun
miroir, relais, retrait du proxy ou contournement de TLS n'a été employé. Aucune
conclusion sur leur contenu ou sur un edge Forex M5 n'en est tirée.
