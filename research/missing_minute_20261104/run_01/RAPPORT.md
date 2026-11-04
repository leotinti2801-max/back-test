# MISSING_MINUTE_V01 — rapport après l'unique exécution autorisée

**Verdict préfixé : ARRÊT pour V03 et ARRÊT pour V04.**

Sur le bloc d'évaluation du1eravril2021 inclus au1erjanvier2022 exclu,
S_CONT avec coûts renforcés perd8 165,45 EUR pour V03 et7 614,92 EUR pour V04.
Aucun run n'est interrompu par R2. Le verdict vient donc de la deuxième règle,
net S_CONT renforcé inférieur ou égal à zéro. Les effectifs dépassent100,
mais cela n'annule pas ce critère prioritaire.

ARRÊT signifie arrêt de cette piste sur ces données. Ce n'est ni une preuve
qu'aucune autre variante ne peut fonctionner, ni une autorisation d'en essayer
une. V03 reste la référence ; V04 ne la remplace pas. ICT reste en pause.
Aucun ordre, aucune connexion courtier, aucun déploiement ni probabilité FTMO.

## Exécution et intégrité

L'utilisateur a envoyé exactement :

```text
GO RUN MISSING_MINUTE_V01 4f87d394b249543486b49588bed8813a4d706d0b33c70a15c803e0b7ba1b0a53
```

Une invocation de `evaluate_after_go.main()` a effectué les12 trajectoires
prévues :2 stratégies ×3 scénarios ×2 coûts. Elle a terminé sans exception
le4novembre2026, de21:45:07 à21:45:20 UTC, soit22:45 à Paris.
Aucune seconde invocation, aucune relance automatique, aucun changement
de code ou de règle après le gel. Le témoin et l'évaluation sont deux blocs
d'un compte continu depuis le4janvier, pas deux comptes remis à zéro.

Le lanceur a été appelé depuis un wrapper qui capture les versions avant/après.
Les arguments transmis étaient :

```text
--go "GO RUN MISSING_MINUTE_V01 4f87d394b249543486b49588bed8813a4d706d0b33c70a15c803e0b7ba1b0a53"
--cache /workspace/back-test/data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl
```

L'empreinte du gel est restée inchangée :

```text
4f87d394b249543486b49588bed8813a4d706d0b33c70a15c803e0b7ba1b0a53
```

Le cache contrôlé à l'invocation est celui attendu :

```text
9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2
```

Les résultats originaux et leur `MANIFEST_SHA256.json` n'ont pas été réécrits
pour ajouter ce rapport. Les compléments de vérification sont séparés.

## Versions réellement utilisées et tirages

| Élément | À l'invocation | Après l'invocation | Gel |
| --- | --- | --- | --- |
| Python | 3.12.14 | 3.12.14 | 3.12.14 |
| numpy | 2.3.5 | 2.3.5 | 2.3.5 |
| pandas | 2.2.3 | 2.2.3 | 2.2.3 |

Interpréteur enregistré :
`/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`.

Les tirages portent sur197 séances lundi–vendredi, séances sans trade incluses.
Pour chacun des5000 tirages,40 blocs mobiles non circulaires de5séances sont
concaténés puis tronqués à197séances. Générateur numpy PCG64, graine20261104.
La matrice est commune à V03 et V04. Les trades sont rattachés à la séance
de leur entrée ; un tirage sans trade vaut0.

Empreinte recalculée après le run, entiers int64 little-endian :

```text
4146fb33453d9928b71d3313c625ec6c4c6bbec256a3df12e2ec65f2d488f635
```

**Comparaison au gel : identique**, ainsi que le générateur et la forme5000×197.
Ce contrôle recalcule les indices calendaires avec la fonction gelée. Il ne
relance ni les trajectoires ni les métriques bootstrap de performance.
Preuve : [POST_RUN_ENVIRONMENT_AND_DRAWS.json](POST_RUN_ENVIRONMENT_AND_DRAWS.json).

## Bloc de contrôle —4janvier au1eravril2021 exclu

