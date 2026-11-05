Le fichier `triangle.csv` contient un triangle de sinistres cumulés (années d'origine 2006 à 2022, 17 périodes de développement).

Ajuste un modèle de Poisson sur-dispersé (GLM log, effets origine et développement) aux montants incrémentaux, avec un paramètre de dispersion estimé par la statistique du khi-deux de Pearson divisée par les degrés de liberté.

Calcule l'erreur de prédiction analytique de la provision.

Donne le paramètre de dispersion, la provision totale, l'erreur de prédiction totale et celle de l'année 2022.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"dispersion": 0, "provision_totale": 0, "erreur_prediction_totale": 0, "erreur_prediction_2022": 0}
```
