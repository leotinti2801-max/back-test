# Stratégie Forex minimale — London Range V01

**Une seule méthode, zéro indicateur, 40 lignes pour le signal.** Le moteur de
backtest, les contrôles de risque et les rapports sont séparés. Leur code reste
nécessaire ; le bot complet n'est pas présenté comme un programme de 40 lignes.

## Règles

1. Sur EUR/USD, figer le haut et le bas observés de 08 h à 09 h **Europe/London**.
2. Entre 09 h et midi Londres, attendre une M5 complète qui clôture au-dessus ou
   au-dessous du range. Entrer sur la quote d'ouverture M1 suivante, si le prix
   est toujours au-delà. Les horaires été/hiver sont gérés par la zone IANA.
3. Stop de l'autre côté du range, sur le côté exécutable, plus un tick. Objectif
   prévu à 2R, coûts prévus inclus ; le R cash final dépend aussi de la conversion.
4. Au maximum une tentative par sens et deux par jour, même si une tentative est
   refusée. Une seule position ouverte. Sortie de toute position à 16 h Londres.

Risque prévu maximal : 250 € par trade et 500 € cumulés par jour sur les
100 000 € simulés. Pause de 24 h après deux pertes consécutives. Ces plafonds
sont prévisionnels : un gap et la conversion peuvent produire une perte
effective supérieure. Aucune augmentation du risque par trade n'a été faite.

Les entrées avant midi Londres sont antérieures à l'interdiction 15 h 30–17 h
Europe/Paris dans les conventions des périodes étudiées. Cette règle ne force
pas à clôturer une position ouverte pendant l'interdiction de nouvelles entrées.

## Validation et résultats

34 tests logiciels passent, dont 12 sur cette nouvelle méthode. Ils vérifient les
clôtures, le premier essai de chaque sens, l'horloge, les gaps, la causalité, le
risque, les frais et la pause. Une revue indépendante a identifié deux défauts
de diagnostic qui ont été corrigés ; les CSV financiers restent identiques.

Sur 04/01/2021–18/02/2021, fin exclue : **27 trades, +670,63 € après frais**.
Avec commission ×1,5 et glissement ×2 : +603,82 €.

Le calcul annuel s'arrête le **1er avril 2021 à 11:40 UTC (13:40 Paris)** : une M1
manque pendant une position. Les 49 trades déjà clos donnent −246,39 € ; le net
de l'année est **inconnu**, pas −246,39 €. Le scénario de coûts augmentés a le
même trou, avec −382,62 € sur les seuls trades clos avant l'arrêt.

Cette V01 n'est pas qualifiée FTMO. Les règles officielles ne sont pas encore
vérifiées et 2021 est déjà du développement consulté. Le résultat positif des
45 jours ne démontre pas un avantage stable ; la fenêtre courte est incluse
dans l'année et ne s'ajoute pas comme un échantillon indépendant.

## Exécution

Python 3.12, numpy 2.3.5 et pandas 2.2.3, déjà présents dans l'environnement.
Le module utilise le chargeur vérifié et le moteur bid/ask d'origine conservés
dans le dépôt. Il n'utilise pas les signaux H4/M30 ni leurs indicateurs.

```sh
cd /workspace/back-test
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m simple_forex.runner \
  --cache data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl \
  --output reports/simple_london_next_run
```

Le dossier de sortie doit être nouveau. Chaque run gèle les sources et le
protocole avant calcul, conserve les événements M5/refus et les trades, et
exporte les enveloppes M1 de liquidation. Ces enveloppes comprennent des frais
de sortie hypothétiques ; elles ne certifient pas l'equity contractuelle FTMO.

Une minute manquante dans le range empêche sa construction. Une M5 de recherche
incomplète annule les nouveaux signaux de la séance. Une entrée ou une position
non résolue arrête le portefeuille continu et laisse son total à null.

Le protocole fixe une seule version ; aucune grille de réglages n'a été optimisée.
La suite utile est de qualifier les données manquantes et d'étudier un historique
encore inutilisé avant de modifier une règle. Aucun accès courtier, ordre réel
ou achat de challenge n'est implémenté ou activé.
