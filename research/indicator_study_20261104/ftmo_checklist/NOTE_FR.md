# Contraintes FTMO et exécution pour toute étude de filtre — 4 novembre 2026

Cette note encadre une future comparaison d'indicateur autour de **V03**, sans
modifier le signal, ses budgets ou les anciens résultats. Aucun backtest ni
nouvel accès HTTP n'a été exécuté pour ce document. Le profil demandé par
l'utilisateur est FTMO **2-Step, 100 000 EUR, Challenge et Verification réunis en
strictement moins de 30 jours calendaires** selon la convention de recherche du
projet. Cette convention n'est pas une clause contractuelle vérifiée.

Mise à jour après réponse directe de l'utilisateur : **MT5 est confirmé** dans
le profil du compte. Le type Standard/Swing reste non renseigné, sans nouvelle
question dans ce cycle. La plateforme demandée est connue ; ses spécifications
contractuelles et celles du symbole ne sont pas encore vérifiées. Les règles
contractuelles actuelles restent inconnues : le 4 novembre à
10:12:10.776116 UTC, la requête officielle a échoué à l'ouverture du tunnel proxy
avec `403 Forbidden`. Aucune page FTMO n'a été reçue ; ce n'est pas un HTTP 403
attribuable au site. Les champs de règles ci-dessous restent `null`. Un filtre
peut être étudié comme hypothèse économique, mais aucun résultat ne peut recevoir
une certification FTMO tant que les clauses et le contrat d'exécution manquent.

## Point de départ à préserver

V03 : range EURUSD 08–09 h Europe/London ; nouvelle cassure M5 après clôture
intérieure réellement observée ; entrées 09–14:30 h, fin exclue ; sortie 16 h ;
stop de l'autre côté exécutable du range plus un tick ; cible prévue 3R ; une
position au maximum ; risque prévu au plus 125 EUR par entrée et 500 EUR cumulés
par séance ; au plus quatre entrées effectivement exécutées ; pause de 24 h
après deux pertes consécutives. Ce sont des règles du modèle de recherche,
aucunement des limites FTMO vérifiées.

Résultats existants seulement : 31 clôtures D45, 54,8 % de gains nets,
+765,35 EUR ; 61 clôtures dans le préfixe annuel connu, 50,8 %,
+642,37 EUR. Les 31 sont incluses dans les 61. Le maximum observé est deux
entrées par jour. Un seul TP atteint sur les 61 clôtures ; 48 sorties horaires,
12 stops. Le gain moyen des gagnants vaut environ 0,90R sur D45 et 0,71R dans
le préfixe, pas 3R. L'année reste inconnue à partir du trou du
1er avril 2021 à 11:40 UTC en position. Tout 2021 a déjà servi au développement.

## Matrice obligatoire

« Rejet » ci-dessous désigne selon le cas le rejet de l'hypothèse économique ou
le rejet d'une **affirmation de validation** ; une donnée manquante n'est pas la
preuve d'une stratégie déficitaire.

