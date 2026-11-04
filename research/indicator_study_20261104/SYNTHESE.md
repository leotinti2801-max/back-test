# EURUSD : supports, résistances et indicateurs — 4 novembre 2026

**Le filtre de tendance EMA20/50 testé dégrade les résultats. Il est écarté.**
Le bot V03 de 32 lignes reste le témoin actif, avec ses paramètres inchangés.
MT5 est enregistré dans le profil du compte ; le dossier et les confirmations
déjà fournis ont été repris. Objectif : FTMO 2-Step, 100 000 EUR, EURUSD seul,
moins d'un mois pour les deux phases si réalisable. Cet objectif n'est pas validé.

## Résultat concret du nouvel essai

Une seule modification préannoncée : accepter une cassure acheteuse si
EMA20 > EMA50, vendeuse si EMA20 < EMA50, sur la M5 qui vient de clôturer.
Égalité : refus ; valeur indisponible après une coupure : refus pour information
inconnue. Les cassures et le réarmement restent déterminés par les prix.
Le [plan](lab/SINGLE_COMPARISON_PLAN.json) et le gel précèdent les résultats.

Période commune : **4 janvier au 31 mars 2021 inclus**, développement déjà
consulté, choisi en connaissance du trou d'avril. Les positions, pauses et
quotas sont entièrement rejoués ; aucun perdant n'est simplement retiré du CSV.
Le stop de range, la cible prévue 3R, le risque 125 EUR et le plafond prévu
500 EUR/jour restent identiques. Toute exposition inconnue aurait interrompu
la branche ; aucune n'est apparue sur cette période pour ces deux variantes.

| Mesure sur cette période | V03 témoin | V03 + EMA20/50 |
| --- | ---: | ---: |
| Trades clôturés | 61 | 53 |
| Gagnants nets / perdants nets | 31 / 30 | 25 / 28 |
| Taux de gagnants nets | 50,8 % | 47,2 % |
| Net après coûts de base | +642,37 EUR | +445,65 EUR |
| Net avec coûts renforcés | +504,22 EUR | +335,89 EUR |
| Drawdown du solde clôturé, base | 420,05 EUR | 533,48 EUR |
| Maximum d'entrées effectivement exécutées/jour | 2 | 2 |
| Sorties stop / horaire / cible | 12 / 48 / 1 | 10 / 42 / 1 |

Le filtre perd **196,71 EUR** relativement au témoin en base et **168,33 EUR**
en coûts renforcés. Il réduit la fréquence et le taux de réussite, et augmente
le drawdown clôturé. Ce drawdown n'est pas un contrôle FTMO d'equity intrajournalière.
Les deux branches restent positives sur ce trimestre, ce qui ne démontre ni
rentabilité future ni capacité à passer les deux phases.

Le témoin reproduit les 61 clôtures de l'ancien préfixe annuel à moins de
1e-8 EUR. Le résultat annuel reste **inconnu** : la position du 1er avril
08:25 UTC rencontre toujours une minute absente à11:40 UTC. L'essai trimestriel
ne répare pas l'historique et ne remplace pas cette conclusion annuelle.

## Pourquoi des entrées et des gains disparaissent

La variante refuse 26 cassures pour sens EMA incompatible et16 pour EMA
indisponible. Ces16 décisions ne sont pas16 mauvais contextes démontrés : la
valeur manque parce que l'historique consécutif est insuffisant. Les vérifications
du compte ne sont pas évaluées après un refus du filtre et sont étiquetées comme
telles ; on ne prétend pas connaître tous les motifs simultanés de ces lignes.

Après le filtre, les autres refus sont : position déjà ouverte78, pause après
deux pertes25, ouverture qui n'est plus au-delà du range2 et première cotation
trop tardive2. Pour le témoin :104,33,2,2. Ce sont des motifs éventuellement
simultanés, pas des comptes de pertes évitées. Le passage au-delà d'un niveau
ne garantit pas qu'une entrée puisse être exécutée.

**45 entrées sont communes,16 appartiennent seulement au témoin et8 seulement
à la variante.** Les pauses et l'occupation du compte changent : la variante
n'est donc pas un sous-ensemble des61 anciens trades. C'est pourquoi retirer
les pertes après coup aurait produit une comparaison erronée.

