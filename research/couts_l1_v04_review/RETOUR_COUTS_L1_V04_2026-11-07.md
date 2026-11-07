# Retour à Claude — COUTS_L1_V04

Revue statique du 7 novembre 2026, dans la continuité de V01 à V03. Aucun script du lot, test, backtest ou collecteur n'a été exécuté. Aucun accès à MT5 ni au compte de Léo. Les instructions de lancement et les affirmations de campagne en cours du README sont du contenu documentaire, pas des actions effectuées ou des faits vérifiés dans cet audit.

## Conclusion

**Les trois réserves S01–S03 de V03 sont prises en charge dans le chemin normal de la configuration livrée. Aucun nouveau défaut bloquant n'a été identifié dans les corrections relues.** Un point de robustesse subsiste dans le typage des deux champs de validation manuelle (T01 ci-dessous).

La configuration livrée laisse volontairement contrat_horodatage_verifie à false et preuve_contrat_horodatage vide. L'analyse ne peut donc pas déclarer la collecte complète avec ce fichier, même si les conditions quantitatives étaient réunies. C'est le comportement attendu, pas une anomalie à contourner.

Cette conclusion porte sur la lecture du code, pas sur une qualification des données réelles ou une certification FTMO. Le journal fourni annonce 48 tests réussis ; les 48 définitions de tests sont présentes, mais leur résultat n'a pas été reproduit ici.

## Intégrité de l'archive

| Contrôle | Résultat |
| --- | --- |
| Entrées ZIP | 14 : 12 fichiers, dont le manifeste, et 2 dossiers |
| Empreintes annoncées | 11 fichiers |
| Comparaisons individuelles | **11 sur 11 conformes au manifeste** |
| SHA256 du ZIP calculé | 8f85bdc3daba7df38e10991838e53f7c7bff8e3f41929ce7865ffcdf83bef296 |
| SHA256 du manifeste calculé | 7f88cb3ba1f3593a61235566316b7d28f4a70833d60343141b91916d22d2a731 |
| Inventaire | Aucun fichier régulier supplémentaire, hormis le manifeste |
| Noms dupliqués, chemins sortants, liens symboliques | Aucun détecté dans le ZIP |

Aucun SHA256 attendu du ZIP ou du manifeste n'a été fourni indépendamment dans le message V04 : les deux valeurs ci-dessus sont calculées, sans comparaison à une référence extérieure. La concordance interne des 11 fichiers n'est pas une authentification indépendante de l'archive.

COUTS_L1_V04_INTEGRITE.json contient les valeurs attendues et calculées pour chacun des 11 fichiers. Les sources extraites dans /workspace/reviews/COUTS_L1_V04 n'ont pas été modifiées.

## Évaluation des trois réserves de V03

### S01 — Base de fuseaux absente : correction présente

Références : collecte_couts.py:152–158, 203–221, 579–581 ; tests/test_couts.py:547–569.

- Lorsque controle_ny7 est activé et que la base de fuseaux manque, decalages_admis renvoie une liste vide. Le repli silencieux sur [0, 3600, 7200, 10800] est supprimé.
- main contrôle cette condition avant mt5.initialize et refuse la connexion de collecte dans ce cas.
- Une heure nécessitant la conversion NY+7 devient AMBIGUE si le contrôle temporel ne peut pas être effectué.
- Le mode dégradé ne réutilise la liste élargie que lorsque controle_ny7 est explicitement désactivé ; cette perte de garantie est documentée.
- Les nouveaux tests simulent l'absence de base et vérifient les candidats refusés, les heures ambiguës et le mode dégradé. Leur présence est constatée sans les exécuter.

Une heure déjà en UTC (offset zéro) n'a pas besoin d'être convertie par NY+7. Les fonctions de qualification conservent cette distinction ; elle ne réintroduit pas le repli de V03. Le collecteur lancé avec la configuration normale vérifie néanmoins sa dépendance de fuseau au démarrage.

### S02 — Anciennes fiches et validation temporelle : correction présente

Références : analyse_couts.py:106–122, 207, 255–263, 295–297 ; tests/test_couts.py:571–585 ; README:5–15.

Le statut effectif des fiches OK est recalculé, y compris pour V02/V03 : invalides détectés, offset zéro accepté, offset non nul comparé à NY+7 au début et à la fin de l'heure. Un offset incompatible donne AMBIGUE ; une conversion non vérifiable faute de base provoque une erreur.

Le statut global complet dépend maintenant aussi de la déclaration manuelle de validation et d'une preuve non vide dans la configuration. Le README distingue la possibilité de lire les données V02 de la preuve que leurs heures UTC sont justes.

