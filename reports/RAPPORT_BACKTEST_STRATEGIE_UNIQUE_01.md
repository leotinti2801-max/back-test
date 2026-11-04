# Backtest de la stratégie unique EUR/USD H4/M30

Exécution : focused_run_01, 3 novembre 2026. Période UTC : 01/01/2021 inclus – 01/01/2022 exclu.

Une seule stratégie : A_STRUCTURE_FIXED_2R, structure H4, cassure M30, premier repli POI et cible prévue à 2R. Paramètres gelés inchangés. Capital initial 100 000 €, risque prévu maximal de 250 € par position.

| Mesure | Coûts de base | Commission ×1,5 et glissement ×2 |
| --- | ---: | ---: |
| Trades clos | 3 | 3 |
| Gagnants / perdants | 2 / 1 | 2 / 1 |
| Résultat net observé | +201,22 € | +173,09 € |
| Profit factor | 1,80 | 1,69 |
| Drawdown sur clôtures | 250,02 € | 250,15 € |

Les deux gains proviennent de sorties horaires ; aucun TP à 2R n'a été exécuté. Le troisième trade sort au stop. Les scénarios réutilisent les mêmes données et leurs trades ne sont pas des observations indépendantes.

## Vérification

Le lanceur dédié à une seule stratégie a été exécuté avec succès, code de sortie 0. Les manifestes SHA256 sont vérifiés. Les flux monétaires des six lignes des deux scénarios ont été recalculés directement depuis les quotes : écart maximal de 0 €. Les résultats sont identiques à ceux de la stratégie A lors de la précédente exécution annuelle. Aucun autre candidat n'a été relancé.

## Limites

Ce calcul réutilise 2021 et les mêmes paramètres : il vérifie la reproductibilité, sans constituer une validation indépendante. Trois trades ne démontrent pas une rentabilité stable. Le flux historique demeure incomplet ; les chemins choisis n'ont pas rencontré d'état actif non résolu, ce qui ne certifie pas la complétude du marché. Le drawdown présenté porte sur les clôtures et ne mesure pas tous les creux intraposition. Aucun ordre réel n'est envoyé.

## Reproduction

Depuis la racine du dépôt, avec un nouveau dossier de sortie :

```sh
PYTHONPATH=src python scripts/run_focused_backtest.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/focused_run_02
```
