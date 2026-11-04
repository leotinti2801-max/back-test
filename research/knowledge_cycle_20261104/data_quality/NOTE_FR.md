# Vérification locale de la minute manquante — 4 novembre 2026

La minute du **1er avril 2021 à 11:40 UTC** manque dans les deux caches vérifiés.
Le fichier antérieur contient 150,269 lignes du 2021-01-03 22:00:00+00:00 au 2021-05-31 04:59:00+00:00.
Ses 14 colonnes et son index sont exactement identiques au sous-ensemble du cache annuel.
Ce contrôle a été reproduit ici : il ne repose pas uniquement sur l'ancien audit.
Il n'apporte donc aucune cotation supplémentaire pour résoudre l'exposition de London Range V01.

SHA256 antérieur : `0cad4b151c47e05376e170d0b78351229769e9e86816f60233080fabdf3251de` (18033788 octets).
SHA256 annuel et copie active : `9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2` (48121320 octets).
Les identités correspondent au manifeste de preuves fourni. Le manifeste, les audits et
le script historique de préparation sont identifiés dans `LOCAL_SOURCE_AUDIT.json`.
Une concordance de SHA prouve la cohérence des pièces, pas leur authenticité fournisseur.
La lecture a employé une whitelist explicite des globals pandas/numpy/datetime ; aucun
`pickle.load` libre ni ancien script de préparation n'a été exécuté.

Les caches contiennent 11:39 puis 11:41, avec les mêmes valeurs dans les deux fichiers.
La première cotation enregistrée pour 11:41 est à 11:41:05.289 UTC. Le détail des quatre
barres observées de 11:38 à 11:42 est conservé dans le JSON. Une barre M1 n'identifie
pas la dernière cotation réelle de la minute précédente, ni le parcours entre deux barres.

L'inventaire récursif de `/workspace` et `/tmp` et les répertoires centraux de
6 ZIP locaux n'ont pas fourni d'archive de ticks d'avril.
Le README des preuves annonce les ticks dans un paquet distinct
`ARCHIVES_TICKS_BRUTES_202012_2021.zip`, absent du périmètre local inspecté.
Le CSV de quarantaine d'octobre concerne une heure d'octobre : il ne couvre pas avril.
Les ZIP de livraison contiennent des caches ou résultats, sans ticks supplémentaires identifiés.

L'archive requise est `EURUSD_202104.zip`, 7463785 octets,
SHA256 `db93091c6e0ebba8fe9a5cef8df50b110962a5f154bd78900659ff7c58e91702` ; le CSV interne annoncé a le SHA256
`4e2149657097b09467c599705266a6ea47e5747c94e72473d8c835db161bb445`. L'ancien inventaire indique sa présence sur Drive :
https://drive.google.com/file/d/19DOLFPcs1wrtmQQM8LQyHPutOTOgaLhB/view?usp=drivesdk
Cette localisation est une indication documentaire ; aucun accès Drive n'a été effectué ici.
Le fuseau déclaré par la préparation est EST fixe UTC−5. Il faut donc examiner les
ticks source du 1er avril entre 06:39 et 06:42, notamment `[06:40,06:41)`.

Les audits enregistrent zéro ligne invalide supprimée et aucune interpolation, mais
sans l'archive, ces affirmations ne peuvent pas être revérifiées à cette minute.
**Absence locale du fichier brut** : démontrée dans le périmètre inspecté.
**Absence de cotation dans le fichier source** : non vérifiable sans ce fichier.
**Absence de cotation sur le marché ou perte lors de collecte/export** : non démontrée.
Même un fichier source sans ticks ne suffirait pas à prouver un marché sans cotations.
Il faut le fichier exact, son rapport de gaps et, si nécessaire, une source indépendante
avec conventions de prix et de temps documentées, sans raccord implicite de flux.

Le trou reste non résolu. Aucun prix n'a été rempli, aucune source mélangée,
aucun cache modifié et aucune simulation lancée. Le total annuel inconnu doit le rester.

Reproduction : depuis le dépôt, exécuter
`PYTHONDONTWRITEBYTECODE=1 python research/knowledge_cycle_20261104/data_quality/inspect_local_sources.py --output-directory research/knowledge_cycle_20261104/data_quality/reproduction_02`.
Choisir un répertoire de sortie neuf ; les audits existants ne sont pas écrasés.
L'inventaire reflétera les fichiers présents au moment de chaque reproduction.
