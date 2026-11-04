# Cycle de recherche Forex — 4 novembre 2026

## Résultat du cycle

Trois travaux indépendants ont été menés en parallèle : données, sources FTMO et
littérature. Une quatrième analyse rapproche les résultats déjà calculés. Aucun
nouveau backtest, aucune optimisation et aucun changement de risque ou de signal.
Le fichier actif reste la stratégie London Range de 40 lignes, sans indicateur.

Le cycle s'arrête sur des prérequis externes identifiés, pas sur un compteur de
crédits. Le solde d'abonnement n'est pas accessible et aucune boucle permanente
en arrière-plan n'a été mise en place. Les résultats sont enregistrés pour ne
pas refaire les mêmes recherches sans information nouvelle.

## 1. Le gain initial ne s'est pas maintenu dans les observations suivantes

Les CSV établissent que la fenêtre de 45 jours est exactement incluse dans les
49 clôtures connues du calcul annuel. Le rapprochement ne mélange pas deux
stratégies ou deux simulations indépendantes.

| Ensemble observé, coûts de base | Trades clos | Net établi | R cash moyen |
| --- | ---: | ---: | ---: |
| 04/01–18/02/2021, fin exclue | 27 | +670,63 € | +0,100R |
| Du 18 février au dernier trade clos le 31 mars | 22 | −917,02 € | −0,167R |
| Préfixe connu combiné | 49 | −246,39 € | −0,020R |

Le scénario de coûts augmentés donne respectivement +603,82 €, −986,44 € et
−382,62 €. Le total de l'année reste inconnu à cause d'une position non résolue.

Les résultats observés après la fenêtre courte suffisent à réfuter l'affirmation
« les 45 jours positifs démontrent une rentabilité stable ». Ils ne permettent
pas d'identifier à eux seuls une cause économique, un régime ou le bon nouveau
paramètre. Le gain moyen des 20 gagnants du préfixe vaut environ 0,877R : un
objectif prévu à 2R n'est pas la moyenne réellement encaissée.

Les 61 sous-trajectoires de 30 jours entièrement contenues avant le jour du trou
ont aussi été décrites, sans simulation supplémentaire. La meilleure totalise
+1 653,71 € sur les clôtures et la pire −1 227,04 €. Elles se chevauchent, héritent
des pauses de la trajectoire d'origine et ne sont pas des challenges remis à
zéro. Ces nombres ne mesurent aucune probabilité de réussite FTMO et ne
constituent pas une sélection d'une « meilleure période » à conserver.

Pièces : `performance/PERFORMANCE_FACTS.json`,
`performance/OBSERVED_30D_SUBTRAJECTORIES.csv` et le script
`performance/analyse_existing.py`, qui lit seulement les journaux existants.

## 2. L'ancien cache ne répare pas la minute manquante

La minute du 1er avril 2021 à 11:40 UTC, soit 13:40 à Paris, manque dans les
deux caches présents. Les 150 269 lignes et 14 colonnes de l'ancien cache sont
exactement celles du sous-ensemble correspondant du cache annuel. Il ne s'agit
donc pas d'une deuxième source indépendante fournissant une cotation de secours.

Les identités, les types désérialisés et les archives locales ont été contrôlés.
La lecture s'est faite par une liste explicite de types autorisés ; aucun pickle
libre n'a été exécuté. Aucun prix n'a été rempli, aucune série mélangée et aucun
fichier de données modifié.

Le fichier brut utile est identifié :

