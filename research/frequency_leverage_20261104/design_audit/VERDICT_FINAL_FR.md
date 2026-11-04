# Verdict indépendant sur run_01 — 4 novembre2026

**PASS : aucune anomalie matérielle trouvée dans les72 cellules contrôlées.**
Le plan exécuté comporte **neuf bras**, quatre périodes et deux scénarios de coûts.
La note de conception àhuit bras était intermédiaire ; le neuvième bras
`EXTENDED_HOLD60_CAP8` est présent dans le plan final et le gel vérifiés.

L'audit a vérifié **363 fichiers de résultats,21 identités de sources et3014 lignes
de trades clos corrélées**. Les empreintes correspondent au manifeste et au gel ;
le noyau historique et le protocole V03 sont inchangés. Les pertes, soldes et PnL
existants ont été rapprochés, sans nouvel ordre ni appel à un simulateur.

Contrôles réussis sur tous les bras/périodes/coûts :

- risque prévu par trade ≤125€ ou62,50€, cumul prévu journalier ≤500€, quota4/8 ;
- aucune position chevauchante ; pause24h depuis la deuxième clôture perdante,
  expiration de la pause et compteurs journaliers suivis depuis les événements ;
- confirmations aux clôtures M5/M1, range08–09h déjà connu, réarmement réellement
  intérieur et plages Londres avec conversionDST ;
- durée maximale60min et sortie de session respectées, quote présente sur les
  expositions closes et à leur fill terminal ; aucun total inconnu imputé ;
- entrées, stop de range, cible3R, quantités arrondies, plafonds notionnels,
  commissions, glissement et conversion FX des fills recomposés depuis le cache ;
  **écart maximal de PnL :0€** ;
- réinitialisation du portefeuille à100000€ au début de chaque cellule ;
- clone `FunctionType` avec code/defaults identiques, dictionnaire de globals
  distinct, seule factory `parameters` remplacée ; fonction originale inchangée.

Le témoin Q1 reproduit à l'octet les CSV de trades **et décisions** du témoin déjà
gelé. Levier30 et100 reproduisent à l'octet trades, décisions, enveloppes et pertes
du témoin dans chacune des huit combinaisons période/coûts. Les tables de sizing
diffèrent normalement par leur plafond de levier : le levier n'améliore ici aucun
trade, car cette contrainte ne borne pas les tailles exécutées.

## Résultats Q1 déjà produits, simplement rapprochés

| Bras | Clôtures base/stress | Net base€ | Net stress€ | Maximum entrées/jour base/stress |
|---|---:|---:|---:|---:|
| V03 |61/61|642,37|504,22|2/2|
| LEVERAGE30 |61/61|642,37|504,22|2/2|
| LEVERAGE100 |61/61|642,37|504,22|2/2|
| EXTENDED |61/60|−44,46|92,29|2/2|
| HOLD60 |94/94|543,20|327,72|3/3|
| EXTENDED_HOLD60 |108/108|685,81|444,43|4/4|
| EXTENDED_HOLD60_CAP8 |108/108|685,81|444,43|4/4|
| EXTENDED_HOLD60_8SMALL |108/108|339,44|221,42|4/4|
| EXTENDED_HOLD60_8SMALL_M1 |117/115|138,53|33,39|4/4|

La fréquence augmente effectivement avec la durée60min et, davantage, avec M1.
Le plafond8 n'est pas huit entrées réalisées. Le petit gain de
`EXTENDED_HOLD60` sur le témoin sous coûts de base disparaît sous stress : le
critère préannoncé d'amélioration dans lesdeux coûts n'est pas rempli.
Ce constat ne justifie pas une promotion. Les différences entre coûts peuvent
modifier les sorties et les pauses : les trajectoires ne sont pas nécessairement
identiques. L'analyse détaillée du cas EXTENDED est un travail séparé.

## Périmètre et reproduction

Les72 cellules observées n'ont rencontré aucune exposition inconnue ; cela ne
certifie pas la complétude de tout le marché. La branche d'arrêt sur exposition
inconnue du moteur gelé reste présente et conserve un total `null`. Les six tests
sources ont été relus, pas relancés par cet audit. Les fills **consignés** sont
vérifiés ; aucun parcours stop/TP contrefactuel ni ordre réel des ticks n'est rejoué.
L'equity M1 demeure une enveloppe de modèle, sans conformité FTMO démontrée.

Les fenêtres28jours sont incluses dans Q1 et utilisent des comptes neufs : elles
ne sont ni indépendantes ni une simulation des deux phases FTMO.2021 était déjà
consulté. Aucun résultat annuel complet, taux80% ou passage enmoins d'un mois
n'est établi. Aucun fichier financier ni source active n'a été modifié.

Pièces : `FINAL_AUDIT.json` et `audit_recorded_run.py` dans ce dossier.
Reproduction, en choisissant un fichier neuf :

```sh
PYTHONDONTWRITEBYTECODE=1 python research/frequency_leverage_20261104/design_audit/audit_recorded_run.py --output research/frequency_leverage_20261104/design_audit/FINAL_AUDIT_REPRODUCTION.json
```

Ce script ne crée aucun signal de trading ni chemin d'exécution : il contrôle les
CSV existants et les quotes sources, avec lecture du cache après vérification de
taille/SHA et désérialisation par whitelist.
