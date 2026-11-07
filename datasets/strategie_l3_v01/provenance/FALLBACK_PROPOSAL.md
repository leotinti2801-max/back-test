# Alternative proposée — en attente d'accord de Léo

Aucun fichier de cotations HistData ou TrueFX n'a été téléchargé. Seules les pages de documentation publiques ont été consultées le 7 novembre 2026.

## Option proposée : HistData, Generic ASCII en ticks

Source officielle : https://www.histdata.com/f-a-q/data-files-detailed-specification/
FAQ officielle : https://www.histdata.com/f-a-q/

Ce format contient horodatage à la milliseconde, bid, ask et volume. Les fichiers M1 HistData sont basés sur le bid seul : ils ne remplacent pas les ticks bid/ask demandés.
Le fournisseur indique EST fixe, sans heure d'été : UTC = horodatage HistData + 5 heures toute l'année. Ne pas utiliser une zone New York avec changement saisonnier.
La présence effective de chaque mois jusqu'à octobre 2026 reste à vérifier après accord ; aucune couverture intégrale n'est présumée.

## Conversion proposée après accord uniquement

1. Conserver chaque archive originale et son SHA256, son URL, sa date d'acquisition et le rapport de qualité éventuellement fourni.
2. Lire les lignes en flux, schéma d'entrée `YYYYMMDD HHMMSSNNN,bid,ask,volume`. Convertir EST fixe UTC−05:00 vers UTC. Charger les mois locaux adjacents nécessaires aux bornes UTC, notamment décembre 2019 pour le début janvier 2020.
3. Ne conserver que les ticks du 2020-01-01 00:00:00 UTC au 2026-10-17 00:00:00 UTC exclus. Conserver l'ordre source des ticks de même horodatage. Signaler les anomalies de format ou d'ordre ; ne pas supprimer silencieusement des lignes.
4. Grouper par minute UTC, intervalle [minute, minute+60 secondes[. Calculer séparément les quatre OHLC du bid et de l'ask. `n_ticks` = nombre d'enregistrements source de la minute, pas la colonne volume.
5. Exporter un CSV par mois UTC, même schéma : `utc_minute,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close,n_ticks`.
6. Produire le même type de manifeste SHA256 et la liste des minutes sans ticks. Distinguer absence de cotations reçues et archives non acquises. Aucune interpolation et aucun prix ask reconstruit à partir d'un spread supposé.
7. Conserver HistData dans un jeu séparé identifié par son fournisseur ; ne pas substituer silencieusement ses ticks à des trous Dukascopy. Vérifier les conditions de redistribution avant un dépôt public. Choisir le périmètre final avec Léo.

La conversion ne calcule ni rendement, ni spread, ni statistique horaire ou liée aux fenêtres de stratégie. Aucun backtest et aucune modification de la fiche gelée.

## Autre possibilité : TrueFX

Source officielle : https://www.truefx.com/truefx-historical-downloads-2/
TrueFX annonce des cotations historiques top-of-book à la milliseconde. L'accès aux fichiers nécessite un compte. Le schéma et le fuseau des archives accessibles devront être confirmés dans la documentation accompagnant les données avant conversion. Les conditions de redistribution devront aussi être vérifiées avant un dépôt public.
La méthode d'agrégation M1 et le schéma de sortie resteraient identiques une fois les horodatages correctement normalisés en UTC.
