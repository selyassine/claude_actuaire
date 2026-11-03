Le fichier `experience.csv` donne, pour 5 États et 12 trimestres, le coût moyen des sinistres (colonne `Ratio`) et le nombre de sinistres (colonne `Poids`). Ignore la colonne `Cohorte`.

Applique le modèle de crédibilité de Bühlmann-Straub avec les estimateurs sans biais usuels des paramètres de structure.

Donne la prime collective, la variance entre États et la variance intra-État.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"prime_collective": 0, "variance_entre": 0, "variance_intra": 0}
```
