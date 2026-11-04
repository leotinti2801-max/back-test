# Diagnostic causal de chaque occasion — stratégie unique EUR/USD

Les occasions sont les franchissements certifiés par le contexte existant. Des bougies incomplètes peuvent en masquer d’autres ; elles ne sont pas imputées à des absences de signal.

## Réconciliation des franchissements

| Scénario | Franchissements | Issues |
| --- | ---: | --- |
| base | 914 | NOT_EVALUATED_OUTSIDE_UTC_SESSION: 440; REFUSED_STATIC_CONDITIONS: 443; SETUP_CREATED: 8; IGNORED_DYNAMIC_GATE: 23 |
| higher_costs | 914 | NOT_EVALUATED_OUTSIDE_UTC_SESSION: 440; REFUSED_STATIC_CONDITIONS: 443; SETUP_CREATED: 8; IGNORED_DYNAMIC_GATE: 23 |

## Cycle de vie de chaque setup

Voir les fichiers BASE_SETUPS.csv et HIGHER_COSTS_SETUPS.csv pour les dates, raisons et décisions. Les motifs simultanés ne doivent pas être additionnés comme des cas indépendants.

- base : 8 setups ; {'ENTERED': 3, 'SESSION_CLOSE_NO_ENTRY': 3, 'FIRST_RETURN_REFUSED': 2}.
- higher_costs : 8 setups ; {'ENTERED': 3, 'SESSION_CLOSE_NO_ENTRY': 3, 'FIRST_RETURN_REFUSED': 2}.

## Trades exécutés

| Scénario | Entrée UTC | Sortie | Net EUR | R encaissé |
| --- | --- | --- | ---: | ---: |
| base | 2021-01-05T09:56:00Z | TIME | 238.54 | 0.959 |
| base | 2021-07-16T09:13:00Z | SL_GAP | -250.02 | -1.002 |
| base | 2021-07-20T15:27:00Z | TIME | 212.71 | 0.854 |
| higher_costs | 2021-01-05T09:56:00Z | TIME | 224.27 | 0.904 |
| higher_costs | 2021-07-16T09:13:00Z | SL_GAP | -250.15 | -1.002 |
| higher_costs | 2021-07-20T15:27:00Z | TIME | 198.97 | 0.803 |

## Prochaine action de recherche

Qualifier les données H4/M30 et la couverture de l’ATR avant de retoucher les filtres. Examiner ensuite les setups consommés par les horaires et les fins de session à partir des événements, sans supposer que les entrées refusées auraient gagné.

Les enveloppes M1 de liquidation sont conservées pour examiner les positions ouvertes. Elles incorporent des coûts de sortie hypothétiques et ne représentent pas automatiquement l’equity contractuelle FTMO. Aucun statut de réussite FTMO n’est attribué sans profil de compte vérifié.

Cette exécution réutilise le développement 2021 avec les mêmes règles. Le diagnostic ajoute de la traçabilité, aucune nouvelle hypothèse de trading.
