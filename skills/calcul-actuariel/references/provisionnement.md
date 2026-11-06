# Provisionnement non-vie

Fichier de référence du skill `calcul-actuariel` pour les commandes `controler`, `triangle`, `chain-ladder`, `bf`, `cape-cod`, `mack`, `odp` et `bootstrap`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

## Formats d'entrée

- **Triangle** : CSV (séparateur `,` `;` ou tabulation, détecté) ou Excel. Première colonne = année d'origine, en-têtes = périodes de développement, cellules futures vides. Avec `;` comme séparateur, la virgule décimale est acceptée. Précise toujours `--type cumule` ou `--type incremental` quand tu le sais : la détection automatique n'est qu'un indice.
- **Primes** (BF, Cape Cod) : colonnes `Origine`, `Prime`, et pour BF `Ratio` ou `Ultime_a_priori` (ou l'option `--ratio`). Une origine par ligne, les mêmes libellés que le triangle, la même unité monétaire (le moteur alerte si le ratio ultime / prime semble indiquer une unité différente).

Si les données de l'utilisateur sont dans un autre format, convertis-les d'abord dans ce format en fichier, puis appelle le script.

Sur un nouveau fichier, lance d'abord `controler`. Présente les anomalies bloquantes et les alertes à l'utilisateur et demande-lui comment les traiter : ne corrige rien toi-même (ne complète pas un trou, ne retire pas un doublon, n'exclus pas un facteur atypique) sans son accord, puis passe sa décision en option explicite de la méthode.

## Méthodes déterministes

| Commande | Rôle | Statut |
| --- | --- | --- |
| `controler` | Audit de qualité d'un triangle, d'un fichier de sinistres ou de primes, sans calcul : anomalies bloquantes, alertes, informations | disponible |
| `triangle` | Lit et contrôle un triangle, dernière diagonale | disponible |
| `chain-ladder` | Facteurs, CDF, ultimes, provisions | testé : Friedland (2010) ch. 7, Mack (1993) |
| `bf` | Bornhuetter-Ferguson | testé : Friedland (2010) ch. 9 |
| `cape-cod` | Cape Cod (ratio estimé sur toutes les années) | testé : Friedland (2010) ch. 10 |

Options de développement communes (`chain-ladder`, `bf`, `cape-cod`) :

- `--moyenne ponderee|simple` (défaut pondérée), `--periode N` (N dernières années calendaires), `--queue F`.
- `--exclure '2003@12-24'` pour retirer un facteur individuel, `--facteurs-imposes '12-24=1.70'` pour un choix de jugement. Les noms de facteurs reprennent les en-têtes du triangle.
- `--arrondi 3` reproduit la convention des exhibits de Friedland (facteurs et CDF arrondis à 3 décimales). Sans cette option, le calcul est en pleine précision.

Chaque choix de jugement apparaît dans `hypotheses` : explique-le à l'utilisateur.

## Méthodes stochastiques

| Commande | Rôle | Statut |
| --- | --- | --- |
| `mack` | Erreur de prédiction de Chain Ladder (Mack 1993), par année et totale | testé : Mack (1993) tableau 3, England et Verrall (2002) tableaux 13-14 |
| `odp` | Poisson sur-dispersé, erreur de prédiction analytique | testé : England et Verrall (2002) tableau 3 |
| `bootstrap` | Bootstrap ODP : moyenne, erreur de prédiction, quantiles (dont 99,5 %) | testé : England et Verrall (2002) tableaux 33-34, à 5 % près |

Ces trois commandes exigent un triangle carré complet et utilisent les facteurs Chain Ladder standards (sans queue ni exclusion). Options : `mack --sigma-dernier mack|precedent`, `odp --dispersion pearson|deviance`, `bootstrap --simulations N --graine G`. Donne toujours la graine utilisée : elle rend le résultat reproductible.