| Contrôle | Obligation pour chaque futur essai | Rejet / indétermination |
| --- | --- | --- |
| Produit et clauses | Capturer les conditions officielles datées du 2-Step, la devise, le type Standard/Swing, la plateforme et les clauses par phase. | Règles absentes : conformité `INDETERMINATE`. Ne pas importer les règles 1-Step. |
| Equity continue | Valoriser les positions ouvertes au côté exécutable : bid pour liquider un long, ask pour un short ; convertir en EUR ; suivre frais et swaps selon le contrat et leur date réelle d'imputation. | Le drawdown de balance close et les enveloppes hypothétiques de liquidation V03 ne certifient pas les limites contractuelles. Toute trajectoire active inconnue bloque un PASS. |
| Perte journalière et reset | Paramétrer le seuil, la base de référence, les coûts inclus, l'heure et le fuseau IANA une fois vérifiés ; gérer changements d'heure et positions traversant le reset. | Tous ces paramètres sont `null`. Un budget prévu de 500 EUR/séance Londres ne prouve pas une limite journalière FTMO. |
| Perte maximale | Vérifier seuil, référence, caractère statique/suiveur, moments de mise à jour et définition de la violation. | Champ inconnu : `INDETERMINATE`. Une violation antérieure ne disparaît pas quand le compte revient en gain. |
| Jours qualifiants | Compter les journées selon la définition officielle par phase et son fuseau ; ne pas confondre nombre de trades et nombre de jours. | Minimum et définition `null` ; pas de validation à partir d'un seuil historique supposé. |
| Phases | Vérifier objectif net, conditions de clôture, jours, absence de violation et conditions de passage ; réinitialiser compte/états selon le contrat et une convention explicite pour les pauses. | Pas de réemploi du profit de phase 1, ni des signaux de phase 2 antérieurs à son activation. Délais administratifs inconnus, distincts du délai de trading. |
| Fenêtres <30 jours | Nouvelle tentative à plat et avec balance initiale, fin exclusive `début + 30 jours` ; chauffe strictement passée ; suivre les deux phases dans le même calendrier. | Pas d'assimilation d'une sous-trajectoire historique déjà en cours à un challenge neuf. Les fenêtres chevauchantes sont dépendantes ; garder les fenêtres inconnues au dénominateur. |
| Spread, coûts, glissement | Utiliser bid/ask horodatés et la même tarification pour témoin et filtre ; coûts de base et stress documenté ; aucune double déduction. | Rejeter une amélioration qui disparaît avec des coûts crédibles préfixés, ou suspendre la conclusion si leur source manque. |
| News et maintien | Vérifier restrictions propres à la phase et à Standard/Swing : instruments, événements concernés, horaires, ouverture/clôture/SL/TP, nuits et week-ends. Employer un calendrier historique connu à la décision. | Restrictions et calendrier non vérifiés : aucune conformité démontrée. La sortie prévue à 16 h n'exempte pas des annonces intrajournalières ni d'un incident d'exécution. |
| Stops et contrat | Respecter côté bid/ask, tick, distance minimale, freeze level, volume minimal/pas, valeur du contrat, marge et conversion EUR. Le filtre ne doit pas déplacer le stop range pour fabriquer un meilleur R. | Valeurs du courtier/plateforme `null` ; les valeurs V03 sont seulement des hypothèses de simulation. Si le stop est inexécutable, refuser l'entrée avant son résultat. |
| Risque et fréquence | Garder 125 EUR/entrée, 500 EUR prévus/séance, quatre entrées, une position et la pause 24 h ; mesurer la fréquence réellement exécutable, durée des positions et refus simultanés. | Ne pas relever le risque, empiler les positions ou supprimer la pause pour atteindre une date. Quatre autorisées ne signifie pas quatre exécutées. |
| Causalité de l'indicateur | Valeur calculée sur barres closes disponibles ; source, initialisation, trous et décalage temporel fixés ; aucune future barre ni publication macro révisée. | Toute fuite temporelle invalide l'essai ; absence de valeur = motif inconnu/refus explicite, jamais un zéro économique. |
| Comparaison équitable | Une seule famille/paramétrisation de filtre annoncée, un témoin V03 identique, toutes les variantes conservées ; nouvelles données qualifiées et encore inutilisées pour la validation. | Optimisation rétrospective de 2021 ou gagnant choisi après essais : développement seulement. Une modification du stop, TP ou risque devient une autre hypothèse. |
| Effet sur le parcours | Rejouer à terme la trajectoire complète et les états du compte ; distinguer refus du filtre, position ouverte, pause, limite, données absentes et perte exécutée. | Supprimer des perdants du CSV après coup n'est pas un test causal. Un filtre peut libérer une position ou éviter une pause, donc modifier les entrées ultérieures. |
| Robustesse et décision | Rapporter net en EUR, gains/pertes réalisés, effectif, concentration temporelle, coûts, fréquence, inconnues et faisabilité des deux phases ; évaluer la dépendance par séances/blocs si l'échantillon le permet. | Rejeter un avantage net non reproduit hors développement ou trop dépendant d'un petit nombre d'événements ; échantillon insuffisant = inconclusif. Un win rate plus haut ne suffit pas. |

## Stop minimal : deux contraintes distinctes

La distance minimale **contractuelle** de stop reste `null`. La garde économique
V03 est connue : à l'entrée, avec `d` la distance prix entre entrée et stop,
`s` le spread observé, la condition est
`s + commission aller-retour + 2 × glissement <= 0,30 × d`.
Le code accepte l'égalité et refuse au-delà. Ce n'est pas une clause FTMO.

