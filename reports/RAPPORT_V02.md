# H4/M30 V02 — développement et résultats du 3 novembre 2026

## Résultat principal

Une version expérimentale exécutable est livrée avec cinq hypothèses, des contrôles de risque et des journaux reproductibles. Elle débloque les entrées. **Aucune variante ne satisfait les conditions de sélection fixées avant les résultats ; aucune n'est qualifiée pour le trading réel.**

La rentabilité n'a pas été améliorée de façon démontrée. Obtenir uniquement des trades gagnants ne peut pas être garanti avec des informations disponibles avant l'entrée. Le bot livré ne comporte aucun accès courtier et n'envoie aucun ordre.

## Changements réalisés

1. Réutilisation du moteur d'exécution et de la construction des données d'origine, conservés à l'octet dans `vendor/h4m30_v01`. Reproduction de la référence : 12 setups et zéro trade compté sur 2021.
2. Cible alternative calculée dès l'ouverture d'entrée : 2R ou 1,5R nets prévisionnels, frais inclus. Elle est fixe ensuite, sans attendre un sommet futur. Une autre variante utilise un ancien pivot confirmé, non cassé et sans revisite observable avant l'entrée.
3. Biais H4 alternatif fondé sur la direction du corps de la dernière H4 complète, avec corps/range minimal de 25 %. Une H4 manquante suspend le contexte ; aucune vieille H4 n'est prolongée artificiellement. Cela remplace les verrous de plusieurs mois dans les variantes concernées, sans prétendre être plus rentable.
4. Comparaison d'un corps de cassure minimal de 1 ATR et de 0,5 ATR. Les pivots de cassure, la POI et la consommation du premier retour restent ceux de la logique héritée.
5. Contrôles communs : risque prévu de 250 € coûts prévus compris, capital de départ de 100 000 €, une entrée par jour UTC, pause de 24 h après deux pertes, levier maximal 10, interdiction des nouvelles entrées de 15 h 30 à 17 h Europe/Paris.
6. Sessions explicites : entrées 08–16 h UTC, sortie après 120 minutes au plus ou à 16 h UTC. Ces modifications font partie d'un nouveau protocole ; l'écart avec la référence n'est pas attribuable à la seule cible.

## Expérience bornée et sélection

Les cinq variantes et leurs paramètres ont été enregistrés dans `run_v02_01/FREEZE_BEFORE_RESULTS.json` avant leurs résultats. Il n'y a eu aucune recherche de seuil supplémentaire après observation de ces résultats. Une seconde exécution, `run_v02_02`, vérifie la version finale après correction d'un chemin d'API sans cache de structures partagé. Ce chemin n'était pas utilisé par les premiers calculs. Les résultats et journaux financiers des deux exécutions sont identiques ; le fichier source antérieur est conservé dans `source_snapshots/v02_01/strategy.py`.

- Développement : premier semestre 2021.
- Vérification chronologique : troisième trimestre.
- Vérification finale sur 2021 : quatrième trimestre.
- Sélection : uniquement les résultats du développement ; minimum 20 trades clos, net positif, profit factor ≥1,2, drawdown sur clôtures ≤5 000 €, aucune interruption pour état inconnu. Classement préétabli par net/drawdown.

Ces seuils sont des critères exploratoires, pas une preuve statistique. **Toute l'année 2021 avait déjà été consultée avant ce travail. Les deux vérifications ultérieures ne sont donc pas un véritable échantillon indépendant.** Le seuil historique de 100 trades clos pour envisager une interprétation de performance n'est atteint par aucune variante.

Aucune variante n'est admissible : A n'a qu'un trade sur le développement ; B, C et D y perdent de l'argent ; E y perd de l'argent avec un seul trade. Le programme ne choisit pas une variante par défaut quand ces conditions échouent.

## Année 2021 en continu, après frais

Une vérification supplémentaire a rejoué l'année entière avec continuité du solde, des séries de pertes et des pauses entre trimestres. Elle a conservé exactement les mêmes variantes. Ce tableau provient de cette exécution annuelle, pas d'une somme arbitraire de périodes ou de journées indépendantes.

| Variante | Trades clos | Gains / pertes | Net observé | Profit factor | Drawdown sur clôtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| A — biais structurel original, cible 2R | 3 | 2 / 1 | +201,22 € | 1,80 | 250,02 € |
| B — impulsion H4, corps ≥1 ATR, cible 2R | 11 | 4 / 7 | −608,81 € | 0,57 | 1 184,14 € |
| C — impulsion H4, corps ≥0,5 ATR, cible 2R | 20 | 7 / 13 | −1 055,13 € | 0,62 | 1 555,64 € |
| D — impulsion H4, corps ≥0,5 ATR, cible 1,5R | 20 | 7 / 13 | −1 208,94 € | 0,56 | 1 583,22 € |
| E — impulsion H4, ancienne cible structurelle connue | 1 | 0 / 1 | −249,67 € | 0,00 | 249,67 € |

