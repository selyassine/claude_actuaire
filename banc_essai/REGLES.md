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
