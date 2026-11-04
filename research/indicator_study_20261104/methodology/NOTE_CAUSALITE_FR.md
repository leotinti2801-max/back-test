# Proposition d'audit causal des niveaux V03 — 4 novembre 2026

Cette note définit un audit descriptif des **61 clôtures du préfixe V03 de base**.
Elle n'ajoute aucun filtre, ne modifie aucune entrée et ne lance aucune simulation.
La position ouverte le 1er avril à 08:25 UTC, inconnue à 11:40, est hors de ces
61 clôtures ; elle doit rester dans un registre séparé, sans résultat imputé.
Les 31 clôtures D45 sont incluses dans les 61, pas un échantillon supplémentaire.
Le schéma proposé est `LEVEL_AUDIT_SCHEMA_PROPOSAL.json` dans ce dossier.

## Jour Forex : convention explicite, puis complétude

Proposition unique : jour étiqueté par sa date de fin, de **17:00 la veille à
17:00 America/New_York**, intervalle gauche inclus/droite exclue. Les dates de
fin éligibles sont lundi à vendredi ; ce calendrier est une convention d'étude,
pas une preuve de fermeture du marché les autres jours. Construire les bornes
avec le fuseau IANA, puis convertir en UTC. Ne pas remplacer par 22h UTC toute
l'année : 17h New York vaut 22h UTC en hiver et 21h UTC en été.
Le changement d'heure du jour de référence est distinct du décalage EST fixe
UTC−5 déclaré par la préparation HistData et de l'heure d'entrée Londres.

À l'entrée `t`, choisir le dernier jour éligible dont la fin est `<= t`.
Le lundi matin, cela donne normalement le jour finissant le vendredi à17h.
Ne jamais choisir automatiquement le dernier jour **ayant des quotes** : un
jour férié absent reste inconnu, sans repli silencieux vers un jour plus ancien.
Les hauts/bas du jour en cours ne sont pas des niveaux journaliers déjà clos.

Une journée n'est complète que si toutes ses minutes attendues sont présentes
et hors quarantaine. Calculer le nombre attendu à partir des bornes UTC ; ne
pas compresser l'index ni imputer les trous. Faute de calendrier de fermeture
certifié, une absence de ligne reste une absence de donnée, pas une fermeture.
Les niveaux exacts PDH/PDL sont `UNKNOWN_INPUT_GAP` si une minute manque.
Journaliser bornes, nombre attendu/observé/manquant et première minute absente.

**Contrôle de faisabilité réalisé, sans backtest :** les61 entrées du4janvier
au31mars2021 correspondent à54 journées précédentes distinctes ; **0/54** ont
leurs1440 minutes, donc PDH/PDL exacts inconnus pour61/61 sous cette convention.
Avant le5janvier : `[2021-01-03 22:00Z, 2021-01-04 22:00Z)` contient1435/1440
minutes. Avant le4janvier : le jour finissant le1erjanvier contient0/1440.
Ce constat ne justifie pas de modifier le découpage après lecture des résultats.

Une vue complémentaire peut conserver les extrema **observés** comme bornes
partielles : `vrai_high >= high_observé`, `vrai_low <= low_observé`. Les nommer
`KNOWN_PARTIAL_BOUND_ONLY`, pas PDH/PDL certifiés ; ne pas transformer leur
absence de niveau entre entrée et TP en « aucun obstacle ». Leur existence peut
décrire des prix réellement observés, sans certifier les extrema de la journée.

## Pivots H1 : confirmation sans information future

Ancrer les H1 en UTC, `[h,h+1h)`, disponibles à leur clôture. Chaque H1 nécessite
60/60 M1, indépendamment du nombre de ticks dans une minute. Un pivot haut
strict a un high **mid** central supérieur aux quatre high mid des deux H1 de
gauche et deux de droite ; un pivot bas est strictement inférieur aux quatre low.
Une égalité n'est pas un pivot. Les cinq H1 sont consécutives sur la grille,
complètes et sans quarantaine. Ne jamais utiliser les cinq dernières H1 présentes
en sautant un trou ou un week-end.

