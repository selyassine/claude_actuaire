Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2011 à 2020, 10 périodes de développement).

Applique la méthode Chain Ladder standard (facteurs moyens pondérés par les volumes sur toutes les années, sans queue) et donne la provision totale.

Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés suivantes (nombres sans séparateur de milliers ; `null` pour une valeur que tu ne peux pas calculer avec les données fournies, `true` ou `false` pour une question oui / non) :

```resultats
{"provision_totale": 0}
```