| Stratégie | Trades, par scénario et coût | Net base EUR | Net renforcé EUR |
| --- | ---: | ---: | ---: |
| V03 3R | 61 | +642,37 | +504,22 |
| V04 2R | 61 | +839,28 | +719,24 |

Les trois scénarios reproduisent ce même contrôle sans trou en position.
Les732 lignes de contrôle des12 trajectoires sont comparées aux témoins
gelés, champ par champ, dans la tolérance1e-8. Les valeurs arrondies ci-dessus
ne remplacent pas les valeurs précises des CSV/JSON.

Ces résultats Q1 étaient déjà publiés : ils ne sont pas de nouvelles preuves.
Ils ne doivent pas être présentés comme le résultat de l'évaluation suivante.

## Bloc d'évaluation —1eravril au1erjanvier2022 exclu

Chaque net inclut déjà les coûts et le change du scénario. Le R réalisé est
`net EUR / risque prévu EUR` du trade, puis moyenné sur les trades clos.

| Stratégie | Scénario | Trades base | Net base EUR | Moyenne R base | Trades renforcés | Net renforcé EUR | Moyenne R renforcée |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V03 | S_CONT | 211 | −7 623,32 | −0,292142 | 210 | −8 165,45 | −0,314391 |
| V03 | S_PESS | 210 | −7 833,70 | −0,301871 | 209 | −8 372,77 | −0,324030 |
| V03 | S_OPT | 213 | −5 801,86 | −0,219832 | 212 | −6 327,47 | −0,241219 |
| V04 | S_CONT | 214 | −7 202,84 | −0,272409 | 213 | −7 614,92 | −0,289067 |
| V04 | S_PESS | 213 | −7 413,22 | −0,281909 | 212 | −7 822,24 | −0,298449 |
| V04 | S_OPT | 216 | −5 995,38 | −0,224410 | 215 | −6 393,52 | −0,240385 |

Les nets restent négatifs dans les trois scénarios et les deux coûts.
Les effectifs changent : un résultat hypothétique au trou modifie ensuite
les pauses et le solde. **S_PESS et S_OPT ne sont pas des bornes mathématiques
garanties du portefeuille**, même s'ils sont ici ordonnés de cette façon.

Le compte continu complet Jan4–Jan1 donne notamment, pour S_CONT renforcé :
V03−7 661,23 EUR et V04−6 895,68 EUR, soit contrôle+évaluation. Le verdict
préannoncé porte exclusivement sur le bloc d'évaluation, pas sur ces totaux.
La séparation et les chiffres précis sont disponibles dans
[BLOCK_COMPARISON.csv](BLOCK_COMPARISON.csv).

## Inférence et application des règles de décision

Calcul exclusivement sur S_CONT renforcé, selon la procédure demandée :
`p brut = (1 + nombre de métriques bootstrap <=0) /5001`, puis Holm à deux
stratégies. Ce sont les p de la règle utilisateur, pas une calibration
indépendante ou une probabilité de réussite FTMO.

| Mesure sur évaluation S_CONT renforcé | V03 | V04 |
| --- | ---: | ---: |
| Trades clos | 210 | 213 |
| Net EUR | −8 165,45 | −7 614,92 |
| Moyenne nette R/trade | −0,314391 | −0,289067 |
| Percentile inférieur unilatéral95 %, non ajusté, descriptif | −0,433461 | −0,392159 |
| p brut enregistré | 1,000000 | 1,000000 |
| p ajusté Holm | 1,000000 | 1,000000 |
| Net S_PESS renforcé EUR | −8 372,77 | −7 822,24 |
| Verdict | **ARRÊT** | **ARRÊT** |

Les deux stratégies sont incluses dans Holm malgré leur arrêt au critère de
net négatif. Aucun R2 ne bloque l'inférence commune. Le percentile descriptif
n'est pas utilisé pour le verdict. Aucune stratégie ne remplit les trois
conditions de candidature ; le résultat Q1 plus favorable de V04 ne change
pas son statut.

## Trous rencontrés et règles appliquées

