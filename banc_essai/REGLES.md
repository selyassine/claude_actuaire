# Règles du banc d'essai (enregistrées avant tout passage)

Ces règles sont fixées le 2026-11-03, avant la construction des méthodes et avant tout passage. Toute modification ultérieure doit être faite par un commit séparé, daté et justifié, et le rapport final doit la mentionner.

## Question posée

Claude calcule-t-il plus juste avec le skill `calcul-actuariel` que sans ?

## Conditions

| Condition | Ce que Claude a |
| --- | --- |
| A | Pas de skill, pas d'exécution de code |
| B | Pas de skill, exécution de code autorisée (il peut écrire son propre Python) |
| C | Le skill installé, exécution de code autorisée |

## Tâches

- Environ 40 tâches, 5 par famille de méthodes : Chain Ladder, BF et Cape Cod, Mack, bootstrap ODP, vie, GPD, crédibilité, SCR.
- Chaque tâche = un fichier de données (CSV ou Excel) + une consigne rédigée comme un praticien la recevrait. La publication d'origine n'est jamais citée.
- La moitié des tâches utilise les données publiées telles quelles ; l'autre moitié des variantes (données décalées, autre taux, autre seuil) pour neutraliser la mémorisation.
- Valeurs attendues : pour les données publiées, la publication ; pour les variantes, un logiciel indépendant reconnu (packages R `ChainLadder`, `actuar`, `lifecontingencies`, `evir`) ou un calcul Excel de l'actuaire. Jamais Claude. Chaque valeur attendue est validée par l'actuaire avant le premier passage.
- Les tâches et corrigés sont stockés dans `banc_essai/taches/` ; un corrigé n'est jamais placé dans le dossier du skill.

## Passages

- Chaque tâche est jouée 3 fois par condition, chaque fois dans une session neuve.
- Le même modèle Claude est utilisé pour les trois conditions ; il est noté dans le rapport.
- La consigne demande de terminer la réponse par un bloc :

  ````
  ```resultats
  {"nom_de_la_valeur": 123.45, ...}
  ```
  ````

  Les noms des valeurs sont donnés dans la consigne.

## Notation

- `banc_essai/noter.py` compare chaque valeur à la valeur attendue, avec la tolérance du corrigé (arrondi publié, ou 2 % relatif pour le bootstrap).
- Une valeur absente ou illisible compte comme fausse.
- Score d'une condition = part des valeurs justes, sur l'ensemble et par famille.
- On note aussi, à part, si la réponse cite les hypothèses retenues (oui / non).

## Seuils de réussite

1. Condition C : au moins 95 % de valeurs justes sur l'ensemble, et au moins 90 % pour chaque famille.
2. Écart C − B : au moins 30 points visés sur l'ensemble.
3. Les résultats sont publiés par famille, y compris quand ils sont défavorables. Une famille sans écart est signalée et sa place dans le skill est rediscutée.

## Amendement du 2026-11-03 : banc d'essai réduit (premier passage)

Décidé par Yassine le 2026-11-03, après la construction des méthodes et **avant tout passage**.

Ce qui change par rapport aux règles ci-dessus :

1. **16 tâches au lieu d'environ 40** : 2 par famille de méthodes (8 familles).
2. **Toutes sur données publiées**, sans variantes. Les valeurs attendues sont celles des fiches de référence déjà validées par Yassine (champ `fiche_source` du corrigé). Le risque de mémorisation n'est donc pas neutralisé : il sera discuté dans le rapport.
3. **Un passage par tâche et par condition au lieu de trois**, soit 48 sessions au lieu de 360.
4. **Bootstrap : tolérance de 5 % au lieu de 2 %.** Les valeurs publiées sont elles-mêmes issues d'une simulation. Entre la publication et le moteur (graine 2026, 10 000 simulations), l'écart sur l'erreur de prédiction atteint 2,1 %, ce qui rend 2 % plus strict que le bruit Monte-Carlo.
5. **Les autres tolérances sont celles des fiches** : arrondi publié, 1,5 % sur les quantiles GPD (écart de jeu de données documenté) et 0,1 % sur l'ODP analytique.

Pourquoi : obtenir une première mesure rapide sans nouveau corrigé externe. R n'est pas accessible depuis l'environnement de développement, et les 20 variantes demandaient des corrigés indépendants. Le protocole complet reste l'objectif : le rapport présentera ces résultats comme une **première mesure**, pas comme la validation finale.

Les seuils de réussite (95 % en C, au moins 90 % par famille, écart C − B d'au moins 30 points) restent inchangés.

## Amendement du 2026-11-05 : passage sur les 16 variantes

Décidé par Yassine le 2026-11-05, **avant toute session** de ce passage.

1. **Tâches** : les 16 variantes de `banc_essai/variantes/taches/` (2 par famille), sur données perturbées ou simulées, dont les corrigés ont été validés par Yassine le 2026-11-05. Les réponses ne figurent dans aucune publication.
2. **Un passage par tâche et par condition**, soit 48 sessions, comme au premier passage.
3. **Conditions** identiques au premier passage. A : conversation incognito, skills désactivés, exécution de code désactivée. B : conversation normale, exécution de code active, skills `calcul-actuariel` désactivé. C : conversation normale, seul `calcul-actuariel` activé, en **version 0.2.0** (moteur avec contrôles de l'audit du 2026-11-05). Même modèle et même effort pour les 48 sessions, notés dans le rapport.
4. **Consigne** : le texte de `consigne.md` et les fichiers de données de la tâche, sans aucune autre indication. Aucune intervention pendant la réponse.
5. **Tolérances** : celles des corrigés des variantes (0,05 % relatif sur les montants exacts, au centime en vie, 1,5 % sur les quantiles GPD, 5 % sur le bootstrap).
6. **Notation** : `python banc_essai/noter.py --reponses banc_essai/variantes/reponses --taches banc_essai/variantes/taches --conditions A,B,C`. Un essai manquant compte comme faux.
7. **Rapport séparé** : `banc_essai/variantes/RAPPORT.md`, sans mélanger avec le premier passage.

Les seuils de réussite restent inchangés : 95 % en C, au moins 90 % par famille, écart C − B d'au moins 30 points.

## Amendement du 2026-11-06 : famille « pièges »

Proposé le 2026-11-06 à la suite de l'analyse de Yassine (point 8), **avant toute session** sur ces tâches.

1. **Tâches** : les 9 tâches de `banc_essai/pieges/taches/`, dont 5 tunisiennes. Elles ne seront jouées qu'une fois leurs corrigés validés par Yassine.
2. **Valeurs attendues non numériques** :
   - une valeur `null` signifie que la donnée manque et que la bonne réponse est de ne pas chiffrer. La clé doit être présente et valoir `null`.
   - une valeur booléenne doit être reproduite exactement.
   - une clé absente reste fausse.
3. **Conditions, passages et notation** : identiques à l'amendement du 2026-11-05. Les réponses vont dans `banc_essai/pieges/reponses/`, et le rapport est séparé dans `banc_essai/pieges/RAPPORT.md`. Le skill joué est le dernier publié au moment du passage, et sa version est notée.
4. **Seuil propre à cette famille** : en condition C, au moins 8 tâches sur 9 justes. On mesure aussi, à part, l'écart C − B.
