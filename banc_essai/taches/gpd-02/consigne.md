Le fichier `sinistres_incendie.csv` contient 2 167 sinistres incendie de plus d'un million (en millions), une ligne par sinistre.

Ajuste par maximum de vraisemblance une loi de Pareto généralisée aux excès au-delà du seuil de 4. Avec l'estimateur de queue 1 − F(x) = (N_u / n)(1 + ξ (x − u) / σ)^(−1/ξ), calcule les quantiles à 99,5 % et 99,99 % de la distribution des sinistres.

Donne le nombre de dépassements, ξ, son erreur type asymptotique et les deux quantiles.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"n_depassements": 0, "xi": 0, "erreur_type_xi": 0, "quantile_995": 0, "quantile_9999": 0}
```
