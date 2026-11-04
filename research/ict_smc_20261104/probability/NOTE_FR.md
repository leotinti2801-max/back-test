# Probabilité avant entrée : diagnostic, pas permission d'augmenter la mise

Ce module ne calcule aucun nouveau signal, ne charge aucun prix et ne lance
aucun backtest. Il reçoit les trades clôturés du **même scénario**. À l'entrée
`t`, il utilise seulement les résultats dont `closed_at_ms <= t`, selon l'ordre
du moteur : la clôture déjà connue est traitée avant la nouvelle entrée. Une
position ouverte ou non résolue ne contribue pas ; un résultat futur n'est
même pas lu. Un gain signifie `net_eur > 0`, frais déjà inclus. Un zéro est
un non-gain, mais reste séparé des pertes.

La fréquence empirique vaut `wins/n`. La moyenne de Laplace
`(wins+1)/(n+2)` est fournie comme **diagnostic lissé**, sans prétendre qu'un
a priori Beta(1,1) représente le marché. Sans observation, cette valeur vaut
0,5 par construction ; la fréquence empirique et les bornes restent `null`.

L'intervalle nominal Wilson95 utilise `z=1,959963984540054`. Il est descriptif :
les trades Forex peuvent être dépendants, le régime peut changer, et2021 a
déjà servi au développement. La couverture binomiale nominale ne certifie donc
ni une chance conditionnelle de gain du prochain setup ni la calibration d'un
score ICT. Le minimum100 clôtures est un seuil de revue, pas une preuve de
rentabilité ou une calibration indépendante.

**Le multiplicateur de risque reste toujours1, et `probability_tradeable`
reste faux.** Le budget du lanceur reste125 EUR/trade et son plafond prévu
500 EUR/jour. Même200 gains historiques ne déverrouillent pas une hausse.
Passer simplement `independent_calibration_verified=True` lève une erreur :
ce module ne possède aucun modèle ni artefact de calibration indépendant.
Un futur système adaptatif devra implémenter et vérifier ces pièces ainsi que
les plafonds de risque avant de changer les tailles. Aucune règle de Kelly
ni transformation du nombre de confluences en pourcentage n'est ajoutée.

L'espérance observée publiée est directement la moyenne des résultats nets
antérieurs. Elle ne constitue pas une prédiction conditionnelle du prochain
trade. Augmenter les lots d'après cette moyenne ou le win rate global après
le backtest introduirait une information future ; le module l'empêche au
niveau de la collecte et ne décide aucune exposition supplémentaire.

Interface : `summarize_prior(trades, entry_ms,
independent_calibration_verified=False)` dans `prior.py` ; sortie JSON sans
NaN. Les tests synthétiques vérifient l'exclusion du futur, l'ordre de clôture,
les zéros, les bornes, l'immutabilité et le blocage des mises adaptatives.
