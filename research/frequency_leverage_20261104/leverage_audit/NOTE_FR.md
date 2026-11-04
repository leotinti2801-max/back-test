# Audit du levier des trades V03 existants — 4 novembre 2026

**Le plafond de levier 10 ne limite aucune des tailles observées.** Le porter
à 30 ou 100, en conservant le budget de risque de 125 EUR et le même stop,
ne change la quantité d'aucun des 61 trades trimestriels, en coûts de base comme
en coûts renforcés. Cela réduit seulement la marge théorique réservée pour ces
tailles. Aucun nouveau backtest ni HTTP n'a été réalisé.

## Périmètre et méthode

Lecture des témoins `V03_base_TRADES.csv` et
`V03_higher_costs_TRADES.csv` dans
`research/indicator_study_20261104/lab/comparison_01/` : du 4 janvier au
1er avril 2021, fin exclue. Les deux scénarios portent sur les mêmes 61 entrées ;
les 122 lignes d'audit ne sont pas 122 observations indépendantes. C'est du
développement sur 2021 déjà consulté, pas une nouvelle validation.

Le cache a été chargé par le lecteur existant : taille et SHA256 contrôlés,
désérialisation sur liste autorisée, schéma validé. Le `mid_open` de chaque
entrée vient de sa minute réellement présente dans le cache, sans approximation
à partir du prix d'exécution. Le protocole actif est identique au protocole gelé
de la comparaison. Le solde avant chaque entrée est reconstruit du journal.

Avec `fx = mid_open`, `d = direction × (entrée − stop)`, le moteur utilise :

```
risque unitaire EUR = (d + commission aller-retour + glissement) / fx
quantité budget = 125 / risque unitaire EUR
quantité plafond = levier plafond × solde avant entrée × fx / prix entrée
quantité exécutée = plancher(min(quantité budget, quantité plafond) / 2000) × 2000
levier effectif du modèle = quantité exécutée × prix entrée / fx / solde
```

`X.size_position` a été appelé pour contrôler ces tailles et les scénarios
10/30/100 ; aucune trajectoire de prix ni suite de signaux n'a été simulée.
Les contrôles des prix d'entrée bid/ask plus glissement, quantités, risques
prévus et soldes retrouvent exactement les CSV : écart maximal **0**.

## Résultat sur les entrées exécutées

| Mesure | Coûts de base | Coûts renforcés |
| --- | ---: | ---: |
| Trades contrôlés | 61 | 61 |
| Quantité minimale / maximale, EUR de base | 30 000 / 150 000 | 30 000 / 142 000 |
| Levier effectif moyen | 0,6304× | 0,6162× |
| Levier effectif maximal | **1,4894×** | **1,4108×** |
| Plafond 10 inférieur à la quantité budget avant arrondi | **0/61** | **0/61** |
| Plafond 10 réduisant effectivement la quantité arrondie | **0/61** | **0/61** |
| Risque prévu réellement dimensionné, min–max EUR | 120,01–124,93 | 117,78–124,99 |
| Tailles modifiées avec plafond 30, risque inchangé | **0/61** | **0/61** |
| Tailles modifiées avec plafond 100, risque inchangé | **0/61** | **0/61** |

Le risque réellement dimensionné peut être inférieur à 125 EUR à cause du pas
de quantité de 2 000 EUR. Sur ces entrées, la quantité non arrondie que permettrait
le plafond 10 est proche d'un million d'EUR ; le budget de risque n'en autorise
qu'environ 31 000 à 150 000. Le budget et la distance au stop sont donc les
contraintes de taille actives. Le maximum de levier effectif survient le
11 février 2021 à 09:10 UTC dans les deux scénarios.

## Marge : calcul de modèle, pas relevé MT5

Le proxy de notionnel utilisé pour inverser la formule du plafond est
`quantité × entrée / fx`. Marge initiale proxy = notionnel / plafond ; marge
libre proxy = solde avant entrée − marge initiale proxy.

| Plafond hypothétique | Marge initiale maximale proxy, base / stress | Marge libre minimale proxy, base / stress |
| --- | ---: | ---: |
| 10 | 15 000,31 / 14 200,41 EUR | 85 713,80 / 86 457,68 EUR |
| 30 | 5 000,10 / 4 733,47 EUR | 95 714,00 / 95 924,62 EUR |
| 100 | 1 500,03 / 1 420,04 EUR | 98 768,79 / 98 790,07 EUR |

Ces maxima et minima peuvent concerner des entrées différentes. Le proxy part
d'un compte à plat avant l'entrée, avec une seule position permise. Il ne
modélise pas une equity MT5 après spread, commission et latent instantané.
Le moteur ne possède pas ici un compte de marge réglementaire/courtier vérifié.
Taille du contrat, calcul de marge réel, paliers, marge-call/stop-out et règles
de conversion doivent être obtenus depuis les spécifications du symbole MT5.
La disponibilité officielle de 30 ou 100 pour le produit FTMO demandé reste
**inconnue** ; type Standard/Swing non confirmé dans les sources de cet audit.

## Conséquence pour la prochaine recherche

Les scénarios 30 et 100 à risque monétaire inchangé sont utiles pour documenter
une sensibilité de marge, mais ils ne constituent pas ici un levier d'amélioration
du nombre d'entrées ou du cash gagné. Augmenter le plafond autorisé et augmenter
le risque engagé sont deux décisions différentes. Une quantité plus élevée
avec le même stop augmente le risque en euros ; elle ne produit pas un meilleur
signal ou un meilleur taux de réussite.

Le témoin trimestriel refuse notamment 104 signaux pour position ouverte et
33 pour pause après pertes, avec des motifs éventuellement simultanés. Aucun
refus `SIZE_BELOW_MINIMUM` n'est rapporté. Le nombre d'entrées réellement
observé reste au plus deux par jour malgré quatre autorisées. Pour chercher
plus d'entrées, l'analyse utile porte donc sur l'occupation du compte, les
sorties horaires et la formation des nouveaux signaux, sans empiler l'exposition
ni augmenter le risque par défaut. Le présent audit ne teste aucune modification
de ces règles et n'attribue aucun gain hypothétique aux refus.

Tout futur essai garde une seule stratégie, un budget explicite, les coûts et
les critères de rejet annoncés ; les contraintes d'equity FTMO et les clauses
officielles restent à vérifier. Ni réussite des deux phases en moins d'un mois,
ni rentabilité future ne sont établies par ce calcul de tailles.

Pièces : `LEVERAGE_AUDIT.json`, `EXISTING_TRADES_LEVERAGE_AUDIT.csv` et
`MANIFEST_SHA256.json`. Aucun fichier du bot, profil ou résultat antérieur modifié.
