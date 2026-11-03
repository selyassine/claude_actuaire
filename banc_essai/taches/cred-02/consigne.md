Le fichier `experience.csv` donne, pour 5 États et 12 trimestres, le coût moyen des sinistres (colonne `Ratio`) et le nombre de sinistres (colonne `Poids`). Les États sont regroupés en deux cohortes (colonne `Cohorte` : A pour les États 1 et 3, B pour les États 2, 4 et 5).

Applique le modèle de crédibilité hiérarchique à deux niveaux (Jewell), avec les pseudo-estimateurs itératifs des variances (type Bichsel-Straub).

Donne la prime collective, la prime de crédibilité de la cohorte A, celle de la cohorte B et celle de l'État 4.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"prime_collective": 0, "prime_cohorte_A": 0, "prime_cohorte_B": 0, "prime_etat_4": 0}
```
