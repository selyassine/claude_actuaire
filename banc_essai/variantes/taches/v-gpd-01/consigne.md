Le fichier `sinistres_tempete.csv` contient 1 900 sinistres tempête de plus d'un million (en millions), une ligne par sinistre.

Ajuste par maximum de vraisemblance une loi de Pareto généralisée aux excès au-delà du seuil de 6. Utilise l'estimateur de queue 1 − F(x) = (N_u / n)(1 + ξ (x − u) / σ)^(−1/ξ) pour en déduire le quantile à 99,9 % de la distribution des sinistres et la prime pure d'une tranche de réassurance 75 XS 25 (priorité 25, limite 100), par sinistre.

Donne le nombre de dépassements, le paramètre de forme ξ, le quantile à 99,9 % et la prime pure de la tranche.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"n_depassements": 0, "xi": 0, "quantile_999": 0, "prime_tranche": 0}
```
