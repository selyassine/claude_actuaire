Le fichier `experience.csv` donne, pour 6 portefeuilles et 10 années, le coût moyen des sinistres (colonne `Ratio`) et le nombre de sinistres (colonne `Poids`). Les portefeuilles sont regroupés en deux cohortes (colonne `Cohorte` : A pour les portefeuilles 1 à 3, B pour 4 à 6).

Applique le modèle de crédibilité hiérarchique à deux niveaux (Jewell), avec les pseudo-estimateurs itératifs des variances (type Bichsel-Straub).

Donne la prime collective, la prime de crédibilité de la cohorte A, celle de la cohorte B et celle du portefeuille 5.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"prime_collective": 0, "prime_cohorte_A": 0, "prime_cohorte_B": 0, "prime_portefeuille_5": 0}
```
