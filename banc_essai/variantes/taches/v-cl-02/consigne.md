Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2014 à 2020, 7 périodes de développement).

Applique Chain Ladder avec des facteurs moyens pondérés par les volumes sur les 3 dernières années calendaires (les 3 derniers facteurs individuels de chaque colonne), en pleine précision, sans queue.

Donne la provision totale, le facteur cumulé (CDF) de l'âge 1 jusqu'à l'ultime et le facteur de la période 1 à 2.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"provision_totale": 0, "cdf_1": 0, "facteur_1_2": 0}
```