Aux coûts V03 (commission 0,00005 et glissement 0,00001 par exécution marché),
cela impose `d >= (s + 0,00007) / 0,30`. Exemple purement illustratif pour
un spread de 0,00010, soit 1 pip EURUSD : environ **5,67 pips** de distance
minimale économique. En stress commission ×1,5 et glissement ×2, la borne du
même exemple devient environ **7,17 pips**. Le spread de 1 pip n'est ni un
spread mesuré dans cette étude ni un tarif officiel. L'arrondi au tick doit
rester défavorable/prudent. ATR/RSI/EMA ne rendent pas exécutable un stop qui
viole ces contraintes. Un filtre de volatilité peut exclure un contexte ; il ne
prouve pas la rentabilité des contextes restants.

## Évaluer le rythme sans inventer une probabilité

Une cible de prix 3R n'est pas le R encaissé : sorties horaires, frais, taille
arrondie et change gouvernent le cash. Le test futur doit publier le nombre de
trades réellement nécessaires et disponibles par phase, avec les jours
qualifiants et les limites d'equity vérifiés. L'autorisation de quatre entrées
ne démontre aucune accélération : le témoin observé est limité surtout par les
positions ouvertes et les pauses. Un filtre peut réduire ses opportunités brutes
tout en changeant ces états ; il faut mesurer les deux effets ensemble.

Les bornes arithmétiques sur des objectifs historiques non vérifiés sont
isolées dans `ANNEXE_REPERES_NON_CONFIRMES.md` et son JSON. Elles distinguent
les journées comptées par phase et les journées calendaires uniques : le
traitement du quota lors du passage de phase reste à définir. Ces bornes
optimistes ne sont ni une estimation de probabilité, ni la preuve que le flux
de signaux suffit. Avec les gains réellement observés, on ne peut pas remplacer
toutes les prochaines sorties par +3R.

## Critères avant toute promotion

Un filtre reste **hypothèse à tester** tant que la cause économique est plausible
mais non confirmée. Pour le promouvoir, il faut un avantage net sur un échantillon
qualifié encore inutilisé, des coûts crédibles, un effectif annoncé suffisant,
une fréquence compatible avec le délai aux risques gelés et aucune contrainte
contractuelle violée. Le minimum V03 de 100 clôtures est un seuil de revue du
win rate, pas une preuve automatique de 80 %, de stabilité ou de réussite FTMO.

Une hypothèse est rejetée pour cet objectif si l'avantage hors développement
est économiquement absent, disparaît sous des hypothèses de coûts raisonnables
préannoncées, exige d'accroître le risque, ou si sa fréquence à risque inchangé
rend les cibles vérifiées incompatibles avec le délai. Un résultat peut aussi
rester **inconclusif** : clauses absentes, données actives manquantes, trajectoire
intrabar ambiguë ou échantillon trop petit. Ne pas transformer cette incertitude
en succès ou en échec économique certain.

À relever dans le gel du prochain essai : nom exact du filtre, justification,
formule/source/version, unité et barres d'entrée, traitement de l'initialisation,
paramètre unique ou petit ensemble fixé, effet prévu sur la fréquence, critère
de décision et historique complet des essais. Ne pas choisir une valeur parce
qu'elle aurait évité un perdant déjà connu.

## Provenance et limites documentaires

Sources locales lues : `AGENTS.md`, `simple_forex/protocol_v03.json`,
`simple_forex/README_V03.md`, `simple_forex/runner.py`,
`reports/RAPPORT_FREQUENCE_ET_R_V03.md`,
`research/ftmo_readiness/OBJECTIF_ET_BLOCAGES.md`,
`research/ftmo_readiness/ACCOUNT_PROFILE_TO_COMPLETE.json`, et les notes du cycle
du 4 novembre. La synthèse de ce cycle décrit V01 et ses anciens résultats ;
ils ne remplacent pas le rapport V03 plus récent.

Une chaîne descriptive du protocole V03 conserve l'ancien texte « one attempt
per direction, even if refused ». Pour cette checklist, la sémantique active
retenue est celle du README et du rapport : réarmement après clôture intérieure,
quatre entrées exécutées, refus ne consommant pas le quota. Ce décalage de texte
est signalé sans modifier le protocole ni son identité.

La checklist n'est ni un nouveau profil FTMO confirmé, ni un évaluateur
exécutable, ni une nouvelle validation statistique. Les nombres contractuels
non confirmés sont isolés dans l'annexe ; le JSON principal les laisse `null`.
