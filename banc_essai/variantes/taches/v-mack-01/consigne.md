Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2012 à 2022, 11 périodes de développement).

Calcule la provision Chain Ladder et son erreur de prédiction (racine de l'erreur quadratique moyenne de prédiction) selon le modèle de Mack, avec l'extrapolation habituelle de Mack pour le dernier paramètre de variance. Donne la provision totale, l'erreur de prédiction totale et celle de l'année 2022.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"provision_totale": 0, "erreur_prediction_totale": 0, "erreur_prediction_2022": 0}
```
