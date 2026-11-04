# Audit indépendant des résultats ICT/SMC

**PASS : quatre cellules contrôlées, une seule entrée de marché unique,
écart maximal de recomposition cash égal à0EUR.** Les quatre cellules sont
le trimestre et l'année exploratoire, chacun en coûts de base et renforcés.
Elles ne représentent pas quatre observations indépendantes.

L'audit n'appelle ni simulateur de portefeuille ni `X.structural_path`. Il lit
les sorties existantes et le cache reconnu par SHA256/taille/schéma, recompose
uniquement le fillTP enregistré à partir des quotes fixes d'entrée et de sortie,
des demi-commissions et du change de chaque flux. Le script reproductible est
`audit_recorded_results.py`, avec preuves dans `AUDIT_RESULTS.json` et
`RECORDED_FILL_RECONCILIATION.csv`.

## Trade effectivement observé

Vente du6janvier2021 à13:00UTC, TP inscrit clos à13:57UTC. La quote d'exécution
de sortie appartient à la M1 commençant13:56UTC ; le moteur inscrit la clôture
à sa fin. Cela ne certifie pas une heure de fill au tick.

| Élément | Base | Coûts renforcés |
| --- | ---: | ---: |
| Prix d'entrée exécuté | 1,23396 | 1,23395 |
| Stop original | 1,23457 | 1,23457 |
| Cible ask de l'autre borne du range | 1,23223 | 1,23223 |
| Quantité EUR | 230000 | 214000 |
| Risque prévu EUR | 124,87996 | 123,99665 |
| Ratio net de cotation prévu | 2,50746 | 2,30070 |
| Net cashEUR reconstitué | +313,50570699 | +285,62225804 |

Les différences de taille viennent des coûts et du risque au stop, pas d'une
probabilité de gain plus élevée. La taille recomposée respecte l'arrondi au pas,
le minimum, le plafond de levier du modèle et le budget125EUR.

L'entrée est dans le FVG à la première quote. Le pivot MSS était confirmé avant
le sweep, le MSS et le FVG sont connus avant le retour, et les délais sont
inférieurs ou égaux à30min à chaque étape. Le stop est bien l'extrême ask
exécutable du sweep plus un tick. La cible correspond au bas ask du range
08–09h Londres, connu avant l'entrée ; son dépassement d'un tick est vérifié
dans la M1 de sortie. Aucun stop concurrent n'est touché dans cette M1.

## États du compte et probabilités

Les journaux sont cohérents avec une entrée et une clôture, sans perte, sans
chevauchement et sans arrêt pour exposition inconnue. Le budget quotidien reste
inférieur à500EUR et le nombre d'entrées à quatre. La pause après deux pertes
n'est pas exercée par ce seul trade ; elle reste dans le moteur inchangé et
ne doit pas être présentée comme nouvellement éprouvée sur ce résultat.

Avant l'unique entrée, le nombre de trades clos antérieurs est **zéro**. La
fréquence lissée0,5 est un prior descriptif, pas une prévision validée. Le
premier trade ne pouvait donc pas être sélectionné ou grossi sur son propre
résultat. Aux refus suivants, un seul trade gagnant antérieur est disponible ;
le seuil100 n'est pas atteint. Les flags de calibration et de probabilité
tradable restent faux, et le multiplicateur de risque vaut1 partout.

Les23 fichiers du résultat et les identités de source du gel ont été vérifiés.
Les soldes, nets, enveloppes de liquidation et compteurs d'événements concordent.
Toutes les minutes observées entre entrée et sortie sont présentes. Aucun
chemin alternatif n'est généré par l'audit et aucun frais n'est déduit deux fois.

## Portée des comparaisons

La comparaison homologue du trimestre est : ICT+313,51EUR contre range2R
+839,28EUR en base ; ICT+285,62 contre+719,24EUR en renforcé. Le net annuel
ICT est identique parce que l'unique trade est déjà dans ce trimestre. Il ne
faut pas comparer ce total annuel ICT au préfixe annuel incomplet d'une autre
stratégie, ni compter le même trade une seconde fois comme nouvelle preuve.

L'absence d'arrêt annuel concerne **l'exposition de ce parcours simulé**.
Elle ne certifie pas l'ensemble des opportunités de marché : six séances ont
des trous de signal et trois ranges sont incomplets. Ces journées restent
étiquetées inconnues ou annulées pour données, pas « sans signal de marché ».

Un seul gain sur un seul trade ne fournit pas une probabilité fiable ni une
justification de hausse des lots. Aucun succès FTMO, equity contractuelle,
ordre réel, absence générale de pertes ou rentabilité future n'est certifié.
