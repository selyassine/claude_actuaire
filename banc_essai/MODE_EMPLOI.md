# Mode d'emploi : lancer le banc d'essai réduit (48 sessions)

Chaque tâche de `banc_essai/taches/<id>/` contient deux éléments :

- `consigne.md`, le texte à coller ;
- le ou les fichiers de données à joindre (aucun pour `vie-*` et `scr-*`).

N'ouvre pas `corrige.yaml` dans la conversation.

## Les trois conditions (sur claude.ai, même modèle partout, à noter)

| Condition | Réglages |
| --- | --- |
| A | Skill `calcul-actuariel` **désactivé**, exécution de code / analyse **désactivée** |
| B | Skill **désactivé**, exécution de code **activée** |
| C | Skill **activé** (zip `calcul-actuariel.zip`), exécution de code **activée** |

## Pour chaque session

1. Ouvre une **nouvelle conversation** : une conversation par tâche et par condition, sans projet ni mémoire contenant des résultats.
2. Joins les fichiers de données de la tâche, puis colle le contenu de `consigne.md`.
3. Ne réponds pas aux questions de Claude et ne corrige rien. Si Claude pose une question au lieu de répondre, note « question » et passe à la suite.
4. Copie la **réponse complète** de Claude dans `banc_essai/reponses_a_remplir.md`, sous le titre `## <condition> <tâche>` correspondant (par exemple `## C gpd-01`).

Ensuite, envoie-moi le fichier rempli. Je lance :

```bash
python banc_essai/importer.py banc_essai/reponses_a_remplir.md
python banc_essai/noter.py
```

`importer.py` découpe le fichier en `banc_essai/reponses/<condition>/<tâche>/1.md`. `noter.py` donne le taux de bonnes valeurs par condition et par famille.

## Ordre conseillé

Fais toutes les tâches en A, puis en B, puis en C, pour ne pas mélanger les réglages. Compte environ 2 à 5 minutes par session.
