# Retour à Claude — COUTS_L1_V03

Revue statique du 7 novembre 2026, dans la continuité des revues V01/V02. Aucun script du lot, test, backtest ou collecteur n'a été exécuté. Aucun accès MT5. Les instructions de lancement et les affirmations concernant une campagne en cours dans le README sont du contenu documentaire : elles ne sont ni une autorisation d'exécution ni un état de campagne vérifié ici.

## Conclusion

**V03 corrige effectivement R01, R02, R04 et une grande partie de R06. R03 reste conditionné à la disponibilité de la base de fuseaux ; son repli peut réintroduire le défaut qu'il vise à éliminer. R05 contrôle les couples version/configuration, pas encore toute l'identité d'une campagne.**

Absence d'appels d'ordre constatée dans le code livré. Les formules de pondération temporelle, le tri stable, la précision de la décision, le minimum de jours par fenêtre et le seuil strict >1,75 pip restent présents. Aucun résultat réel de coût ni état réel du compte n'est validé par cet audit.

## Intégrité

- 14 entrées : 12 fichiers, dont le manifeste, et 2 dossiers.
- Les 11 fichiers annoncés correspondent tous à leur empreinte dans MANIFEST_SHA256.json.
- Aucun fichier régulier supplémentaire, hormis le manifeste ; pas de noms dupliqués, de traversée de chemin ni de lien symbolique détecté dans l'archive.
- SHA256 du ZIP : **3b366b02372139e3062e3bdbf384decdf8539574a93464d9c20fbab3933f2a1a**.
- SHA256 du manifeste : **b79ec927ba5501a05238fa65758a8fd401888a53cc315ada173400e30dcc045d**.
- Aucun de ces deux SHA256 n'a été fourni indépendamment dans le message V03 : ils sont calculés ici, sans comparaison à une référence extérieure. La concordance interne des 11 fichiers ne constitue pas une authentification indépendante.

Le détail individuel figure dans COUTS_L1_V03_INTEGRITE.json. Les sources extraites dans /workspace/reviews/COUTS_L1_V03 sont inchangées. JOURNAL_TESTS.txt annonce 40 tests : journal lu, résultats non reproduits et non certifiés ici.

## Corrections de V02 constatées

| Réserve V02 | État en V03 |
| --- | --- |
| R01, invalides | collecte_couts.py:295–309 classe les heures avec invalides SUSPECTE et distingue SEULEMENT_INVALIDES. analyse_couts.py:87–92 requalifie aussi les fiches V02 OK comportant des invalides. |
| R02, annonces | analyse_couts.py:112–137 vérifie les heures concernées et les timestamps bruts sur la plage −5/+10 min, avec un intervalle maximal de 60 s et contrôle des bornes. L'absence d'archives entraîne un refus de couverture. |
| R03, heure | collecte_couts.py:136–151 limite normalement les candidats à zéro ou au décalage NY+7. Le README explique maintenant correctement que zéro peut être valable. Réserve S01 ci-dessous. |
| R04, synthèse | reconcilier est appelé dans main au démarrage, sous verrou, après connexion et sélection du symbole (collecte_couts.py:516–520, 582). Correction de la synthèse dérivée présente. |
| R05, provenance | Les provenances version/configuration sont comptées ; un mélange non accepté empêche le statut global complet (analyse_couts.py:95–97, 160–166, 214–215). Réserve S03 ci-dessous. |
| R06, attente | Expiration du candidat après cinq minutes et attente sur flux figé même avec candidat ajoutées (collecte_couts.py:166–168, 452–463). Les tests correspondants sont présents, non exécutés ici. |

## S01 — Prioritaire : le contrôle horaire disparaît si la base de fuseaux manque

Références : **collecte_couts.py:136–151, 163–165, 206–209** ; config_couts.json, decalages_admis_s/controle_ny7 ; README, installation et contrôle horaire ; tests/test_couts.py:454–473.

decalage_ny7 intercepte toute exception et renvoie None. decalages_admis réutilise alors la liste de secours **[0, 3600, 7200, 10800]**, même lorsque controle_ny7 vaut true. Le contrôle historique des heures devient également inopérant si le décalage attendu est indisponible.

Exemple déduit du code, non exécuté : en hiver, un flux ayant réellement +7200 s d'offset mais avançant avec 3602 s de retard propose +3600 s, résidu −2 s. Avec la base NY disponible, ce candidat est refusé. Sans la base, +3600 redevient admissible et deux observations peuvent le confirmer. Le défaut R03 de V02 est donc réintroduit par le repli.

Le README reconnaît le repli mais présente aussi la restriction à zéro/NY+7 et le refus du flux retardé d'une heure comme une propriété générale. Les tests centraux de cette propriété sont ignorés via skipIf lorsque la base manque. Un lancement de tests qui se termine par OK avec ces tests ignorés ne prouverait pas cette propriété.

**Correction attendue :** lorsque controle_ny7 est exigé, refuser explicitement le démarrage ou mettre les heures en attente/non validées si la base nécessaire est absente ; conserver un éventuel mode dégradé uniquement comme tel, avec sa perte de garantie inscrite dans les fiches et dans la complétude du rapport. Ne pas simplement élargir silencieusement les offsets acceptés. Ajouter un cas simulant l'absence de base, plutôt que sauter la vérification de sécurité correspondante.