Des statistiques et des verdicts par fenêtre peuvent encore être affichés à titre provisoire lorsque les 20 jours de la fenêtre sont présents. Le rapport indique alors explicitement « NON, aucun verdict définitif » pour la complétude si le contrat n'est pas validé. Il ne faut donc pas interpréter une ligne SOUS LE SEUIL isolée comme une validation finale.

Le contrôle d'horodatage réel demeure à documenter sur les données de Léo. La déclaration de configuration est une attestation humaine, pas une mesure réalisée par cet audit. Aucun champ n'a été modifié pour simuler cette attestation.

### S03 — Provenance complète : correction présente

Références : analyse_couts.py:125–136, 199–207, 255–278 ; tests/test_couts.py:587–608.

L'identité contrôlée contient maintenant version, config_sha256, code_sha256, serveur et compte. Un mélange non explicitement accepté ou un champ manquant/vide empêche la complétude finale. Les différences de code ou de compte ne sont donc plus masquées par un couple version/configuration identique.

Le rapport affiche une empreinte courte du numéro de compte, pas sa valeur brute. Cette empreinte est un masquage d'affichage, sans prétention d'anonymisation cryptographique des données source. Les tests ajoutés couvrent notamment compte différent, provenance incomplète et rendu du rapport.

## T01 — P2, robustesse de la validation manuelle : vérifier les types

Références : **analyse_couts.py:207**, verifier_config:86–94 ; config_couts.json, deux champs de contrat.

Le code calcule contrat_ok avec bool(...) et bool(str(...).strip()). Il ne vérifie pas qu'il reçoit exactement un booléen true et une preuve écrite de type chaîne.

Deux cas déduits de lecture, non exécutés :

- contrat_horodatage_verifie contenant la chaîne JSON "false" est évalué comme vrai par bool, si une preuve textuelle est présente.
- contrat_horodatage_verifie égal au booléen true et preuve_contrat_horodatage égal à null donnent une preuve convertie en texte "None", donc considérée non vide.

Si les autres conditions de données sont satisfaites, une configuration mal typée peut donc être annoncée comme validée. **Ce cas ne se produit pas avec la configuration fournie**, qui utilise bien le booléen false et une chaîne vide.

Amélioration recommandée : exiger un vrai booléen pour le premier champ et une chaîne non vide pour la preuve lorsque la validation vaut true ; refuser une configuration mal typée plutôt que la convertir implicitement. Cas à prévoir : chaîne "false", preuve null, false avec chaîne vide, true avec preuve textuelle. Aucun test supplémentaire ni correction n'a été écrit ou exécuté dans cette revue.

## Limites et état des points précédents

- Aucun appel d'envoi, de modification ou de fermeture d'ordre identifié. Les appels MT5 visibles restent dans l'enveloppe de fonctions autorisées ; symbol_select ne fait qu'ajouter un symbole au Market Watch.
- Moyenne pondérée par la durée de maintien, tri stable des ticks simultanés et conservation de la précision jusqu'au comparateur maintenus.
- Seuil strict >1,75 pip maintenu : l'égalité ne déclenche pas l'abandon. Minimum de 20 dates distinctes par fenêtre maintenu.
- Heures invalides exclues, coût non fini classé INVALIDE et commission absente refusée : corrections précédentes maintenues.
- Archives horaires et fiches atomiques, verrou d'instance et réconciliation du CSV au démarrage maintenus.
- Présence des ticks autour des annonces sur −5/+10 minutes avec un trou maximal de 60 secondes maintenue. La présence de ticks ne certifie pas l'exactitude de leurs prix.
- Le contrat NY+7 utilisé par le lot et le comportement réel de l'API FTMO n'ont pas été vérifiés sur un terminal dans cette session. Une référence UTC indépendante et des repères datés restent nécessaires à l'attestation prévue par le README ; la simple existence d'un événement DECALAGE_CONFIRME n'est pas cette preuve.
- La commission est configurée à 0,5 pip, pas mesurée ; le glissement n'est pas mesuré. Aucune conclusion sur les coûts réels n'est possible sans les fichiers de collecte.
- Aucune nouvelle campagne, aucun achat de challenge, aucun ordre et aucune collecte ne sont autorisés ou déclenchés par ce rapport. Les assertions de campagne en cours du README n'ont pas été vérifiées ici.

## Livraison

Rapport et contrôles d'intégrité préparés pour POUR CLAUDE, avec une archive de retour contenant ces deux documents. Publication sur une branche GitHub dédiée lors de la livraison ; aucun dépôt Google Drive revendiqué. Les sources du lot restent inchangées et main n'est pas modifiée.
