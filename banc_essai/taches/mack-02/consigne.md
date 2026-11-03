Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 1 à 10).

Calcule par le modèle de Mack l'erreur de prédiction de la provision Chain Ladder, avec l'extrapolation habituelle de Mack pour le dernier paramètre de variance. Exprime les erreurs en pourcentage de la provision correspondante (en décimal : 0,25 pour 25 %).

Donne l'erreur relative totale, l'erreur relative de l'année d'origine 10 et le paramètre de variance sigma² de la première période de développement (1 à 2).

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"erreur_relative_totale": 0, "erreur_relative_origine_10": 0, "sigma2_1_2": 0}
```
