Le fichier `triangle.csv` contient un triangle de sinistres cumulés (années 1981 à 1990).

Ajuste un modèle de Poisson sur-dispersé (GLM log, effets origine et développement) aux montants incrémentaux, avec un paramètre de dispersion estimé par la déviance divisée par les degrés de liberté. Calcule l'erreur de prédiction analytique de la provision.

Donne le paramètre de dispersion, l'erreur de prédiction totale et celle de l'année 1990.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"dispersion": 0, "erreur_prediction_totale": 0, "erreur_prediction_1990": 0}
```