Le contrôle NY+7 dépend par ailleurs du contrat FTMO retenu par le lot. Cet audit n'a pas vérifié les pages officielles invoquées par le README ni observé le comportement réel des timestamps API. Zéro et le décalage d'affichage restent deux interprétations différentes qu'une confirmation fondée sur le tick/horloge ne transforme pas, à elle seule, en preuve externe de ce contrat.

## S02 — Limite de migration : requalifier les invalides V02 ne revalide pas leurs heures UTC

Références : **README, paragraphe Campagne en cours** ; **analyse_couts.py:87–97, 167–168, 192–215**.

L'analyse V03 applique bien R01 aux fiches V02 et contrôle leurs archives autour des annonces. Elle ne contrôle toutefois pas leur decalage_serveur_s ni les preuves utilisées par V02 pour établir ce décalage. La restriction NY+7 et les traces enrichies de confirmation concernent le collecteur V03, pas rétrospectivement le dossier V02 copié.

Une campagne provenant uniquement de V02 est homogène au sens du compteur de provenances, mais elle peut conserver les réserves d'horodatage identifiées dans V02. Le fait de disposer de ticks denses autour d'une annonce étiquetée en UTC ne prouve pas indépendamment que l'étiquette UTC est correcte : ces deux informations viennent de la même conversion.

**À expliciter dans la livraison :** distinguer compatibilité de lecture et validation temporelle. Pour une analyse V02, conserver un statut ou une réserve indiquant si le contrat temporel de cette campagne a été vérifié, avec ses éléments de preuve. Ne pas présenter la seule utilisation d'analyse_couts.py V03 comme une correction rétroactive de R03. Si l'historique se révèle décalé, une requalification/reconstruction documentée est nécessaire avant un verdict final.

Ce point n'établit pas que les données de Léo sont erronées : aucune donnée réelle ni journal de sa collecte n'a été fourni dans cette archive. Il ne donne aucune instruction de lancement ou d'arrêt sur son PC.

## S03 — Provenance partielle : version/configuration ne suffisent pas à identifier une campagne

Références : **analyse_couts.py:95–97, 160–166, 214–218** ; collecte_couts.py, provenance.

cle_provenance ne retient que version et config_sha256. code_sha256, serveur, numéro de compte, devise et identité de campagne ne participent pas au contrôle de mélange. Deux ensembles de fiches de comptes ou de codes différents, mais portant la même version et la même configuration, sont considérés comme une seule provenance.

Une provenance entièrement absente donne aussi le couple (version éventuellement absente, None). Si toutes les fiches portent ce même couple, aucun mélange n'est détecté ; l'absence de preuve n'est pas signalée comme provenance invalide. Les tests d'analyse utilisent notamment des fiches minimales ; ils ne valident donc pas un contrôle exhaustif de ces métadonnées.

**Correction attendue :** définir les champs requis pour identifier la campagne, refuser les preuves de provenance manquantes pour une validation finale, et vérifier au minimum le code, le compte/serveur et la configuration selon une politique de compatibilité explicite. Les métadonnées étant déjà enregistrées par les collecteurs, le contrôle peut s'appuyer dessus. Les données de compte n'ont pas à être publiées en clair dans un rapport public pour autant.

## Compléments et portée

- Le contrôle des annonces de V03 comble le trou de V02 : présence des archives, bornes temporelles et intervalle maximal sont examinés. Il ne certifie pas les prix, comme le README le reconnaît. Aucune nouvelle anomalie de sa logique n'est affirmée ici.
- Les fiches horaires atomiques, les archives par heure et le verrou restent présents ; le mécanisme d'append qui créait des doublons dans V01 n'est pas réintroduit.
- La définition médiane des moyennes horaires, la commission configurée de 0,5 pip, les 20 dates distinctes par fenêtre et l'opérateur strict >1,75 sont conservés. La commission réelle et le glissement ne sont toujours pas mesurés par ce lot.
- L'absence d'ordres dans ces scripts ne vaut pas confirmation contractuelle par FTMO des droits de collecte.
- Les corrections proposées dans ce rapport n'ont pas été codées ; aucun test, script du lot, compte, ordre ou collecte n'a été lancé.

## Cas complémentaires à prévoir — non exécutés ici

1. Base de fuseaux absente avec controle_ny7=true : aucun retour au candidat +3600 ne doit produire des heures validées en hiver.
2. Données V02 avec offset incompatible ou sans preuve de contrat API : distinguer campagne lisible et campagne temporellement validée.
3. Même version/configuration mais code, compte ou serveur différent ; champs de provenance absents : refus ou réserve explicite pour la complétude.

## Livraison

Rapport et contrôles d'intégrité préparés pour POUR CLAUDE et publiés sur une branche GitHub dédiée lors de la livraison. Aucun dépôt direct sur Google Drive n'est revendiqué. Aucun fichier source du lot n'a été modifié ; main reste hors du périmètre de publication.
