# Indicateurs EURUSD : formules vérifiées, limites et disponibilité

Lecture ciblée du 4 novembre 2026 : huit fichiers officiels, six fonctions
TA-Lib, un en-tête TA-Lib et le schéma de prix OANDA. Les copies et SHA256 sont
dans [SOURCE_REGISTER.json](SOURCE_REGISTER.json). Aucun code actif modifié,
aucune stratégie concurrente, aucun backtest ou réglage ajouté.

Ces sources établissent des calculs et des conventions de données. Elles ne
mesurent aucun avantage EURUSD et ne valident pas le passage des deux phases
FTMO en moins d'un mois.

## Calculs contrôlés

Dans les formules, `N` est un nombre de bougies, `C/H/L` leurs prix de
clôture/haut/bas, et `Wilder(x,N)` le lissage de coefficient `1/N` après une
initialisation par moyenne. Le choix de bid, ask ou midpoint doit être explicite.

| Indicateur et source officielle | Formule vérifiée | Apport descriptif et limite |
| --- | --- | --- |
| [EMA](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_EMA.c#L130) | `EMA_t = α C_t + (1−α) EMA_(t−1)`, `α=2/(N+1)`. La copie initiale utilise la moyenne des N premiers prix de sa fenêtre de calcul. | Résume le niveau/la direction passée avec retard. Un croisement ne démontre pas une continuation rentable; changer la fenêtre de départ modifie la graine. |
| [RSI](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_RSI.c#L144) | `g=max(ΔC,0)`, `l=max(−ΔC,0)`; moyennes initiales sur N variations, puis Wilder. `RSI=100 G/(G+L)`. La copie consultée renvoie 50 si les deux moyennes sont nulles. | Compare les hausses et baisses récentes. Un RSI élevé n'implique pas une baisse prochaine. Le cas plat et l'initialisation dépendent de la version : ne pas supposer un résultat identique entre plateformes. |
| [ATR](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_ATR.c#L136) | `TR=max(H−L, abs(H−C_préc), abs(L−C_préc))`; ATR initial = moyenne de N TR, puis `ATR_t=((N−1)ATR_préc+TR_t)/N`. | Mesure une amplitude, sans direction. Exprimé en unités de cotation, pas en euros de risque. Un stop en multiples d'ATR ne fixe le risque monétaire qu'avec une taille et une conversion cohérentes. |
| [ADX](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_ADX.c#L145) | `up=H−H_préc`, `down=L_préc−L`; `+DM=up` seulement si `up>down` et `up>0`, et réciproquement pour −DM. DM et TR sont lissés par Wilder; `±DI=100 S(±DM)/S(TR)`; `DX=100 abs(+DI−−DI)/(+DI+−DI)`. ADX = moyenne initiale de N DX puis Wilder. Le code protège les dénominateurs nuls. | L'écart est pris en valeur absolue : ADX décrit l'intensité, pas le sens. Son double lissage crée une latence. Un seuil ADX universellement rentable n'est pas établi par ce code. |
| [Bollinger Bands](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_BBANDS.c#L218) et [STDDEV](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_STDDEV.c#L133) | Pour le cas SMA : milieu = moyenne de N prix; `σ=sqrt(Σ(C−moyenne)²/N)`; haut = milieu + `k_up σ`, bas = milieu − `k_down σ`. Le code utilise le diviseur N, sans correction N−1. D'autres types de moyenne centrale sont possibles. | Une enveloppe de dispersion n'impose pas le retour à sa moyenne. « ±2σ » ne garantit pas 95 % de couverture ni une probabilité de gain : ces interprétations demanderaient d'autres hypothèses et une validation. |

La normalisation ADX ne donne pas une probabilité; l'ATR ne donne pas une
prévision directionnelle. EMA et Wilder ont des coefficients différents à N
identique. Les valeurs par défaut d'une bibliothèque ne sont pas des paramètres
optimaux pour EURUSD.

## Warm-up : premières valeurs et stabilisation

Les fonctions de lookback de la copie TA-Lib consultée donnent les indices
suivants, comptés depuis zéro :

| Fonction | Premier indice autorisé par son lookback |
| --- | --- |
| EMA(N) | `N−1+U_EMA` |
| RSI(N) | `N+U_RSI` |
| ATR(N) | `N+U_ATR` |
| ADX(N) | `2N−1+U_ADX` |
| BBANDS(N) | `max(lookback de la moyenne centrale, lookback STDDEV)`; `N−1` pour le chemin SMA inspecté |

`U` désigne le supplément « unstable » renvoyé par le mécanisme de la version et
du réglage effectifs. Les appels de la branche `main` l'intègrent explicitement.
L'en-tête [ta_global.h](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_common/ta_global.h)
confirme l'existence de réglages par fonction, mais ne suffit pas à résoudre leur
politique par défaut. Ce point reste à vérifier sur la version effectivement
installée avant toute intégration; on ne suppose donc pas `U=0`.

Sous un réglage `U=0` explicitement vérifié, EMA(14) réclame 14 prix,
RSI(14)/ATR(14) 15 prix et ADX(14) 28 prix pour leur première valeur. C'est un
minimum de calcul, pas une garantie de convergence ni une recommandation de
période. Les récurrences conservent l'influence de leur graine; un historique
plus long peut donner une valeur différente. Ne pas remplacer les valeurs
indisponibles par zéro ni réinitialiser chaque matin sans déclarer ce choix.

## Confirmation et prix utilisables

Le calcul d'une fonction TA-Lib ne connaît pas l'heure réelle de disponibilité de
la bougie. Une observation OHLC d'une M5 complète ne peut alimenter une décision
qu'après sa clôture; l'exécution doit utiliser une cotation disponible ensuite.
Cela découle de l'information consommée par les formules, pas d'une promesse de
la bibliothèque. Employer le haut final d'une bougie encore en cours introduirait
de l'information future.

Le [schéma officiel OANDA](https://github.com/oanda/v20-openapi/blob/master/yaml/v20.yaml#L3009)
précise que `time` est le **début** de la bougie et offre un indicateur
`complete`. Il distingue bid, ask et midpoint. Il définit aussi `smooth=true`
comme une ouverture remplacée par la clôture précédente : ce réglage change
les bougies. Ces conventions doivent être qualifiées pour le fournisseur réel;
elles ne peuvent pas être supposées dans le cache utilisateur.

Le même [schéma de cotation](https://github.com/oanda/v20-openapi/blob/master/yaml/v20.yaml#L12387)
prévoit un état négociable, des listes bid/ask avec liquidité et la possibilité
qu'un côté soit vide. Ses prix `closeoutBid/Ask` ne servent jamais à ouvrir une
position. Des indicateurs calculables sur midpoint ne certifient donc pas une
entrée disponible à ce midpoint, une quantité exécutable ou l'absence de
slippage. Le schéma décrit une API OANDA; ce n'est pas une mesure de qualité des
exécutions du courtier FTMO.

## Volume et VWAP : distinction conservée

OANDA définit précisément `Candlestick.volume` comme « The number of prices
created during the time-range represented by the candlestick ». C'est un
compte de prix du flux, **pas une quantité négociée**, et il ne fournit pas le
volume global du Forex. Pondérer des prix par ce champ produit une mesure
pondérée par l'activité de ce flux; cela ne permet pas d'annoncer un VWAP global
Forex. La nature d'un éventuel champ volume d'un autre fournisseur reste à
vérifier indépendamment.

Aucune source primaire dédiée à VWAP ni aucune qualification du volume du cache
utilisateur n'a été lue dans ce cycle : **VWAP reste à vérifier et n'est pas
retenu comme donnée fiable ici**. Huit documents ciblés ont été consultés; la
collecte s'arrête à cette borne. Les URLs de branches sont mutables et les
empreintes fixent seulement les octets réellement archivés. Proxy hérité et TLS
vérifié ont été conservés; aucune destination refusée n'a été contournée.
