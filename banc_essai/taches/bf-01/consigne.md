Le fichier `sinistres_declares.csv` contient un triangle de sinistres déclarés cumulés (automobile, 1998 à 2007, âges 12 à 120 mois). Le fichier `primes.csv` donne par année d'accident la prime acquise et une charge ultime a priori (colonne `Ultime_a_priori`).

Applique la méthode Bornhuetter-Ferguson avec ces ultimes a priori. Pour la cadence, utilise des facteurs Chain Ladder moyens pondérés sur les 3 dernières années calendaires, facteurs et CDF arrondis à 3 décimales, sans queue.

Donne la charge ultime totale, l'IBNR total et l'ultime de l'année 2007.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"ultime_total": 0, "ibnr_total": 0, "ultime_2007": 0}
```
