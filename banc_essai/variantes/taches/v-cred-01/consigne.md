Le fichier `experience.csv` donne, pour 6 portefeuilles et 10 années, le coût moyen des sinistres (colonne `Ratio`) et le nombre de sinistres (colonne `Poids`). Ignore la colonne `Cohorte`.

Applique le modèle de crédibilité de Bühlmann-Straub avec les estimateurs sans biais usuels des paramètres de structure.

Donne la prime collective, la variance entre portefeuilles, la variance intra-portefeuille, le facteur de crédibilité du portefeuille 3 et sa prime de crédibilité.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"prime_collective": 0, "variance_entre": 0, "variance_intra": 0, "credibilite_3": 0, "prime_portefeuille_3": 0}
```
