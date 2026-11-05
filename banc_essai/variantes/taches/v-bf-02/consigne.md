Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2013 à 2022, 10 périodes de développement). Le fichier `primes.csv` donne la prime acquise par année d'origine (n'utilise pas la colonne `Ultime_a_priori`).

Applique la méthode Cape Cod (Stanard-Bühlmann) sans tendance ni ajustement de primes : ratio de sinistralité attendu estimé sur toutes les années. Cadence : facteurs Chain Ladder moyens pondérés sur toutes les années, en pleine précision, sans queue.

Donne le ratio Cape Cod (en décimal, par exemple 0,65), la charge ultime totale et l'IBNR total.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"ratio_cape_cod": 0, "ultime_total": 0, "ibnr_total": 0}
```
