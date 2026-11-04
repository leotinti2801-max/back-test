# Contexte graphique et prolongation 2R → 3R+ — garde-fous

Note du 4 novembre 2026. Aucun backtest, HTTP ou changement du bot. Une
explication graphique reste une hypothèse : H1, EMA20 et ATR14 doivent être
calculés sur des barres closes disponibles à l'entrée, avec chauffe suffisante.
Contexte incomplet = inconnu, jamais une valeur inventée.

## Comparer le filtre sans masquer son coût

Garder dates, risque EUR, stop, cible, horaires, position unique, quotas et pause
identiques. Séparer l'essai du filtre à cible inchangée du nouveau portefeuille
TP2 : changer filtre et TP simultanément mélange leurs effets. Le filtre et ses
paramètres sont annoncés avant les résultats, y compris s'il produit zéro trade.

Publier ensemble occasions, refus, inconnues, entrées, fréquence par séance,
exposition, clôtures positives/négatives/nulles, net EUR, gains/pertes moyens et
drawdown. **Moins de pertes absolues peut seulement signifier moins de trades.**
Taux de pertes = pertes nettes / toutes les clôtures résolues ; les neutres
restent au dénominateur. Taux de TP et taux de gains nets sont distincts.

Zéro trade : taux de gain, taux de perte et espérance par trade `null`, pas
0 % ou 100 %. Net zéro seulement si la période est résolue sans exposition
inconnue. L'abstention ne démontre ni avantage ni progression vers FTMO.

Le pilote rejoue le portefeuille entier : un refus change occupation et pauses,
donc les entrées suivantes. Apparier les entrées par heure et direction :

```
delta net = différences sur entrées communes
          + net des entrées propres au filtre
          - net des entrées propres au témoin
```

Dans les trades propres au témoin, montrer **pertes retirées ET gains sacrifiés**,
puis leur total ; montrer aussi gains/pertes des nouvelles entrées du filtre.
C'est un rapprochement des parcours observés, sans résultat inventé pour les
autres refus.

## Espérance et force des preuves

Espérance empirique = somme des nets EUR / clôtures résolues ; publier aussi
les R cash individuels et leur moyenne. Le gain moyen réellement encaissé ne
peut être remplacé par le TP prévu. `Taux de gain × gain moyen − taux de perte
× perte moyenne absolue` retrouve le net moyen, neutres inclus. Frais déjà
inclus : aucune double déduction.

Les coûts peuvent changer quantité, cible, signe net et pauses : base/stress
ont leurs propres parcours et ne sont pas deux échantillons indépendants.
Tout 2021 est du développement déjà consulté. Afficher effectifs et concentration
par séance ; périodes chevauchantes et essais répétés ne créent pas de données
nouvelles. Une estimation d'incertitude doit respecter la dépendance par séances
et pauses ; peu de blocs ou de trades = inconclusif. Cent clôtures est un seuil
de revue existant, aucune preuve automatique de précision ou de 80 % de gains.

## Portefeuille TP2 et continuation : deux objets

**TP2 réellement simulé :** le pilote produit un nouveau portefeuille dont le TP2
est la vraie sortie, avec ses soldes, pauses et entrées ultérieures. Extraire des
gagnants du portefeuille TP3 ne reconstitue pas ce portefeuille TP2.

**Continuation diagnostique :** après chaque TP2 exécuté dans ce nouveau
portefeuille, observer séparément une position hypothétique conservant le
**stop original**, jusqu'à **16:00 Europe/London**, pour **3R, 4R et 5R**.
Aucun break-even, trailing, stop relevé ou sortie partielle ajouté. Succès = seuil
atteint avant stop original et échéance. Les diagnostics 4R/5R ne s'arrêtent pas
parce que 3R aurait réussi ; un seuil atteint après le stop n'est pas un succès.

La continuation ne change aucun cash, trade, quota ou pause réels du portefeuille
TP2. Son avenir ne sert jamais au filtre ni au choix rétrospectif des contextes.
Si un cash hypothétique est publié, garder l'entrée et ses frais une seule fois :
la branche maintenue ouverte ne liquide pas à TP2 puis ne se rouvre gratuitement.

## Définir R, l'exécution et les inconnues

| Grandeur | Convention explicite |
| --- | --- |
| Distance prix | `D = direction × (entrée − stop original)`. |
| Niveau de prix planifié kR | Formule actuelle : `entrée + direction × [k × (D + commission + glissement) + commission]`, différente de `entrée + direction × kD`. |
| R cash réalisé | `net EUR / risque EUR réellement dimensionné à l'entrée`, avec quantité arrondie et FX effectif. Si normalisation par budget 125 EUR, l'étiqueter autrement. |

Toucher le niveau prévu 3R ne garantit pas +3R cash en EUR. Chaque scénario de
frais conserve ses seuils propres. Contrôler bid pour liquider un long, ask pour
un short, avec la confirmation d'un tick du moteur : une mèche mid ne suffit pas.

Annoncer le premier instant observable après TP2. Les OHLC de la M1 du fill
ne donnent pas l'ordre intraminute : ne pas utiliser toute sa mèche comme
mouvement certain après le fill. Convention prudente possible : démarrer à
`closed_at_ms`, minute suivante pour un TP, et signaler l'intraminute non identifié.
Stop et seuil possibles dans une même M1 = ambiguïté ; une priorité au stop est
une convention prudente, pas une preuve tick par tick. Trou de quotes = inconnu.

Pour chaque seuil, publier : TP2 éligibles `N`, succès avant stop/16 h `S`, stop
avant seuil, échéance sans seuil, inconnues `U` et ambiguïtés. Ne pas supprimer
les inconnues du dénominateur. `S/N` à `(S+U)/N` encadre descriptivement la
proportion compatible avec elles ; aucun intervalle de confiance n'en découle.
Échéance sans seuil = non-succès connu à cet horizon ; stop = événement concurrent,
pas censure indépendante. Ne pas supposer les trous aléatoires/non informatifs.

Rapporter `N3/N2`, `N4/N2`, `N5/N2` puis éventuellement `N4/N3`, `N5/N4`, avec
inconnues. La question est conditionnelle aux TP2 observés. Elle ne mesure ni
probabilité d'une nouvelle entrée, ni espérance d'un portefeuille TP3/4/5 rejoué,
ni passage FTMO. Conserver résultats défavorables et zéro-trade ; promotion
conditionnée au net après frais, fréquence utile à risque inchangé, données
indépendantes et clauses FTMO vérifiées.
