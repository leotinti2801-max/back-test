# Audit de conception fréquence/levier — proposition du4novembre2026

Lecture des sources uniquement ; aucun backtest financier ni test de marché lancé.
La proposition couvre les huit bras annoncés, sans promotion automatique et sans
modifier V03, ses coûts, le moteur d'exécution ou leurs résultats gelés.

## Les deux paramètres actuellement ignorés par une simple configuration

`simple_forex/runner.py:25` impose `max_holding_minutes=1440` ; ajouter60 dans un
JSON ne suffit donc pas. `strategy_rearmed.py:6-7` impose08h/09h/14:30/16h Londres
et`:20` impose une confirmation M5. Il faut injecter ces choix explicitement.
La formule du signal, le stop de range et le réarmement restent ceux de V03.
L'initialisation `previous=0` autorise toujours la première clôture extérieure,
puis une clôture intérieure réellement observée est nécessaire pour réarmer.
Changer M5 en M1 est une nouvelle granularité de confirmation, pas un simple
changement de quota : `[09:00,09:01)` se ferme à09:01, entrée sur la ligne M1
commençant à09:01, jamais à09:00 ni à09:02 par décalage accidentel.

## Architecture isolée acceptable

L'option `FunctionType` annoncée peut préserver exactement le code du portefeuille :
copier le dictionnaire `core.simulate.__globals__`, y remplacer uniquement le nom
`parameters` par une factory locale, puis construire une fonction avec le même
`__code__`, les mêmes `__defaults__` et `__closure__`. Copier aussi `__kwdefaults__`
s'ils existent. Vérifier `isolated.__code__ is core.simulate.__code__` et
`isolated.__globals__ is not core.simulate.__globals__`.
Cette approche n'est pas un patch du module : ne jamais affecter
`core.parameters`, `core.signals`, `X.structural_path` ou leurs globals.
Les helpers partagés `order`, `close_position`, `D` et `X` restent en lecture seule.
Les paramètres renvoyés par `core.parameters(...)` sont déjà une copie profonde :
la factory n'ajoute que la durée maximale sur cet objet local.

Passer `signal_source` explicitement à chaque appel, car le défaut du moteur est
le signal V01. Le signal de recherche est une copie courte et paramétrée du signal
réarmé, avec calendrier Londres et pas de confirmation1/5min déclarés par bras.
Copier/fixer les valeurs de chaque bras dans une **factory**, pas dans une closure
capturant une variable de boucle mutable qui appliquerait ensuite le dernier bras.
Chaque appel doit recevoir sa copie de configuration ; aucun cumul de balance,
pause ou compteurs entre bras, scénarios de coûts ou comptes indépendants.

Conserver SHA des sources originales, source des factories et du signal paramétré,
identité du protocole, données, runtime et paramètres effectifs par bras. Un test
de parité V03 doit précéder les nouvelles variantes : mêmes résumés financiers et
CSV de trades à l'octet sous coûts de base **et** stress. Ne pas transformer le
clonage en une réécriture silencieuse des branches de refus ou d'inconnu.

## Huit bras et attribution des différences

| Bras annoncé | Entrées Londres, fin exclue | Sortie Londres | Durée max | Risque/trade | Levier |
|---|---|---|---:|---:|---:|
| V03 témoin |09:00–14:30|16:00|1440min|125€|10|
| LEV30 |identique V03|16:00|1440min|125€|30|
| LEV100 |identique V03|16:00|1440min|125€|100|
| EXTENDED |09:00–16:00|17:00|1440min|125€|10|
| HOLD60 |identique V03|16:00|60min|125€|10|
| EXTENDED_HOLD60 |09:00–16:00|17:00|60min|125€|10|
| EXTENDED_HOLD60_8SMALL |09:00–16:00|17:00|60min|62,50€|10|
| EXTENDED_HOLD60_8SMALL_M1 |identique8SMALL, confirmationM1|17:00|60min|62,50€|10|

Tous gardent3R prévu,500€ de risque prévu journalier, une position, pause24h après
deux pertes, mêmes coûts et mêmes règles de données. LEV30/LEV100 doivent garder
le quota V03 de4 pour isoler le levier. Le quota8 des bras de fréquence doit être
explicite avant calcul : s'il remplace4 dans EXTENDED/HOLD60/EXTENDED_HOLD60,
présenter ces bras comme **horaires/durée+quota**, pas comme une isolation parfaite
des horaires ou de la durée. Garder4 dans ces trois bras serait l'autre option
d'isolation ; ne pas choisir entre ces options après les résultats.
Les deux8SMALL ont explicitement un quota8 ; la réduction de risque est un facteur
supplémentaire, pas une amélioration gratuite du PnL ou du drawdown.