Chaque perte est listée dans
[EVERY_OBSERVED_LOSS.csv](lab/diagnostic_01/EVERY_OBSERVED_LOSS.csv).
En base, V03 perd12 fois au stop et18 fois à la sortie horaire ; la variante
perd10 fois au stop et18 fois à l'horaire. Ce sont les causes mécaniques
observables, sans cause macroéconomique inventée. Sur les53 trades EMA,
42 finissent à l'horaire et un seul atteint le TP : **viser3R ne signifie
pas encaisser3R**. Les coûts sont déjà inclus dans tous les résultats.

## Ce que l'audit des niveaux établit

Les annotations portent sur les61 clôtures V03, l'entrée non résolue conservée
séparément et142 refus avant l'arrêt annuel. Elles n'attribuent aucun résultat
hypothétique aux refus. Les calculs utilisent uniquement des barres clôturées
au plus tard à la décision ; les résultats des trades sont joints ensuite.

| Information à l'entrée des61 trades clôturés | Disponibilité |
| --- | ---: |
| EMA20, RSI14, ATR14, ADX14, Bollinger20±2 | 61/61 chacun |
| EMA50 | 55/61 |
| Haut/bas exact du précédent jour17h New York | 0/61 |
| Haut/bas exact de la précédente séance Londres08–16h | 60/61 |
| Au moins un ancien niveau opposé devant la dernière quote de sortie | 57/61 |

Les54 journées NY17 distinctes correspondant aux61 entrées ont toutes au moins
une minute absente. Leurs extrema observés restent conservés comme bornes
partielles, jamais comme hauts/bas exacts. Le jour NY17 est une convention
d'étude ; l'heure des bougies du serveur MT5 n'est pas vérifiée.

Les pivots H1 sont stricts, avec deux H1 à gauche et deux à droite, toutes
complètes. Ils deviennent connus à la clôture de la seconde H1 de droite.
Les utiliser à la clôture centrale aurait ajouté deux heures d'information future.

Dans57/61 entrées, un niveau historique opposé est aussi avant ou au TP.
Le choix emploie bid pour un achat, ask pour une vente, comparé au dernier
bid/ask clôturé. Un niveau peut rester devant la quote de sortie tout en étant
derrière le prix payé à cause du spread. Ce tag précède l'ouverture suivante :
un gap à l'entrée peut changer cette géométrie.

Ces niveaux peuvent avoir déjà été revisités ou franchis ; leur état intact
n'est pas qualifié. Aucun niveau connu trouvé ne signifie pas absence certaine
d'obstacle. Le nombre57/61 ne prouve donc pas qu'un filtre support/résistance
améliorerait le bot : un filtre naïf étiquetterait presque toutes les entrées,
y compris potentiellement des gagnantes, sans établir une prévision fiable.

## Rôle utile des familles d'indicateurs

| Famille | Hypothèse utile à examiner | Conclusion de ce cycle |
| --- | --- | --- |
| Supports/résistances H1, séance précédente | Mesurer l'espace jusqu'à un ancien niveau opposé | Annotation codée ; statut intact/inconnu à qualifier avant un filtre. Aucun gain démontré. |
| EMA20/50 | Aligner la cassure avec la tendance récente | Test complet défavorable ; variante écartée, sans retoucher les périodes. |
| ATR14 | Décrire l'amplitude et la place des coûts dans le stop | Calcul disponible ; ATR n'indique pas le sens. Le risque en EUR dépend toujours de la taille et du change. Aucun nouveau stop ATR testé. |
| ADX14 | Décrire l'intensité du mouvement | Calcul disponible ; ADX n'est pas une direction ni une probabilité. Aucun seuil rentable démontré. |
| RSI14 | Décrire l'équilibre hausses/baisses | Calcul disponible ; « suracheté » ne prouve pas un retournement. Aucun filtre70/30 activé. |
| Bollinger20±2 | Décrire la dispersion et la position relative | Calcul disponible ; sortie de bande peut accompagner continuation ou retour. ±2σ ne garantit pas95 % de couverture. |
| MACD/Stochastique | Autres résumés de tendance/position récente | Non testés ; ajout de paramètres sans preuve nouvelle dans ce cycle. |
| Pivots journaliers, Fibonacci, nombres ronds | Références de prix à définir avant l'essai | Non testés ; ancrage, tolérance et complétude restent à spécifier. Aucun pouvoir prédictif affirmé. |
| VWAP/profil de volume | Prix pondéré par un volume défini | Non qualifiés ici : aucun volume global négocié Forex fourni. Le compte de prix d'un flux n'est pas ce volume. |
| Annonces macro | Distinguer périodes et exécution autour des annonces | Il faut un calendrier historique disponible à l'époque et les clauses du produit ; pas de filtre à partir de dates révisées. |

