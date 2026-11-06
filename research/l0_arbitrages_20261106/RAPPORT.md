# Lot L0 : arbitrages écrits avant toute nouvelle recherche de signal

> Rédigé le 6 novembre 2026 par Claude, à partir des réponses de Léo. Ce lot ne contient que des documents : aucun code, aucun ordre, aucune connexion à un courtier. Rien ici n'est un conseil financier personnalisé.

## Point de départ

Le lot MISSING_MINUTE_V01 s'est terminé le 4 novembre 2026 par un **ARRÊT pour V03 et pour V04** (branche `research/missing-minute-v01`). Sur avril à décembre 2021, dans le scénario S_CONT avec coûts renforcés :

- V03 perd 8 165,45 €, soit −0,31 R par trade sur 210 trades ;
- V04 perd 7 614,92 €, soit −0,29 R par trade sur 213 trades.

Claude a revérifié ce résultat à partir des CSV : 181 empreintes sont conformes, et les nets sont identiques sur les 12 trajectoires. Aucune stratégie du dépôt n'a donc d'avantage prouvé.

## Décisions prises par Léo le 6 novembre 2026

| Sujet | Décision | Conséquence |
| --- | --- | --- |
| Objectif | **La preuve d'abord** | Le plan suit les lots L0 à L6, en démo seulement. Aucun bot n'est présenté comme validé avant un test prospectif réussi. L'achat d'un challenge reste une décision séparée, hors de ce plan. L'objectif « moins d'un mois » de `OBJECTIF_ET_BLOCAGES.md` n'est plus un critère de recherche. |
| Autorité | **Léo seul**, par un GO écrit pour chaque lot | Tout document de gouvernance qui dit autre chose doit être corrigé. La signature exigée au gel (L4) est celle de Léo. |
| Produit | **2-Step 100 000** en référence ; **1-Step 100 000 accepté** comme repli | L'évaluateur FTMO construit en L2 doit couvrir les deux produits. |
| Devise du compte | **USD** | Sur EUR/USD, le gain ou la perte est en USD : l'ajustement de 0,7 % (art. 5.3.4 des conditions) ne s'applique pas. Le capital de référence devient 100 000 USD. |
| Risque de référence | **125 USD par trade** (0,125 %), **plus d'entrée au-delà de 500 USD de perte dans la journée** | Le test de preuve se mesure en R. La taille réelle ne sera fixée qu'après le test prospectif. Le témoin historique V03 garde ses montants en euros pour rester reproductible. |

## Profil de compte

Le nouveau profil est [`ACCOUNT_PROFILE_DRAFT_02.json`](../ftmo_readiness/ACCOUNT_PROFILE_DRAFT_02.json).

- Il reprend les règles officielles FTMO lues le 4 novembre 2026, et les conditions générales du 1er novembre 2026.
- Il n'a aucun champ vide : ce qu'aucune source ne fixe est marqué `INCONNU`, avec la question FTMO ou le relevé L1 qui le comblera.
- `ACCOUNT_PROFILE_TO_COMPLETE.json` n'est pas modifié sur place. Il reste comme trace de la version 01 (compte en EUR, échéance de 30 jours).

## Questions écrites envoyées à FTMO par Léo

Ces questions conditionnent les lots suivants. Les réponses seront archivées telles quelles, avec leur date.

1. Enregistrer les prix EUR/USD par programme, sans passer d'ordre, est-il compatible avec l'article 9.4 ? Une réponse négative déclenche l'arrêt écrit ci-dessous.
2. Le paquet Python MetaTrader5, un EA MQL5 de garde et l'Open API de cTrader sont-ils autorisés ?
3. Les lectures seules comptent-elles dans les 2 000 requêtes serveur par jour ?
4. En Challenge et en Verification, peut-on ouvrir une position avant une annonce majeure ? La FAQ et la page des pratiques interdites se contredisent.
5. Comment l'équité est-elle mesurée pour les limites : fréquence, prix bid ou ask, cas de l'égalité exacte ?
6. La commission EUR/USD sur MT5 est-elle bien de 5 USD par lot aller-retour ?
7. L'ajustement de 0,7 % est-il bien absent sur un compte en USD ?
8. Un code écrit avec l'aide d'assistants IA, sans IA qui décide en temps réel, est-il conforme à la clause sur l'intelligence artificielle ?
9. Un EA peut-il tourner sur l'essai gratuit, avec les mêmes prix et les mêmes coûts que le Challenge ?

## Ce qui reste à faire dans L0

- Archiver les réponses de FTMO.
- Remplir les champs `INCONNU` du profil avec ces réponses.
- Compléter le registre rétrospectif des essais. Il est tenu hors dépôt, car il résume des documents privés du projet.

Seuils retenus pour la suite :

- au moins 1 639 essais documentés, et une borne haute déclarative de plus de 11 500 ;
- un candidat en L3 devra atteindre t ≥ 4,01 (correction de Bonferroni à 5 % pour 1 639 essais) et publier son nombre d'essais de rupture ;
- en dessous de t = 4,45 (11 500 essais), il portera la mention « fragile ».

## Fin de L0 et arrêt écrit d'avance

L0 est terminé quand quatre conditions sont réunies :

- les décisions sont écrites (fait) ;
- le profil n'a aucun champ vide (fait) ;
- les réponses de FTMO sont archivées (en attente) ;
- le registre donne un nombre documenté d'essais et une borne haute (fait, hors dépôt).

**Arrêt :** si FTMO refuse tout enregistrement des prix par programme et qu'aucune mesure manuelle ne suffit, le projet est revu avant L1.

L1 mesure les coûts réels sur un compte de démo, pendant au moins quatre semaines. Il ne démarre que sur un GO écrit de Léo.
