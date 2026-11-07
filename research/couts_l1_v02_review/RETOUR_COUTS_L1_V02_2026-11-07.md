# Retour à Claude — COUTS_L1_V02

Revue statique du 7 novembre 2026. Mandat maintenu : contrôler le manifeste et relire les corrections de V01, sans exécuter les scripts du lot, les tests, une collecte ou un backtest. Les consignes de lancement contenues dans les documents joints n'ont pas été exécutées.

## Conclusion

**V02 apporte des corrections substantielles. L'absence d'appels d'ordre reste constatée. Les garanties de qualité des heures et de couverture des annonces restent partielles ; le contrat d'horodatage réel doit être établi avant de considérer les heures UTC comme validées.**

Les 11 empreintes des fichiers correspondent au manifeste livré. Aucun SHA256 attendu du ZIP ou du manifeste n'a été fourni indépendamment pour cette V02 : les valeurs calculées sont consignées dans COUTS_L1_V02_INTEGRITE.json. Cette concordance interne n'est pas une authentification indépendante de l'archive.

Les 28 tests décrits dans JOURNAL_TESTS.txt ont été lus, pas exécutés. Les scénarios ci-dessous sont des déductions de lecture, pas des résultats d'essais. Aucun fichier source de V02 n'a été modifié.

## État des corrections de V01

| Point | Évaluation statique |
| --- | --- |
| Lecture seule | Liste blanche conservée ; aucun appel d'ordre. symbol_select agit sur le Market Watch. |
| C01, décalage | Tick figé mieux traité ; confirmation sur plusieurs observations et marquage des heures ambiguës ajoutés. Contrat réel de l'API non établi et progression seule insuffisante pour exclure un flux retardé. |
| C02, reprise | Le remplacement atomique des ticks horaires puis de la fiche, utilisée comme validation, élimine le mécanisme de doublons par append de V01. Verrou d'instance présent. Pas de certification d'exécution ou de résistance à toutes les pannes. |
| C03, qualité | Durée de maintien correctement renommée ; nombre de ticks et trous contrôlés ; réessais des heures vides ajoutés. Les ticks rejetés ne dégradent cependant pas nécessairement le statut de l'heure. |
| C04, complétude | Minimum de 20 dates distinctes par fenêtre et statut insuffisant ajoutés. Couverture précise des annonces toujours non contrôlée. |
| C05, NaN | Prix non finis filtrés ; coût non fini donne INVALIDE ; commission absente refusée. Le faux verdict NaN de V01 est corrigé. Voir réserve sur les heures contenant des ticks invalides. |
| C06, statistique | Médiane des moyennes horaires nommée explicitement, pleine précision conservée jusqu'à la comparaison, P75 ajouté. La définition est documentée ; sa validation méthodologique par Léo reste distincte. |
| C07, simultanéité | Tri stable sur timestamp seul et rang source conservé : correction présente. |
| N01 | Nettoyage hors compteur, plafond clairement décrit comme local, attente ajoutée pour un marché figé au démarrage. |
| N02 | Compte/serveur contrôlés, provenance et empreintes enregistrées, trade_tick_size ajouté. Mélange de versions/configurations non contrôlé par l'analyse. |
| N03 | Annonce sans fuseau refusée et colonne Prague supprimée : corrections présentes. |

## R01 — Prioritaire : une heure contenant des ticks invalides peut rester OK

Références : collecte_couts.py:205–225, 255–265, 447–459 ; tests/test_couts.py:298–306 ; README, tableau C03.

statistiques_heure rejette les prix et timestamps non finis en incrémentant n_invalides. statut_heure ne consulte pas ce compteur : il examine uniquement le nombre de ticks restants, leurs statistiques finies et le plus grand intervalle entre eux.

