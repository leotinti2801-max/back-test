# Revue méthodologique ICT/SMC — avant calcul historique

Cette note examine la définition proposée par le parent : balayage du range
Londres08–09h, MSS, FVG puis retour observé. Aucun cache n'est chargé, aucune
simulation ni requête HTTP n'est lancée et aucun code de trading n'est modifié.
Les remarques ci-dessous sont des règles à figer dans le plan et des critères
de revue ; elles ne constituent pas une vérification du futur code.

Les termes ICT/SMC n'ont pas une définition unique. Ce test doit être présenté
comme **une formalisation particulière**, pas comme l'ensemble de la méthode
ICT ni une preuve d'intervention institutionnelle. Un dessin rétrospectif d'un
order block ne prouve pas des ordres présents ou exécutables à cet endroit.

## Chronologie minimale

Le range08–09h Europe/London requiert toutes sesM1. Ses bornes deviennent
connues à09h, avec le fuseau IANA et ses changements d'heure. Le haut et le bas
mid servent à décrire le balayage ; leurs équivalents bid/ask doivent être
conservés pour les stops et la cible exécutable. Un range incomplet ne devient
pas une séance sans signal : il est inconnu.

Le balayage est une M5 complète dont le high/low dépasse d'au moins un tick
une borne et dont la clôture revient strictement dans le range. Si les deux
bornes sont balayées par la mêmeM5, rejeter comme configuration ambiguë sans
choisir ensuite la direction gagnante. Une clôture égale à la borne n'est pas
strictement intérieure. Un franchissement par gap peut satisfaire cette règle
de prix ; il ne démontre pas qu'une séquence de stop orders a été observée.

Le MSS intervient sur une **M5 ultérieure** au balayage. Pour un achat, le
pivot hautM5 de référence est déjà confirmé à l'heure du balayage ; pour une
vente, c'est le pivot bas. Un pivot strict2gauche/2droite n'est connu qu'à la
clôture de sa seconde barre de droite, jamais à la barre centrale. Geler son
identité et son prix lors du balayage : un pivot confirmé plus tard ne peut pas
remplacer celui qui manquait pour rendre rétroactivement le setup admissible.

Le déplacement doit comparer le corps de la M5 MSS à l'ATR14 **de la M5
précédente**. Cet ATR utilise un segment consécutif de barres complètes, avec
la version TA-Lib et son initialisation fixées. Aucun ATR courant, aucune
compression des heures manquantes. Le corps doit être directionnel et la
clôture doit effectivement franchir le pivot dans ce sens.

Le FVG est constitué par troisM5 complètes, la dernière étant celle du MSS :
haussier si `low[s] > high[s-2]`, baissier si `high[s] < low[s-2]`, avec largeur
minimale d'un tick. Il est connu à la clôture de`s`, pas au début du déplacement.
Ses bornes sont figées. Exiger ensuite une **nouvelle** clôtureM5 dans le FVG,
parmi les six prochaines barres complètes, avant14h30. La M5 de formation ne
peut pas servir en même temps de retour après formation.

## Invalidation, expiration et tentatives

Le stop est l'extrême exécutable de la M5 balayage, avec un tick de marge :
`bid_low-tick` pour un achat et `ask_high+tick` pour une vente. Utiliser seulement
l'extrême mid peut rendre le stop incohérent avec la liquidation réelle.
Le stop initial doit rester figé ; l'élargir sur les nouvelles mèches pour
conserver un setup serait une autre hypothèse de risque.

De la fin du balayage jusqu'à l'entrée, tout toucher du stop initial invalide
le setup. Dans une M5 qui touche le stop et clôture dans le FVG, l'invalidation
doit précéder l'entrée : l'ordre des ticks ne permet pas d'affirmer que le
retour était exploitable avant l'invalidation. Appliquer la même priorité
avant une confirmation MSS. Les minutes du balayage lui-même ne doivent pas
invalider un stop défini à partir de leur extrême plus marge.

Une minute manquante dans la formation ou l'attente rend l'état inconnu. Ne
pas sauter le trou, rapprocher des bougies non consécutives, ou reprendre le
setup parce qu'un futur retour semble exploitable. Une absence pendant une
position ouverte doit toujours interrompre la branche de portefeuille avec
total inconnu et coûts connus conservés ; annuler seulement les nouveaux
signaux ne résout pas l'exposition déjà ouverte.

