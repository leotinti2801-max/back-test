# FTMO 2-Step 100 000 EUR — vérification du 4 novembre 2026

**Les conditions actuelles ne sont pas vérifiées.** Aucun profil confirmé n'a été modifié et aucun nouveau backtest n'a été lancé.

## Accès réellement testé

Une seule requête a été effectuée vers la page officielle :

https://ftmo.com/en/trading-objectives/

Heure UTC de la tentative : 2026-11-04T10:12:10.776116+00:00

Résultat : `URLError: Tunnel connection failed: 403 Forbidden`. Le refus est observé lors de l'ouverture du tunnel par la route proxy héritée ; aucune page officielle FTMO n'a été reçue. Ce constat ne doit pas être présenté comme un code HTTP renvoyé par le site FTMO lui-même. La vérification TLS a été conservée et aucun accès direct, proxy alternatif ou miroir n'a été essayé.

Le statut runtime consulté signalait un réseau restreint, `state=unknown`, `observations_current=true` et aucune liste de domaines personnalisés autorisés. Le snapshot local ne contenait ni `ftmo.com` ni `www.ftmo.com`. Une configuration déclarée ou un état inconnu ne prouve pas que la politique est effectivement appliquée ; le résultat de la requête est l'observation de connectivité retenue.

Aucune nouvelle tentative inchangée n'est utile tant qu'un état d'accès pertinent n'a pas changé. Le parent conserve la gestion du brouillon réseau ; aucun domaine n'a été ajouté par cet agent.

## Profil incomplet, explicitement conditionné

Le produit demandé est FTMO **2-Step**, compte simulé de **100 000 EUR**. Ce périmètre vient de la tâche du parent, pas d'un document récupéré. Les objectifs par phase, la perte journalière, la perte totale, la méthode de référence balance/equity, le fuseau de reset, les jours minimaux et leur définition, les règles d'annonces/week-end, et les délais de passage de phase restent à confirmer.

Les repères historiques 10 % / 5 % d'objectifs, 5 % de perte journalière, 10 % de perte maximale, quatre jours et reset CE(S)T restent uniquement une **hypothèse de travail non confirmée au 4 novembre 2026**. Ils ne sont pas inscrits comme règles actuelles et ne peuvent autoriser un verdict « FTMO PASS ». Les règles 1-Step, notamment toute référence à un seuil mobile ou à une règle de concentration des gains, ne sont pas transférées au 2-Step.

Il faut aussi séparer les deux phases d'évaluation du compte FTMO ultérieur et distinguer les types Standard/Swing pour les annonces et la détention. Un solde positif ne prouve pas le respect d'une limite fondée sur l'equity intraposition.

## Pièces

- `FETCH_RESULT.json` : date, URL, route, erreur exacte et absence de document officiel.
- `PROFILE_VERIFICATION_STATUS.json` : champs actuels non confirmés laissés à `null`, hypothèses séparées, statut réseau et périmètre.
- `MANIFEST_SHA256.json` : empreintes des pièces.

La seule conclusion nouvelle de ce cycle est une preuve datée d'accès encore indisponible. Aucune condition FTMO contemporaine n'est inventée ou certifiée.