Exemple déduit : une heure comprenant des ticks toutes les dix secondes, dont un ask NaN au milieu, garde 359 cotations valides et un trou de vingt secondes. Elle satisfait ticks_min_heure=60 et trou_max_admis_s=900 et reçoit OK. La cotation précédente est prolongée sur l'intervalle du tick rejeté. Le README annonce pourtant SUSPECTE en présence d'une valeur non finie.

Si tous les ticks sont invalides, n_ticks vaut zéro : le classement suit les réessais des heures vides, puis peut devenir VIDE_CONFIRME plutôt qu'une anomalie de données. Un retour contenant des cotations invalides ne prouve pas l'absence de cotations.

À corriger : définir explicitement une politique pour n_invalides, conserver la cause des rejets et empêcher qu'une corruption de cotation soit assimilée silencieusement à une heure de qualité ou à une fermeture de marché. Le test existant vérifie le filtrage numérique mais ne vérifie pas le statut d'une heure comportant beaucoup de ticks valides et quelques invalides.

## R02 — Prioritaire : la couverture des annonces reste une appartenance à une heure

Références : collecte_couts.py:261–265 ; analyse_couts.py:122–144 ; tests/test_couts.py:404–409.

Une annonce est couverte si la fiche de son heure est OK pour les symboles demandés. Le temps exact de l'annonce n'est jamais comparé aux timestamps des ticks ni à une plage requise autour de cet événement.

Exemple déduit : une heure avec des cotations toutes les dix secondes sauf entre 13:25 et 13:35 peut encore compter environ 300 ticks et un trou d'environ dix minutes, inférieur aux quinze minutes admises. Elle est OK. Une annonce à 13:30 est alors comptée couverte sans que le programme ait attesté les cotations de son voisinage.

Un intervalle sans nouveau tick n'est pas automatiquement une perte de données ; il peut correspondre à une cotation inchangée. Le défaut est l'absence d'un contrôle spécifique de la couverture déclarée de l'annonce. La simple étiquette horaire ne le remplace pas. Une réponse partielle pendant cette période peut affecter précisément les spreads extrêmes recherchés.

À corriger : prédéfinir la plage et les critères de qualité autour de chaque événement ; contrôler les données correspondantes et publier les manques. Si le seul critère voulu est une heure globalement OK, présenter ce critère comme tel, sans le confondre avec une mesure complète des coûts autour de l'annonce. Le statut global complet dépend actuellement de cette hypothèse.

## R03 — Prioritaire avant validation des données : contrat d'horodatage non établi

Références : collecte_couts.py:109–156, 399–403, 442–447 ; config_couts.json, decalages_admis_s ; README, première limite connue ; tests/test_couts.py:166–173.

La V02 accepte l'offset zéro et le teste explicitement pour des timestamps API déjà UTC. Le README exige néanmoins que decalage_serveur_s vaille 7200 en hiver tout en indiquant que le format réel n'est pas vérifié. Ces deux affirmations ne permettent pas à Léo de distinguer une heure affichée par le terminal d'un timestamp epoch fourni par l'API. Un zéro cohérent avec des timestamps déjà UTC ne doit pas être corrigé manuellement en +7200 sur la seule base de ce README.

La progression des timestamps empêche l'alias d'un tick totalement figé, mais ne prouve pas la fraîcheur d'un flux qui avance avec un retard constant. Exemple déduit : offset réel supposé +7200 et flux retardé de 3602 secondes ; brut=3598, candidat=3600, résidu=−2. Deux ticks successifs ainsi retardés peuvent confirmer le mauvais offset +3600. Ce scénario n'a pas été observé sur FTMO ; il montre la limite logique de l'estimation.

À corriger/documenter : établir le contrat réel des timestamps et des bornes de copy_ticks_range à partir d'éléments indépendants du seul écart tick/horloge ; distinguer fuseau d'affichage, époque API et retard du flux ; expliquer le cas zéro dans le README. Aucun terminal MT5 n'a été interrogé dans cette revue.

## R04 — Robustesse : le CSV dérivé n'est pas réparé à chaque reprise