Le moteur teste `daily_risk + budget_par_trade <=500`, puis ajoute le risque
effectivement dimensionné. Avec125€, « environ4 entrées » n'est pas une borne
universelle : arrondis et contrainte de levier peuvent sous-utiliser le budget.
Le quota8 reste une borne explicite. Avec62,50€, huit budgets sont finançables,
mais les signaux, la position et les pauses peuvent empêcher huit entrées réelles.
Un refus ne consomme ni quota d'entrée ni risque réservé.

## Levier : vérifier d'abord si la contrainte agit

`X.size_position` calcule `q_budget=risque/risk_unit`,
`q_leverage=levier*balance*FX_entry/entry_price`, puis arrondit vers le bas le
minimum des deux par pas de2000€. Si le budget de risque est déjà contraignant,
passer10→30→100 ne change aucune quantité. Une quantité supérieure n'est pas
garantie même si `q_leverage` augmente, à cause de l'arrondi.
Journaliser ces deux plafonds, quantité brute/arrondie et contrainte active à
l'entrée, sans modifier la décision. Le levier de ce modèle est un plafond
notionnel : il ne représente pas un modèle complet de marge MT5, liquidation,
stop-out, liquidité ou règles FTMO. Le risque réel reste susceptible de dépasser
le risque prévu lors d'un gap ou d'une conversion FX défavorable.

## Horaires, durée et inconnus

Le moteur d'exécution calcule `min(entrée+durée, échéance UTC du jour)` : convertir
17h Londres selon la date, pas avec un offset fixe. Il suppose une échéance sur
le même jour UTC que l'entrée ; c'est satisfait ici, pas pour un futur overnight.
À l'échéance, il liquide à l'open bid/ask de la ligne de cette minute avec coûts,
avant d'examiner ses extrema. Préserver cette convention déjà gelée, y compris
stop/TP avant échéance et stop prioritaire dans une M1 ambiguë.
Si cette ligne manque, le résultat reste inconnu ; ne pas sortir au dernier close
connu. Le timestamp minute n'est pas une preuve de quote au milliseconde exact.
Conserver l'étiquetteTIME ; ajouter à part une cause descriptive
`HOLD_LIMIT`, `SESSION_CLOSE` ou `BOTH` déduite des échéances déclarées.

La fenêtre étendue finit à16h **exclue** ; la dernière confirmation possible est
15:55 enM5 et15:59 enM1. Avec60min, la sortie de ces positions précède17h ; le
plafond de session n'est normalement pas la contrainte active de ces dernières
entrées. Une sortieTIME à10:20 peut libérer une nouvelle entrée à10:20 : le moteur
comptabilise d'abord la clôture et la pause éventuelle, puis traite le signal.

Le trimestre commun Jan4→Apr1 exclu reste du développement déjà vu. De nouveaux
horaires ou états peuvent rencontrer un trou antérieur que V03 n'exposait pas.
Tous les bras doivent garder arrêt global et total `null` à la première exposition
inconnue ; aucun changement de dates après lecture pour masquer un bras arrêté.
Si les préfixes divergent, ne pas comparer leurs sommes comme des périodes égales.
Le signal cesse après son premier trou de formation ; le portefeuille conserve
toujours les trous rencontrés pendant une position réellement ouverte.

Les diagnostics Jan4→Feb1, Feb1→Mar1, Mar1→Mar29 sont trois fenêtres de28jours,
comptes neufs100000€, pertes/pause remises àzéro. L'historique de données reste
disponible, sans import du compte Q1. Ces fenêtres sont incluses dansQ1 : elles
ne fournissent ni échantillons indépendants ni trajectoire FTMO àdeux phases.
Leurs nets ne sont pas forcément additifs au netQ1, car la pause peut traverser
une frontière de mois dansQ1. Si les huit bras sont calculés surQ1 et ces trois
fenêtres sous deux coûts, cela fait64 rejeux corrélés, pas64 validations.

## Tests à exiger avant résultats

Les cas structurés de `TEST_CASES_PROPOSAL.json` sont des recommandations, pas
des tests exécutés. Les points bloquants sont parité V03, isolation des factories,
bornesM1/M5, durée réellement injectée, sortie de session avecDST, quotas/risque,
pause depuis sortie, arrêt sur données inconnues et absence de mutation du gel.
Rapporter tous les bras et tous les échecs ; ne pas choisir automatiquement le
meilleur ni multiplier ensuite les durées/seuils. La fréquence se mesure par
entrées réellement exécutées et leur distribution par journée, pas par plafond.