- nom : **EURUSD_202104.zip** ;
- taille documentée : **7 463 785 octets** ;
- SHA256 : `db93091c6e0ebba8fe9a5cef8df50b110962a5f154bd78900659ff7c58e91702` ;
- [ancien lien Drive documenté](https://drive.google.com/file/d/19DOLFPcs1wrtmQQM8LQyHPutOTOgaLhB/view?usp=drivesdk), non récupéré dans ce cycle.

L'archive et son paquet de ticks distinct ne sont pas présents dans les fichiers
et ZIP locaux inspectés. Il faut examiner les ticks bruts et leur rapport de
qualité pour distinguer absence dans le fichier fournisseur et perte de collecte.
Une absence de ticks dans un fichier ne prouverait toujours pas une absence de
cotations sur tout le marché. Le fichier brut peut éclairer le trou ; sa seule
obtention ne garantit pas qu'un prix manquant pourra être reconstitué.

Pièces : `data_quality/NOTE_FR.md`, `LOCAL_SOURCE_AUDIT.json` et
`inspect_local_sources.py`. Les fichiers contiennent la fenêtre d'horloge source
à inspecter, les empreintes et les limites exactes de l'inventaire.

## 3. La littérature lue ne démontre pas l'avantage de notre protocole

Sept documents de deux familles d'auteurs ont été consultés : pysystemtrade de
Rob Carver et la documentation statistique arch. Deux nouveaux documents ont
été récupérés sur leurs dépôts officiels, avec proxy et vérification TLS.

L'exemple breakout de Carver produit un forecast lissé et décrit le lookback en
jours. Il ne spécifie pas notre plage Londres, nos clôtures M5 ou notre TP à 2R.
Les documents arch expliquent les comparaisons multiples et les hypothèses des
bootstraps par blocs. Ils n'autorisent pas à transformer 49 trades tronqués en
probabilité de passage ni à ignorer la dépendance créée par les séances/pauses.

Ce sont des apports méthodologiques vérifiés, pas sept études empiriques
indépendantes. Cette lecture ciblée n'a trouvé aucune validation directe de
notre règle exacte ; elle ne démontre pas qu'aucune étude pertinente n'existe.
Les articles financiers primaires encore inaccessibles ne sont pas présentés
comme lus.

Conséquences pratiques : coûts monétaires nets, ordre temporel conservé,
incertitudes explicites, maintien d'une règle figée avant le prochain
échantillon indépendant. Aucun nouvel indicateur ni choix de seuil n'en découle.

Pièces : `literature/NOTE_PREUVES_ET_LIMITES.md`, `SOURCE_REGISTER.json` et
les empreintes des copies effectivement lues.

## 4. FTMO reste un profil utilisateur confirmé, avec règles non vérifiées

Le projet reste FTMO 2-Step, 100 000 € en euros, les deux phases en moins d'un
mois si possible. La nouvelle lecture officielle du 4 novembre est refusée à
l'ouverture du tunnel proxy ; aucune page FTMO n'a été reçue. Ce refus ne doit
pas être attribué au site lui-même. Les objectifs, pertes, jours et fuseaux
contractuels actuels ne sont donc pas certifiés.

Le brouillon réseau contient déjà FTMO et les domaines financiers préparés.
Il faut revoir/enregistrer ces réglages puis publier l'environnement pour les
activer. Sans changement d'accès, répéter la même requête ne vérifie rien de plus.
Un document contractuel officiel daté fourni directement permettrait aussi
d'étudier ses clauses, en conservant leur date et leur périmètre exact.

Pièces : `ftmo_sources/NOTE_FTMO_FR.md`, `FETCH_RESULT.json` et
`PROFILE_VERIFICATION_STATUS.json`. Aucun profil officiel inventé, aucune règle
1-Step transposée au 2-Step et aucun statut PASS attribué.

## Prochain cycle utile

1. Obtenir l'archive brute d'avril identifiée ou une autre preuve de données de
   même provenance, vérifier les empreintes et inspecter la minute concernée.
2. Activer l'accès officiel ou obtenir les conditions FTMO datées pour compléter
   les définitions d'equity, limites, reset, phases et jours qualifiants.
3. Réexaminer la faisabilité des deux phases avec ces contraintes vérifiées,
   sans augmenter le risque pour faire apparaître un délai favorable.
4. Après qualification des données, réserver une période encore inutilisée et
   tester une seule règle figée. Les cinq hypothèses H4/M30 déjà essayées et la
   nouvelle cassure Londres restent dans l'historique des essais.

Tant que ces prérequis ne changent pas, les mêmes simulations et ajustements sur
2021 n'apporteraient pas la validation indépendante recherchée.
