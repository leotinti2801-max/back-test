# Nouveau backtest V02 — exécution annual_v02_03

Date : 3 novembre 2026. Instrument : EURUSD. Période : du 1er janvier 2021 inclus au 1er janvier 2022 exclu, UTC.

**Nouvelle exécution terminée avec succès. Les données et les paramètres sont inchangés ; les résultats sont identiques à la précédente exécution. Ce test vérifie la reproductibilité, pas une nouvelle période de marché.**

## Résultats après frais

| Variante | Trades clos | Gagnants / perdants | Net observé | Net avec coûts augmentés | Drawdown sur clôtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| A — biais original, cible 2R | 3 | 2 / 1 | 201,22 € | 173,09 € | 250,02 € |
| B — impulsion H4, cible 2R | 11 | 4 / 7 | -608,81 € | -654,68 € | 1 184,14 € |
| C — corps ≥0,5 ATR, cible 2R | 20 | 7 / 13 | -1 055,13 € | -1 154,59 € | 1 555,64 € |
| D — corps ≥0,5 ATR, cible 1,5R | 20 | 7 / 13 | -1 208,94 € | -1 287,61 € | 1 583,22 € |
| E — cible structurelle connue | 1 | 0 / 1 | -249,67 € | -249,70 € | 249,67 € |

Capital de départ : 100 000 €. Risque prévu maximal : 250 € par position. Une entrée par jour UTC au maximum et pause de 24 h après deux pertes consécutives. Année rejouée en continu, sans remise à zéro des soldes ou des pauses entre trimestres.

Scénario de coûts augmentés : commission ×1,5 et glissement de marché ×2, spread bid/ask du cache conservé. Les tailles et les cibles en R sont recalculées avec ces hypothèses de coûts.

## Contrôles de cette exécution

- Dix cellules exécutées : cinq variantes et deux scénarios de coûts ; code de sortie 0.
- Aucun arrêt pour entrée ou position inconnue sur les chemins V02 choisis.
- Les 110 lignes de trades des dix cellules ont été auditées directement depuis les quotes : écart de calcul monétaire maximal de 0 €. Elles comprennent des variantes/scénarios corrélés et ne forment pas 110 observations indépendantes.
- Manifestes SHA256 vérifiés. Résultats JSON, trades CSV et décisions CSV identiques à l’octet à annual_v02_02.
- Aucun changement de code ou de paramètre ; aucun ordre envoyé.

## Interprétation

La variante A est positive sur seulement trois trades ; cet échantillon ne suffit pas à établir sa rentabilité. Les quatre autres variantes sont déficitaires. Aucune nouvelle qualification économique ni activation pour le réel.

Seul le cache 2021 fourni est utilisé. Cette année a déjà servi au développement et comporte des lacunes. L’absence de position non résolue dans ces simulations ne certifie pas la complétude du marché historique. Le drawdown porte sur les clôtures, pas sur tous les creux intraposition.

Pour une validation indépendante, il faut un historique bid/ask qualifié sur une période encore inutilisée. Relancer le même code sur le même historique ne crée pas de nouvelles observations.

## Reproduction

Depuis la racine du dépôt, en choisissant de nouveaux dossiers/fichiers de sortie :

```sh
PYTHONPATH=src python scripts/verify_annual.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --freeze reports/run_v02_02/FREEZE_BEFORE_RESULTS.json \
  --output reports/annual_v02_04

PYTHONPATH=src python scripts/audit_results.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --results reports/annual_v02_04 \
  --output reports/AUDIT_CASH_FLOWS_RUN04.json
```