Les 3 trades de A ne permettent pas de conclure à un avantage. Le gain n'est que de 0,20 % du capital de référence sur ce flux observé. Les variantes plus actives ne deviennent pas rentables grâce au seul déblocage des entrées.

Le drawdown présenté porte uniquement sur les soldes après clôture. Il ne mesure pas le creux intraposition, ni les règles de perte journalière d'une prop firm. Le budget de risque est prévu à l'entrée ; les variations de change et gaps peuvent produire une perte effective supérieure à 250 €.

## Sensibilité aux coûts

La commission a été multipliée par 1,5 et le glissement de marché par 2 pour les mêmes cinq candidats. Le spread observé du cache reste appliqué. La quantité et la cible en R sont recalculées avec ces coûts supposés connus ; il ne s'agit pas seulement d'une soustraction après coup.

| Variante | Net annuel avec coûts augmentés | Trades |
| --- | ---: | ---: |
| A | +173,09 € | 3 |
| B | −654,68 € | 11 |
| C | −1 154,59 € | 20 |
| D | −1 287,61 € | 20 |
| E | −249,70 € | 1 |

Ce stress n'établit pas une robustesse économique de A : son échantillon reste de trois trades. Il n'explore ni spread de crise supplémentaire ni distribution stochastique des glissements.

## Données manquantes et portée des chiffres

Le cache fourni conserve ses lacunes et son heure en quarantaine. Aucune minute n'a été interpolée ; aucun gagnant ou perdant n'a été retiré à partir de son résultat futur. Une entrée potentiellement cachée ou un trou pendant une position entraîne l'arrêt de la branche continue et un total inconnu.

Les dix vérifications annuelles V02 (cinq variantes, deux scénarios de coûts) n'ont pas rencontré d'état actif non résolu. **Cela certifie seulement la reconstitution des chemins choisis sur le flux observé, pas la complétude de l'année de marché.** Le champ `market_period_certified` reste faux. Les lacunes peuvent avoir empêché la formation de signaux en amont.

Les expériences par journées indépendantes livrées dans `run_v02_02/RESULTS.json` sont séparées : capital réinitialisé chaque jour et aucune pause interjournalière. Leur `portfolio_net_eur` est toujours nul au sens JSON (`null`), car elles ne représentent pas un portefeuille annuel. Elles ne servent pas à la sélection.

## Validation logicielle

**19 tests exécutés, 19 réussis, zéro échec et zéro test ignoré.** Le journal est dans `TESTS_V02.txt`.

Ils couvrent notamment : absence d'effet des prix futurs sur les pivots/cassures déjà connus ; absence d'effet du futur sur la cible d'entrée ; bid/ask et commissions ; quantité par pas et risque prévu ; priorité au stop ; gaps et conservation des frais déjà connus ; cible structurelle revisitée ; suspension H4 ; une entrée par jour ; pause de 24 h ; changement d'heure Paris ; sortie à échéance sans lecture des extrêmes futurs ; sélection indépendante des résultats ultérieurs.

Un audit supplémentaire recalcule indépendamment les flux des **110 lignes de trades annuels**, cinq variantes et deux scénarios de coûts, directement depuis les quotes bid/ask. Écart maximal avec le moteur : **0 €**. Il contrôle aussi le risque prévu, les pas de quantité, le solde continu, la limite journalière et la pause. Ce décompte inclut des variantes/scénarios corrélés ; ce ne sont pas 110 observations indépendantes. Voir `AUDIT_CASH_FLOWS.json`.

Les fichiers de référence ont leur SHA256 d'origine. Le cache est lu après vérification de son identité, avec une liste explicite de types pickle autorisés et validation du schéma. Les 408 pièces de l'archive originale ont été vérifiées avant et après le développement et sont conservées hors du dépôt.

## Décision et suite nécessaire

Le statut livré est `RESEARCH_ONLY_NO_QUALIFIED_CANDIDATE` et `live_trading_enabled=false`. Aucun candidat n'est présenté comme rentable ou recommandé pour le réel.

Le prochain apport utile est un historique bid/ask de meilleure qualité, avec calendrier/horloge documentés et une période encore inutilisée. Il faudra alors évaluer une hypothèse préfixée sur davantage d'occasions. Continuer à retoucher les mêmes cinq variantes jusqu'à rendre 2021 positif ne constituerait pas une amélioration démontrée.

## Pièces reproductibles

- `run_v02_01/FREEZE_BEFORE_RESULTS.json` : protocole et identités avant le premier calcul.
- `run_v02_02/RESULTS.json`, `TRADES.csv`, `DECISIONS.csv` : vérification finale par période et diagnostics séparés.
- `annual_v02_02/PLAN_BEFORE_ANNUAL_RESULTS.json` : plan des vérifications annuelles sans nouvelle variante.
- `annual_v02_02/ANNUAL_RESULTS.json`, `TRADES.csv`, `DECISIONS.csv` : année continue et stress.
- Chaque dossier de calcul possède son manifeste SHA256 ; commandes dans le README.
