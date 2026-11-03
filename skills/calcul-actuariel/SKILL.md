---
name: calcul-actuariel
description: Moteur de calcul actuariel testé sur des résultats publiés. À utiliser pour tout chiffre actuariel (provisions, IBNR, triangles, Chain Ladder, Mack, bootstrap, Bornhuetter-Ferguson, tables de mortalité, annuités, provisions vie, GPD, crédibilité, SCR) au lieu de calculer de tête. Use for any actuarial calculation (reserving, life contingencies, EVT, credibility, SCR).
---

# Calcul actuariel

Ce skill contient des scripts Python testés contre des valeurs publiées. Ils remplacent le calcul « de tête », qui produit des chiffres plausibles mais faux.

## Règles

1. **Aucun chiffre actuariel sans script.** Pour toute valeur calculée (facteur, ultime, provision, erreur de prédiction, quantile, prime, SCR), lance la commande correspondante. Ne recalcule pas toi-même ce que le script sait faire, même pour vérifier.
2. **Cite la sortie et ses hypothèses.** Dans ta réponse, reprends les chiffres tels que le script les rend, les options retenues et les hypothèses listées dans le JSON (`hypotheses`). Mentionne tout `avertissement`.
3. **Signale ce qui ne vient pas du moteur.** Si une méthode demandée n'existe pas encore dans le moteur, dis-le clairement, puis calcule en Python explicite et marque ces chiffres « non validés par le moteur ».
4. **Les choix de jugement restent visibles.** Exclusions de facteurs, facteur de queue, ratio a priori, seuil GPD : passe-les en option et explique pourquoi dans la réponse.

## Utilisation

Les scripts sont dans le dossier `scripts/` à côté de ce fichier. Remplace `<skill>` par le dossier de ce skill.

```bash
python <skill>/scripts/cli.py --help                 # liste des commandes
python <skill>/scripts/cli.py <commande> --help      # options d'une commande
python <skill>/scripts/cli.py environnement          # vérifie l'installation
python <skill>/scripts/cli.py triangle --entree triangle.csv --format texte
python <skill>/scripts/cli.py chain-ladder --entree payes.csv --type cumule --periode 5 --queue 1.01
python <skill>/scripts/cli.py bf --entree declares.csv --primes primes.csv --ratio 0.65
python <skill>/scripts/cli.py cape-cod --entree declares.csv --primes primes.csv
```

Sortie par défaut : JSON avec `methode`, `moteur`, `entrees` (fichier + empreinte SHA-256), `options`, `hypotheses`, `resultats`, `avertissements`.

## Formats d'entrée

- **Triangle** : CSV (séparateur `,` `;` ou tabulation, détecté) ou Excel. Première colonne = année d'origine, en-têtes = périodes de développement, cellules futures vides. Avec `;` comme séparateur, la virgule décimale est acceptée. Précise toujours `--type cumule` ou `--type incremental` quand tu le sais : la détection automatique n'est qu'un indice.
- **Primes** (BF, Cape Cod) : colonnes `Origine`, `Prime`, et pour BF `Ratio` ou `Ultime_a_priori` (ou l'option `--ratio`).

Si les données de l'utilisateur sont dans un autre format, convertis-les d'abord dans ce format en fichier, puis appelle le script.

## Commandes disponibles

| Commande | Rôle | Statut |
| --- | --- | --- |
| `environnement` | Vérifie Python, numpy, scipy, pandas | disponible |
| `triangle` | Lit et contrôle un triangle, dernière diagonale | disponible |
| `chain-ladder` | Facteurs, CDF, ultimes, provisions | testé : Friedland (2010) ch. 7, Mack (1993) |
| `bf` | Bornhuetter-Ferguson | testé : Friedland (2010) ch. 9 |
| `cape-cod` | Cape Cod (ratio estimé sur toutes les années) | testé : Friedland (2010) ch. 10 |

Options de développement communes (`chain-ladder`, `bf`, `cape-cod`) :

- `--moyenne ponderee|simple` (défaut pondérée), `--periode N` (N dernières années calendaires), `--queue F`.
- `--exclure '2003@12-24'` pour retirer un facteur individuel, `--facteurs-imposes '12-24=1.70'` pour un choix de jugement. Les noms de facteurs reprennent les en-têtes du triangle.
- `--arrondi 3` reproduit la convention des exhibits de Friedland (facteurs et CDF arrondis à 3 décimales). Sans cette option, le calcul est en pleine précision.

Chaque choix de jugement apparaît dans `hypotheses` : explique-le à l'utilisateur.

Les méthodes suivantes arrivent par phases : Mack, bootstrap ODP, survie et provisions vie, GPD, crédibilité, agrégation SCR. Le fichier `references/methodes.md` indique pour chacune la publication qui la valide.
