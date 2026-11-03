Le fichier `triangle.csv` contient un triangle de sinistres cumulés (années 1981 à 1990).

Réalise un bootstrap du modèle de Poisson sur-dispersé (résidus de Pearson ajustés par les degrés de liberté, 10 000 simulations, erreur de processus incluse) pour obtenir la distribution de la provision totale.

Donne la moyenne de la provision totale simulée, son erreur de prédiction (écart-type) et son quantile à 95 %.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"provision_moyenne": 0, "erreur_prediction": 0, "quantile_95": 0}
```
