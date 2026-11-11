# Données à récupérer : STRATEGIE_TENDANCE_FX_OR_V01

À produire par ChatGPT ou Codex, **sans backtest et sans aucune statistique de rendement** (ni par heure, ni par jour, ni par instrument).

## 1. Prix M1 bid ET ask, du 2020-01-01 au 2026-10-16

Instrument : **XAUUSD (or)**, disponible chez FTMO. Le projet se limite à EURUSD et à l'or, sur décision de Léo du 11/11/2026. EURUSD est déjà disponible.

Exigences :
- même format que `datasets/strategie_l3_v01_histdata` : un CSV par mois et par instrument, manifeste SHA256, liste des minutes manquantes ;
- **conversion horaire** : les fichiers HistData sont en heure de l'Est fixe (UTC-5), mais **décalés d'une heure pendant l'heure d'été européenne**. L'heure UTC vraie se calcule ainsi : étiquette + 5 h, moins 1 h si ce moment tombe dans l'heure d'été d'Europe/Berlin. C'est vérifié sur EUR/USD 2020 contre Dukascopy, avec un écart de 0,0 pip ;
- **contrôle obligatoire** : comparer l'or à quelques jours Dukascopy, téléchargés lentement, en hiver, en été et pendant les 3 semaines de mars et la semaine d'octobre-novembre où les heures d'été européenne et américaine diffèrent.

## 2. Fiche technique FTMO de XAUUSD et d'EURUSD

À relever sur ftmo.com/en/symbols : taille du contrat, valeur du point, commission, swap acheteur et vendeur, levier, horaires de cotation. Indiquer la date de lecture.

## 3. Interdits

Ne calculer aucun rendement, aucune performance, aucun indicateur de stratégie. Le gel de la fiche n'a de valeur que si personne n'a regardé les résultats avant l'exécution unique.
