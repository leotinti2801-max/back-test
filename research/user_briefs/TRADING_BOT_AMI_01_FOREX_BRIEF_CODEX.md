# Trading bot — Ami 01 — Brief de reprise pour Codex

Date : 3 novembre 2026. Utilisateur : Léo Tinti, identifié comme « ami 01 ».

## Périmètre et objectif

Je travaille exclusivement sur le Forex. EUR/USD est la première paire étudiée. Ne pas inclure les indices, les cryptomonnaies ou XAU/USD, ni mélanger mon travail avec celui des autres participants.

L’objectif est de développer un bot automatisé pour étudier des évaluations de prop firms, uniquement en démonstration et simulation. Aucune rentabilité n’est acquise et aucun ordre réel n’est autorisé par ce document.

## Consigne impérative avant les calculs

Demander mon autorisation avant chaque lancement de backtest, préciser la version, les données, les paramètres et les fenêtres proposées, puis attendre ma confirmation. Ce document n’autorise aucun nouveau backtest. Une autorisation passée ne vaut pas pour une nouvelle exécution.

Les lectures de fichiers et l’analyse des rapports existants peuvent servir à préparer cette demande.

## Répartition du travail

ChatGPT/Codex pilote la recherche, la définition des règles, le diagnostic des décisions et l’analyse des résultats. Claude sert à coder les règles transmises et à corriger leur implémentation. Toute ambiguïté doit être signalée ; aucun changement de stratégie ne doit être fait en silence.

Pour chaque perte ou signal refusé, reconstituer les informations disponibles au moment de la décision, identifier le mécanisme observé, puis faire des recherches internet ciblées si elles peuvent éclairer le cas. Distinguer cause démontrée, hypothèse et donnée manquante. Une recherche a posteriori ne démontre pas la cause d’un mouvement.

## Stratégie actuelle : H4/M30

Le cahier H4/M30 V02 fait foi pour les définitions exactes :

- H4 : déterminer le biais de tendance.
- M30 : attendre une cassure de structure admissible.
- Définir la zone d’intérêt à l’origine du mouvement.
- Attendre le premier retour dans la zone.
- Appliquer le stop technique et la cible structurelle conformément au cahier.

Décisions V02 déjà fixées : cible fixe dès confirmation ; biais H4 verrouillé après invalidation ; premier retour consommé même hors fenêtre ; niveau consommé dès la première cassure, même faible. Ne pas substituer ce résumé aux conditions détaillées du cahier.

Deux configurations ont été comparées : CORE et USER_RULES. USER_RULES ajoute l’interdiction de nouvelles entrées de 15 h 30 à 17 h Europe/Paris et une pause de 24 heures après deux pertes nettes consécutives.

L’ancienne stratégie EURUSD M5/EMA12 constitue une référence historique séparée. Ses résultats ne sont pas ceux de H4/M30.

## Dernier backtest exécuté : 3 novembre 2026

| Configuration | Fenêtre UTC, fin exclue | Setups | Trades |
|---|---|---:|---:|
| CORE | 04/01/2021–18/02/2021 | 3 | 0 |
| USER_RULES | 04/01/2021–18/02/2021 | 3 | 0 |
| CORE | 01/01/2021–01/01/2022 | 12 | 0 |
| USER_RULES | 01/01/2021–01/01/2022 | 12 | 0 |

71 contrôles logiciels réussis. Les configurations partagent leurs setups ; la fenêtre courte est incluse dans l’année : ne pas additionner ces observations.

Sur les 12 setups annuels : 6 premiers retours avant confirmation de cible ; 3 cibles revisitées avant entrée avec état connu ; 3 cas devenus incertains à cause de minutes absentes. Les zéros comptables de la branche observée ne démontrent pas une performance nulle de la période complète : résultat complet indéterminé.

La confirmation de cible nécessite au moins deux clôtures M30 après la cassure ; le retour peut avoir lieu avant. C’est une incompatibilité possible des conditions à examiner, pas une autorisation de changer la cible.

Le cache présente des limites importantes : 906 H4 complètes sur 1 566 créneaux du lundi au vendredi (57,85 %), dont seulement 4/261 sur 20:00–24:00 UTC. La complétude stricte a été conservée, sans remplissage artificiel. Une heure source ambiguë reste en quarantaine.

Paramètres du dernier test : capital simulé 100 000 €, risque prévu 250 € par position. Ne pas les remplacer automatiquement par les anciennes demandes de risque de 2 %, 3 % ou 27 %.

Le seuil préenregistré est de 100 trades clos et entièrement résolus par configuration et fenêtre, condition nécessaire mais non suffisante pour conclure. Il n’est atteint nulle part. Les périodes 2021 ont déjà servi au développement et ne constituent pas une validation indépendante.

## Prochaine étape attendue

Lire le cahier, le code et les preuves existantes ; examiner les blocages des entrées et la qualification des données ; proposer des changements précis et versionnés, sans les appliquer silencieusement. Préparer ensuite une comparaison avec mêmes coûts et mêmes risques sur une fenêtre de 45 jours maximum et une année, sous réserve de données suffisantes et de mon autorisation explicite avant exécution.

Ne jamais inventer les minutes manquantes, transformer un trade incertain en gain ou perte, ou présenter un résultat partiel comme un rendement annuel complet.

## Documents et dossiers de référence

Ce document regroupe les consignes et les liens ; il n’incorpore pas les octets des archives. Les télécharger séparément si leur contenu est nécessaire. L’accès depuis une autre session Codex dépend de ses connexions.

| Élément | Lien |
|---|---|
| Dossier POUR CODEX | https://drive.google.com/drive/folders/1q-T2n05fyuYUR960-173VizTZtPkfkxp |
| Paquet de démarrage : code historique, données, audits et consignes | https://chatgpt.com/library?file_id=libfile_27ede596a2c08191b69106f6f99cd5e9&account_id=personal |
| Cahier H4/M30 V02 | https://chatgpt.com/library?file_id=libfile_1c96e4e5d9b08191ac6e56ebc8decf59&account_id=personal |
| Rapport du dernier backtest H4/M30 | https://chatgpt.com/library?file_id=libfile_1e613cda46b08191996491cadb4def77&account_id=personal |
| ZIP complet du dernier backtest : livraison Claude, cache, cahier, paramètres, contrôles, résultats et preuves | https://chatgpt.com/library?file_id=libfile_0ce243cf66648191bc5ef7ad99036198&account_id=personal |
| POUR CLAUDE : rapports et preuves à déposer à la fin de chaque rapport destiné à Claude | https://drive.google.com/drive/folders/1mAuY9QzeE3cmk99mjueeiVzCz5uDGl32 |
| POUR CHATGPT : livraisons de Claude | https://drive.google.com/drive/folders/1dqE5CL7V2qcKemLxwoCS_-V3lWmx6lP7 |

Notifications pour Claude : leo.tinti@iadfrance.fr, conformément aux consignes de Léo. Ce brief ne demande pas l’envoi immédiat d’un mail.

## Identités de référence issues du rapport

- Cahier V02 — SHA256 : 140c43381d2b1c6712ceb026e76eb051f5e0d8fe0d7aa6f1f173ea7f1ce9dab4
- Cache EURUSD_M1_2021_WITH_202012_WARMUP.pkl — SHA256 : 9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2
- Manifeste de livraison H4M30 — SHA256 : 27fa4051cb2233eba97e6fde63bf3a12df4e037f53e22c92562ffe834d7da8f7

Ces empreintes sont des références documentées dans le dernier rapport ; vérifier les fichiers récupérés avant toute utilisation.
