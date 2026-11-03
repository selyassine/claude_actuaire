Le fichier `sinistres_declares.csv` contient un triangle de sinistres déclarés cumulés (automobile, 1998 à 2007, âges 12 à 120 mois). Le fichier `primes.csv` donne la prime acquise par année d'accident (n'utilise pas la colonne `Ultime_a_priori`).

Applique la méthode Cape Cod (Stanard-Bühlmann) sans tendance ni ajustement de primes : ratio de sinistralité attendu estimé sur toutes les années. Cadence : facteurs Chain Ladder moyens pondérés sur les 3 dernières années calendaires, facteurs et CDF arrondis à 3 décimales, sans queue.

Donne le ratio de sinistralité Cape Cod (en décimal, par exemple 0,65), la charge ultime totale et l'IBNR total.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"ratio_cape_cod": 0, "ultime_total": 0, "ibnr_total": 0}
```
