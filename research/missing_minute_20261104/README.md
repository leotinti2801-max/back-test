# MISSING_MINUTE_V01 — préparation, puis arrêt avant évaluation

Ce lot est autorisé uniquement sur `research/missing-minute-v01`, sous ce
dossier. Il ne modifie ni `main`, ni signal, paramètres, protocoles ou résultats
existants. ICT reste en pause. Les règles et les trois précisions de l'utilisateur
sont transcrites dans [protocol.json](protocol.json).

## Autorisation et périmètre

Le checkout a été comparé à `origin/main` après fetch : identiques au commit
`0170810ae290da9005498aad29335f595ff43555`, zéro divergence. La branche
de recherche part de cette base. Les fichiers des dossiers Drive ne sont
ni consultés ni ajoutés ; seules les nouvelles différences dans ce dossier
seront publiées sur la branche de recherche.

La préparation autorise les tests synthétiques et la reproduction déjà publiée
du4janvier au1eravril2021 exclu. Elle interdit tout calcul de performance
sur le bloc d'évaluation, du1eravril au1erjanvier2022 exclu, avant le GO exact.
L'inventaire des trous utilise uniquement les horodatages et masques de présence,
sans rechercher quelles positions seraient exposées.

## Implémentation à examiner

- `path.py` est une copie locale explicite de la fonction d'exécution d'origine.
  Les changements concernent R1/R2 ; frais, change, tick de pénétration et
  priorité stop sont conservés hors trou. `PROVENANCE.json` identifie les sources.
- `engine.py` est une copie locale explicite de `simulate`. R3 ajoute un motif
  de refus sans arrêt ni consommation du quota d'entrée. Aucun patch global
  des modules protégés n'est effectué.
- Aucun prix ni marque de liquidation n'est inventé dans un trou. Les enveloppes
  M1 comportent donc explicitement des intervalles sans valeur.
- S_CONT reprend la logique ordinaire ; si l'échéance est passée dans le trou,
  TIME se fait à la première ouverture disponible, avant les high/low de sa M1.
- S_PESS et S_OPT ferment à l'ouverture de la première minute observée, avec
  conversion à son mid_open. Ce sont des conventions de scénario, pas la preuve
  d'une exécution réelle dans le trou. S_OPT plafonne le **prix** au TP ; le change
  peut faire varier son montant EUR. Ces scénarios ne bornent pas le portefeuille.
- Les journaux R1/R2 contiennent entrée, début/fin du trou, longueur, reprise,
  échéance dans le trou et résolution. Une résolution R1 n'est connue qu'à la
  reprise ; les informations de reprise ne sont pas des signaux utilisables
  avant cette minute.
- La liquidation/comptabilité conserve la convention du moteur sur timestamps :
  TIME et sorties forcées à la reprise ferment à l'ouverture nominale de la M1 ;
  un SL/TP ordinaire intraminute ferme à sa fin. Ce n'est pas un horodatage tick.

## Tests et témoin autorisés

Commande unique de préparation :

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -B \
  research/missing_minute_20261104/prepare.py \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl
```

La préparation lance d'abord les tests synthétiques, sans prix de marché.
Les calculs manuels par unité du test de trou1minute utilisent entrée long2,02,
short1,98, commission aller-retour0,02 et glissement0,01 : à FX2, les nets
attendus sont S_CONT−0,03, S_PESS−0,075 et S_OPT+0,13. Les cas de gap utilisent
explicitement le FX de reprise1,81/2,19 ou2,41/1,59. Les tests du compte couvrent
R3,4 entrées/jour, remise à zéro et pause24h. Aucun cache ne sert à ces tests.

Le marché est ensuite **physiquement tronqué au1eravril exclu** avant le témoin.
Le nouveau code contrôle61 trades pour chaque V03/V04, coût et scénario,
soit12 reproductions. Chaque champ numérique des61 trades est comparé à
la trace publiée avec tolérance1e-8 ; horaires, sens et motifs sont exacts.
Les attendus en précision complète sont ceux des anciens CSV, pas les valeurs
arrondies642,37/504,22/839,28/719,24. Ils ne sont jamais corrigés pour faire passer
le témoin. Tout écart provoque arrêt et rapport, sans gel.

Les résultats de cette étape se trouvent dans `TEST_RESULTS.txt/json`,
`WITNESS.json` et les douze CSV `WITNESS_*_TRADES.csv`. Ce ne sont pas de
nouvelles performances ni une validation.

`KNOWN_GAPS_NO_EXPOSURE.csv` liste toutes les plages manquantes du périmètre,
y compris week-ends et fin du cache, et l'application **hypothétique** de R1/R2/R3.
La cause reste inconnue hors quarantaine documentée. Le résumé mensuel est
dans `GAP_INVENTORY_SUMMARY.json`. Aucune jointure avec les positions n'est faite.

## Gel et GO

Après succès, `FREEZE_BEFORE_RESULTS.json` conserve règles, précisions,
empreintes du cache/code/protocoles/témoin, runtime, calendrier et empreinte des
tirages bootstrap, seuils et sorties prévues. Son SHA256 exact est conservé
dans `FREEZE_BEFORE_RESULTS.sha256` ; il n'est pas le SHA Git du commit.
Les fichiers gelés ne doivent plus changer.

Le seul lanceur d'évaluation est `evaluate_after_go.py`. Ne pas l'exécuter
avant la réponse explicite de l'utilisateur. Après GO seulement, son argument
`--go` doit contenir la phrase entière avec le SHA256 exact. Il vérifie toutes
les empreintes puis crée atomiquement `run_01` avant le moindre calcul.
Si une erreur technique survient, il conserve le dossier et écrit un rapport ;
il ne réessaie pas. Il rejoue12 trajectoires continues distinctes Jan4–Jan1,
puis sépare contrôle/évaluation selon la date d'entrée de chaque trade.

Le bootstrap est calculé exclusivement après le GO, pour S_CONT renforcé,
avec5000 tirages communs V03/V04 et blocs mobiles non circulaires5séances,
séances sans trade incluses, graine20261104. Le générateur PCG64 et le quantile
descriptif `linear` sont explicités pour reproduction. Les p et Holm appliquent
exactement la règle demandée : ce ne sont pas des probabilités de réussite FTMO.
R2 dans une stratégie supprime les p ajustés du lot entier. La priorité des
verdicts suit les précisions reçues. V03 reste la référence, V04 ne la remplace pas.

L'évaluation2021 reste du développement déjà consulté. Aucun verdict n'autorise
un ordre, un déploiement, une nouvelle variante ou une optimisation.

## Écarts et ambiguïtés

Les trois ambiguïtés de bootstrap/Holm/priorité sont résolues par les réponses
de l'utilisateur et transcrites dans le gel. Pas de changement de seuil.
La formule historique descriptive « one attempt per direction » du protocole
V03 diffère du signal réarmé effectif ; ce lot reprend le code réarmé exact,
comme les témoins publiés, sans modifier le protocole historique.
Les conventions de calendrier, générateur et quantile sont détaillées ci-dessus.
Les runs de contrôle préparent le lot ; aucune ligne d'évaluation n'est simulée
avant le GO. Aucun aval nominatif de Loan/Léo/Inspecteur n'est supposé.
