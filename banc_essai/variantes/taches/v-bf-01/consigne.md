Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2013 à 2022, 10 périodes de développement). Le fichier `primes.csv` donne par année d'origine la prime acquise et une charge ultime a priori (colonne `Ultime_a_priori`).

Applique la méthode Bornhuetter-Ferguson avec ces ultimes a priori. Cadence : facteurs Chain Ladder moyens pondérés sur toutes les années, en pleine précision, sans queue.

Donne la charge ultime totale, l'IBNR total et l'ultime de l'année 2022.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"ultime_total": 0, "ibnr_total": 0, "ultime_2022": 0}
```