Le plan doit aussi annoncer la durée maximale d'attente du MSS et la politique
face à un nouveau balayage : conserver le premier ou remplacer par le dernier,
sans sélection selon le résultat. L'ordre de traitement des événements d'une
mêmeM5 doit être déterministe. Une seule tentative est recommandée par setup :
le premier retour valide consomme l'occasion même si le compte ou la quote
refuse l'entrée. Plusieurs retours ne deviennent pas plusieurs essais jusqu'à
trouver celui qui aurait gagné.

## Entrée, cible et comptabilité

Le retour M5 n'est pas un fill limite au milieu du FVG. L'entrée proposée est
la première quoteM1 suivante, avec `first_ts` contrôlé, et son mid_open doit
encore appartenir à la zone. Si l'ouverture saute hors FVG, refuser au prix
observable, sans fabriquer une exécution au prix de la clôture précédente.
L'achat paie ask plus glissement, la vente reçoit bid moins glissement.

La cible opposée du range doit utiliser le même côté de liquidation : haut
bid pour un achat, bas ask pour une vente. C'est un niveau historique connu,
pas la preuve qu'une liquidité intacte existe encore si le prix l'a déjà
revisité. Ne pas déplacer la cible vers un futur haut ou bas après entrée.
Vérifier côté du stop/cible, taille minimale/pas, levier, friction maximale et
`gain_net_quote / risque_net_quote >= 2`, avec la même définition de frais et
de glissement que le moteur. Un ratio2prix n'est pas exactement2R cashEUR
réalisés à cause du change de chaque flux.

Les contraintes du portefeuille doivent rester actives : une position,
quatre entrées exécutées maximum, risque prévu125EUR/trade et500EUR/jour,
pause24h après deux pertes nettes, sortie16h Londres. Les refus ne consomment
pas le quota d'entrées ; le refus du setup doit néanmoins rester observable.
Le budget quotidien prévu n'est pas une certification FTMO d'equity.

Le moteur garde le stop prioritaire si stop et cible sont atteignables dans
la mêmeM1, en signalant l'ambiguïté. À l'échéance16h, utiliser la quote
d'ouverture de cette minute avant son high/low. Conserver commission et
glissement une seule fois dans le résultat net.

## Annotations et probabilités

L'order block peut être annoté comme la dernière bougie strictement opposée
parmi les cinqM5 complètes précédant la M5 MSS. Il faut préciser si la zone
utilise les mèches ou le corps ; les bornes high/lowmid sont une convention
reproductible. L'annotation devient disponible au MSS, même si la bougie
source est plus ancienne. Aucune absence d'OB ne doit bloquer un trade si le
plan dit explicitement « annotation seulement ». Tous les overlays doivent
indiquer leur heure de disponibilité ; une zone confirmée après l'entrée ne
peut pas apparaître comme contexte déjà connu à cette entrée.

Une confluence de dessins n'est pas une probabilité numérique calibrée. Les
observations servant au sizing ne peuvent inclure que des trades déjà clos
à l'entrée, avec leur fréquence et dépendance explicites. Tout2021 est déjà
du développement ; les mêmes observations ne peuvent pas servir à choisir
un indicateur puis à certifier sa probabilité sur un prétendu échantillon neuf.
Le risque adaptatif doit donc rester désactivé pour cette première évaluation.

Publier le nombre de setups à chaque étape et leurs sorties : pivot absent,
ATR inconnu, absence MSS/FVG, invalidation stop, expiration, trou, retour
refusé, position occupée, pause, frais/ratio, entrée et perte exécutée. Zéro
trade produit un taux de réussite `null`, pas une stratégie sans pertes.
Le trimestre commun et un éventuel préfixe annuel arrêté doivent être
distingués. L'annuel partiel n'est pas comparable à un total trimestriel
résolu comme s'ils couvraient la même période.

Les tests recommandés sont dans `TEST_CASES_PROPOSAL.json`. Ils sont proposés,
non exécutés par cette note. Les règles actuellement vérifiées de FTMO ne
sont pas complétées ici et aucun verdict de passage n'est produit.
