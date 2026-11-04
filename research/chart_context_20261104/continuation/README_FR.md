# Continuation indépendante des vrais TP2R

Module de recherche, sans modification du bot et sans lancement historique
automatique. Le plan `PLAN_BEFORE_HISTORY.json` est fixé avant le calcul historique.
Le parent doit d'abord rejouer un portefeuille V03 réellement ciblé2R sur Q1
commun, puis fournir uniquement ses vraies sortiesTP. Les61 anciens trades V03
à3R ne constituent pas cette population2R.

```python
from research.chart_context_20261104.continuation import continue_trade, source_identity

# params = paramètres exacts du trade/scénario (base ou coûts augmentés),
# construits avec frozen.parameters et l'échéance16h Londres du jour.
# cfg doit être celui du portefeuille2R, avec planned_quote_reward_risk=2.
observation = continue_trade(mk, trade, params, cfg)
outcome3 = observation['thresholds']['3R']
```

`trade` accepte les champs du dictionnaire de trade du runner et les valeurs
textuelles de son CSV : entry_utc, direction, entry_price, stop, target, qty_eur,
exit_reasonTP et closed_at_ms/exit_utc ; risque prévu et cash réalisés sont
contrôlés lorsqu'ils sont fournis. Une source incohérente lève
`ContinuationInputError`, au lieu d'être comptée comme un seuil non atteint.

Le module recertifie le chemin2R puis utilise `X.structural_path` séparément pour
3/4/5R depuis **la même entrée**, avec le même stop initial, la même quantité,
les mêmes coûts et la sortie16h Londres. Il s'agit de « conserver au lieu de
sortir à2R », pas d'une seconde entrée à2R ni d'un stop déplacé au break-even.
Les niveaux suivent exactement la formule du runner, frais prévus inclus en
devise de cotation ; ils ne garantissent pas exactement3/4/5R cashEUR réalisé.

Chaque seuil contient `reached=true/false/null` et l'un des statuts suivants :

- `REACHED_BEFORE_STOP_OR_DEADLINE` : TP du modèle avant stop/échéance ;
- `STOP_BEFORE_THRESHOLD` : stop du modèle, y compris son gap éventuel ;
- `EXPIRED_AT_DEADLINE` : échéance atteinte sans TP, avec priorité à son open ;
- `UNKNOWN_DATA_GAP` : parcours restant inconnu, jamais imputé comme un non-hit.

Un3R connu reste oui si4R/5R deviennent inconnus. Un seuil peut être atteint dans
la minute même du TP2R : `time_relation=SAME_M1_AS_2R`. Cette observation ne prouve
pas un passage strictement **après le fill2R** ; l'ordre intraminute reste inconnu.
`LATER_M1_AFTER_2R` distingue une minute ultérieure. Pour un résultat inconnu,
cette relation désigne la première ligne non observée, pas une minute d'atteinte.
`event_row_open_ms` est l'ouverture de la minute, `model_closed_at_ms` la borne
temporelle du moteur, pas un fill tick certifié. Un TP/SL de la ligne10:01 est
rapporté clos à10:02 ; une sortieTIME de10:02 emploie l'open de10:02.

Stop et seuil dans la même M1 : convention prudente stop prioritaire et flag
`stop_and_target_same_M1=true`. Ce n'est pas la preuve qu'un stop était inévitable
en ticks. Un vrai TP2R du même moteur ne peut pas avoir son stop touché dans sa
minuteTP : la recertification rejette ce conflit. La minuteTP2 n'est donc pas
retirée du diagnostic3/4/5R, ce qui ferait perdre des dépassements connus.

Les continuations peuvent se chevaucher alors que le portefeuille réel était déjà
sorti. **Ne pas agréger leurs PnL en equity, refaire un portefeuille comparatif ou
en déduire un passageFTMO.** Le parent doit rapporter les dénominateursTP2, les
oui de même minute, les oui ultérieurs, les non résolus et les inconnus séparément.

Tests synthétiques uniquement :

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s research/chart_context_20261104/continuation -p 'test_continuation.py' -v
```

Le résultat des contrôles et les identités avant historique sont consignés dans
`SYNTHETIC_VALIDATION.json` et `SOURCE_IDENTITY_BEFORE_HISTORY.json`.
Tout changement de source exige un nouveau gel du parent avant le calcul concerné.