Chacune des12 trajectoires rencontre les quatre mêmes trous d'une minute
pendant une position, tous dans le bloc d'évaluation :

| Minute absente UTC | Première minute observée suivante UTC | Longueur | Règle |
| --- | --- | ---: | --- |
| 01/04/2021 11:40 | 01/04/2021 11:41 | 1min | R1 |
| 13/04/2021 09:29 | 13/04/2021 09:30 | 1min | R1 |
| 14/06/2021 12:05 | 14/06/2021 12:06 | 1min | R1 |
| 12/08/2021 10:38 | 12/08/2021 10:39 | 1min | R1 |

Ces48 occurrences corrélées correspondent à **quatre trous distincts**,
pas48 événements indépendants. Aucune échéance ne tombe dans ces quatre trous.

- S_CONT garde la position ouverte sans prix dans le trou. Les trades
  concernés finissent à TIME pour le1eravril et le14juin, au stop pour
  le13avril et le12août, dans les trajectoires renforcées.
- S_PESS sort au stop ou à l'ouverture de reprise si plus défavorable,
  avec glissement et conversion à la reprise.
- S_OPT sort au TP sans amélioration de prix, avec conversion à la reprise.
- Aucun R2 et aucun motif R3 `ENTRY_QUOTE_MISSING_REFUSED` n'est déclenché
  dans ces12 trajectoires. Cela ne signifie pas que le cache est complet.

Les journaux d'origine `GAPS_ENCOUNTERED.csv` contiennent entrée, début/fin,
reprise, longueur et issue. [GAPS_READABLE.csv](GAPS_READABLE.csv) les rapproche
des trades déjà exécutés, sans reconstituer une trajectoire de marché.
Aucune marque de liquidation n'est enregistrée dans une minute absente.
La quarantaine du1ernovembre00–01hUTC reste inchangée.

## Pertes et refus du cas principal

Sur l'évaluation S_CONT renforcée :

- V03 :65 gagnants et145 perdants ;124 pertes au stop (dont2 gaps au stop)
  et21 pertes à la sortie horaire. Les sorties totales sont122SL,2SL_GAP,
  82TIME et4TP.
- V04 :68 gagnants et145 perdants ;123 pertes au stop (dont2 gaps au stop)
  et22 pertes horaires. Sorties totales :121SL,2SL_GAP,70TIME et20TP.

Les frais sont déjà inclus. Les motifs ci-dessus sont mécaniques, pas une
cause macroéconomique inventée. Chaque entrée, refus et sortie reste dans
les CSV de la trajectoire correspondante. Aucune perte n'a été supprimée
pour améliorer l'échantillon.

## Contrôles et limites

[POST_RUN_AUDIT.json](POST_RUN_AUDIT.json) consigne l'audit par Codex des
sorties existantes :12 cellules,3 280 lignes de trades corrélées,732 lignes
de contrôle,747 151 marques de liquidation et137 empreintes vérifiées.
Il contrôle budgets125/500 EUR, plafond4, absence de chevauchement, pauses,
R réalisés, soldes, attribution des blocs, absence de marques dans les trous,
ajustement Holm depuis les p enregistrés et priorité des verdicts.

Cet audit ne charge pas le cache, ne relance aucun simulateur et ne recalcule
pas le bootstrap de performance. Il ne constitue pas une validation
indépendante de la stratégie. Les valeurs des5000 métriques bootstrap ne
sont pas persistées par le lanceur gelé ; les p et percentiles sont ceux
de sa sortie, et l'empreinte des indices calendaires est vérifiée séparément.

Le bloc d'évaluation2021 reste du développement déjà consulté, non vierge.
Ces scénarios traitent des absences sans les réparer et n'établissent pas
le chemin réel des prix dans les trous. L'ancien run annuel arrêté avec
`net_eur=null` demeure intact : ces nouveaux résultats utilisent d'autres
règles explicites de couverture, ils ne remplacent pas sa conclusion.

**Fin du lot : aucune optimisation, nouvelle variante ou relance.**