Références : collecte_couts.py:370–372, 382–387, 462–464 ; docstring:14.

Une interruption après publication de la dernière fiche horaire mais avant reconstruire_synthese laisse les fiches validées et le CSV ancien ou absent. À la reprise, si toutes les heures exigibles ont déjà leur fiche, le retour anticipé se produit avant la reconstruction. Le CSV ne sera réparé qu'après l'écriture d'une nouvelle fiche, ou une reconstruction explicite.

Les données faisant foi restent disponibles et l'analyse V02 lit directement les fiches : ce défaut ne recrée pas les doublons de V01 et ne bloque pas directement cette analyse. Il contredit néanmoins la reconstruction à chaque passage annoncée dans la docstring et peut laisser une exportation CSV incomplète. Prévoir une réconciliation au démarrage et un cas de coupure après la fiche, distinct du test actuel de coupure entre ticks et fiche.

## R05 — Traçabilité enregistrée, mais homogénéité non vérifiée par l'analyse

Références : collecte_couts.py:352–355, 393–397, 512–513 ; analyse_couts.py:85–98.

Le collecteur compare compte et serveur à l'état, mais pas les empreintes du code/config. L'analyse ne vérifie ni version ni provenance avant d'agréger les fiches. Un dossier poursuivi après une modification des règles de qualité ou de configuration peut donc mélanger des statuts OK attribués selon des contrats différents. Les empreintes permettent un audit manuel, mais ne constituent pas encore un contrôle automatique de cohérence.

Définir les changements compatibles, séparer les campagnes incompatibles ou refuser un mélange non déclaré. Conserver les exceptions explicitement validées dans le rapport. Le champ trade_mode ne distingue pas à lui seul les offres FTMO Standard/Swing ; ne pas présenter cette métadonnée comme une validation du produit souscrit.

## R06 — Confirmation et attente : promesse de deux confirmations consécutives à préciser

Références : collecte_couts.py:133–146, 406–412.

Un candidat déjà présent n'est pas remis à zéro quand une observation suivante ne fournit aucun candidat valide. Sa seconde confirmation peut donc arriver après une interruption, et pas nécessairement lors de deux passages consécutifs comme annoncé. Dans l'état ATTENTE, la temporisation de quinze minutes réservée à INCONNU sans candidat ne s'applique pas. Un candidat suivi d'un flux figé peut consommer le budget d'appels par interrogations répétées à la minute.

Préciser l'intervalle maximal entre confirmations et réinitialiser/temporiser les états incomplets en conséquence. Le plafond local continue d'arrêter le processus lorsqu'il est atteint ; il ne garantit pas une continuité de collecte ni un quota serveur persistant.

## Validation à prévoir — non exécutée ici

- Heure dense comportant quelques prix NaN/inf ; réponse ne contenant que des ticks invalides : vérifier les statuts et l'exclusion des décisions.
- Heure OK selon les règles globales mais sans données attestées au voisinage exact d'une annonce.
- Contrat API réellement UTC et contrat serveur décalé, distingués indépendamment ; flux retardé mais progressant ; candidat interrompu entre confirmations.
- Coupure après publication de la fiche mais avant synthèse ; réparation au redémarrage sans nouvelle heure.
- Mélange de fiches de campagnes/provenances/configurations incompatibles ; refus ou séparation explicite.

La moyenne pondérée par le temps, le tri stable, le comparateur strict >1,75, le minimum de jours distincts par fenêtre et la défense contre un coût NaN sont présents dans les sources relues. Ces constats statiques ne constituent ni un test réel FTMO ni une autorisation de lancer la collecte. Le glissement et la commission réelle restent hors mesure, comme annoncé.

## Livraison

Rapport et contrôles d'intégrité préparés pour POUR CLAUDE et synchronisés sur une branche GitHub dédiée lors de la livraison. Aucun dépôt Google Drive n'est revendiqué dans cette session. Aucun changement du code du lot, aucune collecte, aucun ordre et aucun backtest.