`pivot_time = clôture du centre`, mais `known_at = clôture de la deuxième H1 de
droite`. À l'entrée `t`, seul `known_at <= t` est admissible. Exemple : centre
`[08h,09h)`, confirmation par `[09h,10h)` et `[10h,11h)` : connu à11h, jamais à09h.
Le calcul peut employer `make_bars(market,60,'H1')` puis `find_pivots` déjà présents
dans `vendor/h4m30_v01/h4m30_data.py:207` et`:252`, à condition de garder les SHA
et les règles60/60. Leur réutilisation comme outils d'agrégation ne réactive pas
la stratégie H4/M30 archivée.

Ne pas fabriquer un niveau avec le high/low/close de la M1 d'entrée ni une H1
en cours. À la même heure, traiter la clôture de la barre avant la quote d'ouverture
effectivement utilisée ; conserver son `first_ts` pour rendre cet ordre explicite.
Un pivot confirmé reste un fait historique. Son statut d'« intact/non franchi » est
une autre propriété : observer les minutes de `[known_at,t)` seulement. Un trou
dans cet intervalle rend ce statut inconnu, sans effacer l'existence du pivot.
Ne pas exclure un niveau parce qu'il sera franchi après l'entrée. Éviter d'ajouter
une durée de validité ou une tolérance de proximité sélectionnée sur les61 résultats.

## Géométrie de l'obstacle, provenance et interprétation

Conserver la convention mid du niveau structurel. Pour une comparaison aux TP
du moteur, ajouter une référence de même côté exécutable : high bid du centre
pour une résistance de pivot, low ask du centre pour un support ; extrema bid/ask
du jour pour les niveaux journaliers. Ce sont des références de barres définies,
pas une conversion mid par un spread futur ou une promesse de fill.
Comparer un achat à la quote bid d'ouverture observée et au TP bid du trade ;
une vente à la quote ask et au TP ask. Tag géométrique :
`direction*(niveau_exec-quote_sortie_open)>0` et
`direction*(TP-niveau_exec)>=0`. Exprimer les distances en prix/pips ; tout ratioR
doit préciser son dénominateur et ne constitue pas un gain EUR réalisé.

Produire un inventaire des niveaux puis une jointure par entrée. Séparer les
statuts : niveau exact connu, borne partielle, formation inconnue, confirmation
postérieure, état depuis confirmation inconnu. « Aucun niveau connu trouvé »
n'est pas « aucun obstacle existe » si une famille de niveaux est inconnue.
S'il faut choisir le plus proche, appliquer le même ordre déterministe à tous
les niveaux éligibles, jamais selon le résultat du trade. Conserver les candidats
exclus et leurs raisons ; déclarer le lookback et toute règle d'activation avant
de calculer une association avec le PnL.

Un obstacle historique avant le TP3R peut motiver une **hypothèse**. Il ne prouve
ni que le trade aurait perdu ni qu'un filtre aurait amélioré le système. Le filtre
peut retirer des gagnants, réduire la fréquence, et changer les entrées suivantes
via les positions et pauses. L'association sur61 clôtures déjà sélectionnées,
censurées au trou d'avril et issues de2021 déjà consulté n'est pas une validation
hors échantillon. Ne pas annoncer80%, passageFTMO ou PnL contrefactuel.

## Tests causaux à exiger avant l'audit calculé

1. Modifier tous les high/low/close à partir de la M1 d'entrée, en gardant sa quote
   open : aucun niveau connu ni tag d'entrée ne doit changer. Tronquer la série
   exactement à l'entrée doit reproduire les mêmes niveaux disponibles.
2. Pivot dont la deuxième H1 droite finit après l'entrée : exclu ; à sa clôture :
   admissible. Changer cette H1 future ne doit jamais modifier une entrée antérieure.
