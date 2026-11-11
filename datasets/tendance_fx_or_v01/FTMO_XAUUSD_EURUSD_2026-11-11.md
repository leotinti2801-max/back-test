# Fiche FTMO : XAUUSD et EURUSD

Lecture le **11 novembre 2026** (date Europe/Paris).
Source principale : [Symbols, FTMO Global](https://ftmo.com/en/symbols/), affichage dynamique consulté dans le navigateur. Les valeurs ci-dessous sont celles de cette lecture, et non celles d'un extrait ancien indexé par un moteur de recherche. Il s'agit de CFD simulés, pas de contrats futures.

| Paramètre, pour 1 lot | EURUSD | XAUUSD |
| --- | --- | --- |
| Instrument affiché | Euro vs United States Dollar | Gold vs US Dollar, Spot CFD |
| Taille du contrat | 100 000 EUR | 100 onces troy |
| Point technique MetaTrader | 0,00001 USD/EUR | 0,01 USD/once |
| Valeur d'un point pour 1 lot, en USD | 1 USD | 1 USD |
| Commission affichée sur Symbols | 5 USD/lot | 0,0014 % du volume notionnel |
| Commission par côté, précisée par la mise à jour officielle | 2,50 USD/lot | 0,0007 % du notionnel de chaque côté |
| Swap acheteur affiché | −10,27 points | −92,26 points |
| Swap vendeur affiché | +0,13 point | −4,20 points |
| Unité du swap affichée | points | points |
| Marge Standard | 1 % | 2 % |
| Levier Standard | 1:100 | 1:50 |
| Levier Swing | 1:30 | 1:15 |
| Cotation du lundi au vendredi, heure affichée GMT+2 | 00:05–23:55 | 01:05–23:50 |
| Samedi et dimanche | fermé | fermé |

## Unités et commissions

La page Symbols affiche la taille du contrat, les swaps, les commissions, les leviers et les horaires. La définition du point technique vient de [FTMO Quick Trade Manager](https://ftmo.com/en/quick-trade-manager/) : cinquième décimale sur EURUSD, deuxième décimale sur les métaux. **La valeur monétaire du point est calculée**, et n'est pas une mesure de rendement : taille du contrat × incrément de prix. Elle est exprimée en USD avant conversion éventuelle vers la devise du compte. Un mouvement de 1,00 USD/once sur XAUUSD vaut donc 100 USD par lot. Le pip utilisé sur d'autres plateformes ne doit pas être confondu avec ce point MetaTrader.

La [mise à jour FTMO du 25 septembre 2025](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/), entrée en vigueur le 29 septembre 2025, précise le tarif **par côté**. Pour EURUSD, l'ouverture et la fermeture totalisent 5 USD par lot. Pour XAUUSD, la commission de chaque exécution est `prix d'exécution × 100 × nombre de lots × 0,000007`. Les deux exécutions peuvent avoir des notionnels différents. Le chiffre de 0,0014 % affiché sur Symbols ne doit donc pas être appliqué à chacun des deux côtés.

## Portée de la lecture

Les swaps sont une photographie actuelle. Cette fiche ne fournit pas leur historique 2020–2026, ni un calendrier vérifié des multiplicateurs de rollover. Les horaires sont ceux affichés en **GMT+2 au moment de la lecture**. Les jours fériés, maintenances et modifications exceptionnelles se vérifient sur la plateforme et dans les [Trading Updates FTMO](https://ftmo.com/en/trading-updates/).

Les valeurs présentées ne sont pas une mesure des coûts exécutés sur un compte FTMO. Aucun spread historique FTMO n'est fabriqué à partir des prix HistData. Aucun ordre, aucun backtest, aucune statistique de rendement.

La transcription des deux panneaux consultés est conservée dans `provenance/FTMO_BROWSER_TRANSCRIPTION.json`.
