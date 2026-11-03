Le fichier `sinistres_declares.csv` contient un triangle de sinistres déclarés cumulés (automobile, années d'accident 1998 à 2007, âges de développement de 12 à 120 mois).

Estime les charges ultimes par Chain Ladder avec les conventions suivantes : facteurs de développement égaux à la moyenne pondérée par les volumes sur les 3 dernières années calendaires disponibles, facteurs et facteurs cumulés (CDF) arrondis à 3 décimales, pas de facteur de queue (CDF de 1,000 à 120 mois).

Donne la charge ultime totale, l'IBNR total (ultime moins déclaré) et le CDF à 12 mois.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres, sans séparateur de milliers) :

```resultats
{"ultime_total": 0, "ibnr_total": 0, "cdf_12": 0}
```