3. Retirer une M1 dans chacune des cinq H1 : pivot non certifié ; ne pas rapprocher
   les H1 restantes. Cas d'égalité des extrema : aucun pivot strict.
4. Retirer une M1 du jour précédent : PDH/PDL inconnus, bornes partielles conservées
   sous un autre statut ; ne pas omettre ce trade de la jointure. Jour entier absent
   et jour hors bornes du cache : distinguer les raisons.
5. Retirer une M1 après confirmation mais avant entrée : existence du pivot stable,
   état « non franchi » inconnu. Ajouter un franchissement après entrée : état
   historique à l'entrée inchangé.
6. Vérifier New York autour des14mars/7novembre2021 et Londres autour
   des28mars/31octobre ; lundi, jour férié absent et31décembre aux bornes du cache.
   Ne pas appliquer un offset Londres au jour New York.
7. Cas achat/vente avec spread non nul : conventions bid/ask cohérentes ; obstacle
   derrière la quote actuelle exclu, exactement au TP inclus selon le choix déclaré.
8. Les61 identifiants d'entrée restent présents, les CSV de trades restent identiques
   à l'octet et tous les PnL d'origine inchangés. Tester séparément l'entrée inconnue
   du1eravril ; ne pas l'ajouter comme perte ou gagnant aux61.

## Réconciliation du protocole V03, sans mutation

`simple_forex/protocol_v03.json:12` conserve le texte V01 « one attempt per direction ».
Pourtant`:55` indique `signal_source='rearmed'` et `runner.py:184-185` sélectionne
`strategy_rearmed.signals`. Ce dernier réarme après une clôture intérieure
(`strategy_rearmed.py:24-31`) et ne limite pas chaque sens à un seul essai.
`previous=0` à09h (`:19`) autorise aussi la première clôture extérieure après le
range ; elle ne requiert pas une autre clôture M5 intérieure après09h. Les signaux
ultérieurs exigent un retour intérieur observé ; un saut direct extérieur-haut
vers extérieur-bas ne suffit pas à réarmer. Il n'y a pas de retest V02.
Le README omet cette nuance d'initialisation ; le gel et le code définissent
la population réellement produite. Documenter ces écarts sans réécrire les gels.

Identités lues et concordantes avec `simple_rearmed_v03_01/FREEZE_BEFORE_RESULTS.json` :

- signal réarmé : `065e0c652d741b06bf0c6627d73031d63da6e726cdc599da2b6abef963c457c7` ;
- protocoleV03 : `ff6b2a81cb338d0667b8c1b0f74406f617e0f12114093f81656cdecc44652f20` ;
- runner : `a9095487a20262431a3e14d0b713800bfe8cb7f1fb004ace12cc61c89bf21bb6` ;
- agrégateur/pivots : `be020d78225a55068677617dc4a777860e73a3ceec5287ccb3f0dee93cb613eb` ;
- CSV annuel base,61 lignes : `f91c4ebfb40a956a952a34a746236dd00ac84c6346f32f2a72c9f0fe2daf61a9` ;
- cache : `9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2`.

Le cache lu par `backtest_bot.data.load_cache` a été vérifié taille/SHA avant
désérialisation par whitelist. Ses401000 lignes vont du1erdécembre2020 à05hUTC
au31décembre2021 à21:59UTC ; le warmup est utilisable avec sa provenance, sans
inventer les minutes précédant son début. La grille va de00hUTC le1erdécembre2020
au1erjanvier2022 exclu ; les cases vides ne sont pas des observations.
La quarantaine `[2021-11-01 00h,01h UTC)` reste absente ; elle affecterait toute
formation la recouvrant. Le trou1eravril11:40 n'est pas réparé. Les résultats
ci-dessus concernent la couverture d'entrée, pas un nouveau calcul de stratégie.
