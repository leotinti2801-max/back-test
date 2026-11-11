# Contrôle des prix et de l'heure : bloqué

**Aucune comparaison de prix HistData–Dukascopy sur XAUUSD n'a été réalisée.**
La correction demandée (+5 heures, puis −1 heure en été européen) est appliquée,
mais son exactitude sur l'or reste à vérifier. Un contrôle effectué auparavant
sur EURUSD ne constitue pas cette vérification.

## Accès constaté le 11 novembre 2026

Deux demandes espacées de plusieurs minutes au flux historique officiel ont renvoyé
HTTP **429**, avec un renvoi vers la documentation d'export Dukascopy. Celle-ci
décrit une archive AWS S3 en *Requester Pays*, qui exige des identifiants AWS.
Aucun identifiant AWS n'était disponible et aucun téléchargement payant n'a été lancé.

L'interface publique officielle [Historical Data Export](https://www.dukascopy.com/swiss/english/marketwatch/historical/)
a également été inspectée. Son API, découverte dans la configuration et le code
public du widget, a renvoyé une réponse vide avec HTTP **202** et l'en-tête
`x-amzn-waf-action: challenge`. Les tentatives sur Dukascopy ont alors été arrêtées.
Les détails sont conservés dans `provenance/CONTROLE_DUKASCOPY.json`.

## Échantillon prévu pour le contrôle restant

| Journée UTC | Situation à contrôler |
| --- | --- |
| 2020-01-07 | hiver |
| 2020-07-14 | été |
| 2020-03-10 | décalage US/Europe, première semaine de mars concernée |
| 2020-03-17 | décalage US/Europe, deuxième semaine |
| 2020-03-24 | décalage US/Europe, troisième semaine |
| 2020-10-27 | semaine entre les changements d'heure européen et américain d'automne |

Il faut les cotations **bid et ask**, à la minute, ou les ticks permettant de
les reconstituer, avec leur timezone et leur origine Dukascopy. Le contrôle porte
sur l'identité des minutes et les écarts absolus de cotation en USD/once, sans
rendement et sans recherche d'un décalage qui améliorerait un résultat de stratégie.
Le plan est conservé dans `provenance/PLAN_CONTROLE_DUKASCOPY.json`.

Le statut ne peut passer à « validé » qu'après récupération de ces références
et publication de la comparaison. Le statut actuel est **NON VALIDÉ**.
