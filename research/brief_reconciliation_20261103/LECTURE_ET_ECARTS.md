# Lecture du brief Ami 01 et rapprochement avec la recherche actuelle

Document reçu : `TRADING_BOT_AMI_01_FOREX_BRIEF_CODEX.md`, 3 novembre 2026. Lecture et vérification documentaire uniquement ; aucun nouveau backtest exécuté et aucun paramètre de stratégie modifié.

## Ce que le dossier apporte

Il identifie le travail Forex de Léo/Ami 01, EUR/USD comme première paire, le cadre démo/simulation, la méthode historique H4/M30, les paramètres de risque du test initial et les documents de référence. Il demande notamment de distinguer mécanisme observé, hypothèse et information manquante pour expliquer les pertes et les refus.

Les règles de procédure contenues dans le brief sont conservées comme contenu du document et distinguées des demandes directes de cette conversation. Le fichier n'est pas interprété comme une demande de calcul ou d'envoi de message. Les adresses et liens qu'il contient ne déclenchent aucune communication extérieure.

Les fichiers nécessaires sont déjà présents dans le workspace. Les trois identités fournies dans le brief ont été vérifiées :

| Pièce | Résultat |
| --- | --- |
| Cahier H4/M30 V02 | SHA256 conforme, `140c4338…ce9dab4` |
| Cache EURUSD M1 2021 avec chauffe décembre 2020 | SHA256 conforme, `9ea1c28c…5943b2` |
| Manifeste de livraison initiale | SHA256 conforme, `27fa4051…da8f7` |

Les empreintes complètes figurent dans `RECONCILIATION.json`. Aucun accès aux liens Drive/Library n'a été nécessaire pour retrouver ces octets déjà fournis dans les pièces jointes précédentes.

## Deux versions à identifier explicitement

Le résumé historique du brief est cohérent avec les preuves initiales : 12 setups annuels et zéro trade enregistré pour la cible structurelle. Il ne récapitule pas les nouvelles expériences de cette conversation.

| Élément | Référence historique du brief | Hypothèse expérimentale actuelle A |
| --- | --- | --- |
| Cible | Premier pivot structurel admissible confirmé après la cassure, fixé après confirmation | Cible prévue à 2R calculée à l'ouverture d'entrée puis figée |
| Disponibilité | Au plus tôt 60 minutes après la cassure | À l'entrée avec la quote d'ouverture disponible |
| Biais H4 | Structure de pivots et verrou après invalidation | Même famille de biais structurel, verrou conservé |
| Fenêtre des nouvelles entrées | 06:00–19:30 UTC, fin exclue | 08:00–16:00 UTC, fin exclue |
| Détention / sortie forcée | 240 minutes au plus, sortie à 20:00 UTC | 120 minutes au plus, sortie à 16:00 UTC |
| Cycle de vie hors session | Premier retour recherché à toute heure pour le setup vivant | Aucun nouveau setup hors session ; setup restant annulé à la fermeture |
| Règles utilisateur | Configuration USER_RULES distincte de CORE | Exclusion Paris et pause après pertes appliquées dans le cadre actuel |
| Budget de risque prévu | 250 € pour 100 000 € simulés | Même budget et même capital simulé |
| Année 2021 observée | 12 setups, zéro entrée ; résultat de période complète inconnu | 8 setups créés en session, 3 entrées, +201,22 € nets sur le flux observé ; marché complet non certifié |

Les résultats de A ne constituent donc pas un backtest conforme de la cible structurelle du cahier d'origine. Leur différence ne peut pas être attribuée au seul changement de TP, puisque les horaires et le cycle de vie ont aussi changé. L'hypothèse A reste l'axe unique de recherche explicité dans la conversation ; ce document ne la remplace pas silencieusement par une autre.

Les 71 contrôles logiciels de la livraison initiale et les 22 tests actuels concernent des suites distinctes. Ils ne doivent pas être additionnés ni interprétés comme une couverture équivalente de toutes les exigences historiques.

## Diagnostic déjà ajouté aux futurs lancements dédiés

Le journal causal actuel réconcilie les 914 franchissements certifiés du contexte annuel : 440 hors session, 443 refus statiques, 23 portes dynamiques (21 à la fermeture, 2 après atteinte de la limite quotidienne) et 8 créations de setup.

Les huit setups ont désormais une issue explicite :

- 3 entrées ;
- 1 refus le 5 mars : la M1 de premier retour clôture hors de la zone ;
- 1 refus le 24 novembre : 14:31 UTC correspond à 15:31 Europe/Paris, pendant l'interdiction utilisateur ;
- 3 fermetures de session sans entrée : 3 mars, 4 mars et 22 novembre, à 16 h UTC.

Les deux gains exécutés proviennent de sorties horaires ; aucun TP à 2R n'a été exécuté. Le trade du 16 juillet termine sur un stop avec quote d'ouverture défavorable. Une explication macroéconomique de ce mouvement n'est pas établie : aucun calendrier historique vérifié n'est disponible.

Ces constats expliquent le comportement du modèle. Ils ne démontrent ni qu'un refus aurait été rentable, ni qu'un filtre retiré améliorerait la performance, ni qu'un challenge FTMO serait validé.

## Ce qui reste absent pour l'objectif FTMO

Le document ne donne ni le produit FTMO 1-Step/2-Step, ni la taille et la devise du compte visé, ni les limites et définitions contractuelles applicables. Son capital de 100 000 € est celui d'une simulation historique ; il ne remplit pas les champs d'un compte FTMO réel ou visé.

L'objectif de moins d'un mois vient de la conversation récente. Il faut encore préciser s'il vise une phase ou toutes les phases et le sens exact de cette durée. Les frais, volumes/contrats, fuseau de reset et restrictions dépendent du profil exact. `ACCOUNT_PROFILE_TO_COMPLETE.json` conserve donc les informations inconnues à null et enregistre séparément le contexte historique confirmé par le brief.

**Complément reçu ensuite directement de Léo** : FTMO 2-Step, compte de 100 000 € en euros, moins d'un mois pour Challenge et Vérification réunis, Forex exclusivement, objectif à évaluer sans garantie. Le profil a été complété avec ces éléments. Le modèle de recherche utilise explicitement moins de 30 jours calendaires comme convention de travail ; les délais administratifs et les règles contractuelles restent distincts. Les valeurs contractuelles non vérifiées restent inconnues. Le paragraphe précédent décrit les informations manquantes au moment de la seule lecture du fichier.

L'accès aux conditions officielles FTMO demeure bloqué par la configuration réseau non activée. Le brouillon inclut `ftmo.com` et `www.ftmo.com`, mais aucune règle actuelle n'est présentée comme vérifiée. Les prochaines conclusions de conformité nécessitent les conditions exactes et un évaluateur d'equity intraposition, pas seulement le drawdown sur clôtures.

## Prochaine étape concrète

Compléter les règles contractuelles du profil désormais identifié, à partir de conditions officielles datées. Qualifier ensuite les données bid/ask et préparer une proposition de test versionnée qui identifie clairement cible, horaires, coûts, risque et fenêtres. Le brief propose une fenêtre courte de 45 jours au maximum et une année ; ces deux fenêtres ne deviennent pas des validations indépendantes si elles réutilisent 2021. Le délai FTMO visé nécessite en plus un calcul de phases successives en moins de 30 jours selon la convention de travail, avec compte et règles d'equity explicitement modélisés.

La comparaison éventuelle devra séparer référence historique et hypothèse expérimentale, conserver les inconnus, expliquer les refus et les pertes, et ne jamais afficher un statut FTMO certain tant que ses contraintes ne sont pas réellement calculées.