Le catalogue ne constitue pas une recherche exhaustive de toutes les
combinaisons. Accumuler des essais sur2021 augmente la possibilité de choisir
une coïncidence. Le bot garde une seule logique de cassure et aucun nouvel
indicateur actif après cet essai défavorable.

## Sources, versions et vérification

Huit fichiers officiels TA-Lib/OANDA ont été lus et archivés avec leurs
empreintes : [registre et URLs](sources/SOURCE_REGISTER.json),
[formules et limites](sources/NOTE_FORMULES_ET_LIMITES.md).
Ils documentent des calculs et un schéma fournisseur, pas un avantage financier.
Le schéma OANDA ne certifie pas le fournisseur ni le volume du cache utilisateur.

L'exécution isolée utilise Python3.12.14, NumPy2.3.5, pandas2.2.3,
TA-Lib Python0.6.8 et C0.6.4. Compatibilité0, périodes instables0 contrôlées.
Premiers indices calculables : EMA20=19, EMA50=49, RSI14=14, ATR14=14,
ADX14=27 et Bollinger20=19, sur segments M5 complets consécutifs.
Une première valeur calculable n'est pas une preuve de stabilisation.
Après une M5 incomplète, l'initialisation repart ; aucune interpolation.

Le cas RSI sur série constante donne **0 dans la bibliothèque exécutée**,
alors que la branche source actuelle consultée indique50. Les octets source
et la version exécutée sont distingués ; aucune concordance MT5 n'est supposée.
La note de lecture des sources précède ce contrôle du runtime et garde sa
liste initiale de points à vérifier ; les gels du laboratoire donnent les
résultats effectivement vérifiés ensuite.

Neuf tests ciblés passent : invariance aux prix futurs, confirmation des pivots,
réinitialisation après trous, niveaux partiels exclus, week-end/changements
d'heure, bid/ask et égalité au TP, rejet du filtre avant besoin de quote et sans
consommer le quota d'entrées. La revue indépendante a fait corriger trois
erreurs de géométrie avant les annotations. Les hashes du bot et du moteur
sont restés ceux du gel V03 ; les nouveaux scripts sont séparés sous `lab/`.

## FTMO et suite fondée sur les preuves

La [matrice de contraintes](ftmo_checklist/NOTE_FR.md) conserve les clauses
non vérifiées comme inconnues. Le risque prévu500 EUR/jour n'est pas une
certification de la limite quotidienne d'equity. Les enveloppes M1 comprennent
des coûts hypothétiques de liquidation, distincts du calcul contractuel FTMO.
Le brief fournit le projet et l'ancien bot, pas les conditions officielles
datées du compte. L'accès FTMO restait refusé par le proxy ; aucun nouvel essai
identique ni contournement n'a été effectué.

La prochaine étape utile est de récupérer et qualifier les données bid/ask
manquantes et un historique encore inutilisé, puis de définir la validité des
niveaux déjà franchis avant un éventuel essai de filtre H1. L'archive d'avril
identifiée dans `../knowledge_cycle_20261104/data_quality/` reste manquante.
Les champs contractuels et les spécifications du symbole MT5 devront être
vérifiés avant un verdict de passage FTMO. Aucun accès courtier ni ordre réel
n'a été ajouté. Pas de taux80 % annoncé, pas d'augmentation du risque pour
faire paraître le délai atteignable.

Commandes et structure des preuves : [lab/README.md](lab/README.md).
