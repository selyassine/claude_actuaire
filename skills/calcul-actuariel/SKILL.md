---
name: calcul-actuariel
description: Moteur de calcul actuariel testé sur des résultats publiés. À utiliser pour tout chiffre actuariel (provisions, IBNR, triangles, Chain Ladder, Mack, bootstrap, Bornhuetter-Ferguson, tables de mortalité, annuités, provisions vie, GPD, tarification de tranche de réassurance XL, crédibilité, SCR, marge de solvabilité tunisienne, tables TD99/TV99, comparaison avec un modèle externe) au lieu de calculer de tête. Use for any actuarial calculation (reserving, life contingencies, EVT, XL reinsurance layer pricing, credibility, SCR, model validation).
---

# Calcul actuariel

Ce skill contient des scripts Python testés contre des valeurs publiées. Ils remplacent le calcul « de tête », qui produit des chiffres plausibles mais faux.

## Règles

1. **Aucun chiffre actuariel sans script.** Pour toute valeur calculée (facteur, ultime, provision, erreur de prédiction, quantile, prime, SCR), lance la commande correspondante. Ne recalcule pas toi-même ce que le script sait faire, même pour vérifier.
2. **Cite la sortie et ses hypothèses.** Dans ta réponse, reprends les chiffres tels que le script les rend, les options retenues et les hypothèses listées dans le JSON (`hypotheses`). Mentionne tout `avertissement`.
   Le chiffre que tu donnes comme résultat (tableau final, bloc demandé, conclusion) est toujours celui du moteur, même si une autre méthode te semble meilleure. Une estimation différente (par exemple une erreur type GPD tirée de la hessienne observée au lieu de la formule asymptotique du moteur) peut être citée à côté, marquée « autre méthode, non validée par le moteur », jamais à la place.
3. **Signale ce qui ne vient pas du moteur.** Si une méthode demandée n'existe pas encore dans le moteur, dis-le clairement, puis calcule en Python explicite et marque ces chiffres « non validés par le moteur ».
4. **Les choix de jugement restent visibles.** Exclusions de facteurs, facteur de queue, ratio a priori, seuil GPD : passe-les en option et explique pourquoi dans la réponse.
5. **Un refus du moteur n'est pas contourné.** Si la commande sort en erreur (triangle à trou, facteur non estimable, poids négatif, SCR non fini…) ou si `statut` vaut `incomplet`, ne recalcule pas toi-même pour obtenir un chiffre : explique l'erreur et demande à l'utilisateur la donnée ou le choix manquant (par exemple un facteur imposé et sa justification).

## Utilisation

Les scripts sont dans le dossier `scripts/` à côté de ce fichier. Remplace `<skill>` par le dossier de ce skill.

```bash
python <skill>/scripts/cli.py --help                 # liste des commandes
python <skill>/scripts/cli.py <commande> --help      # options d'une commande
python <skill>/scripts/cli.py environnement          # vérifie l'installation
python <skill>/scripts/cli.py controler --entree triangle.csv --nature triangle --type cumule   # qualité des données, sans calcul
python <skill>/scripts/cli.py triangle --entree triangle.csv --format texte
python <skill>/scripts/cli.py chain-ladder --entree payes.csv --type cumule --periode 5 --queue 1.01
python <skill>/scripts/cli.py bf --entree declares.csv --primes primes.csv --ratio 0.65
python <skill>/scripts/cli.py cape-cod --entree declares.csv --primes primes.csv
python <skill>/scripts/cli.py mack --entree payes.csv --type cumule
python <skill>/scripts/cli.py odp --entree payes.csv --type cumule
python <skill>/scripts/cli.py bootstrap --entree payes.csv --type cumule --simulations 10000 --graine 2026
python <skill>/scripts/cli.py gpd --entree sinistres.csv --seuil 10 --quantiles 0.995,0.999 --tranche 50,200 --diagnostic-seuils 3,5,10,20 --test-ajustement 999
python <skill>/scripts/cli.py tranche-xl --entree sinistres.csv --seuil 10 --annees 11 --tranche 50,200 --franchise-annuelle 20 --limite-annuelle 300
python <skill>/scripts/cli.py credibilite --entree experience.csv --modele buhlmann-straub
python <skill>/scripts/cli.py credibilite --entree experience.csv --modele regression --barycentre --periode-future 13
python <skill>/scripts/cli.py scr --entree scr.json
python <skill>/scripts/cli.py marge-solvabilite-tn --entree marge.json          # marge de solvabilité tunisienne (art. 58 bis)
python <skill>/scripts/cli.py provisions-tn --entree provisions.json --cadences cl_auto_materiels.json   # règles de l'arrêté tunisien de 2001
python <skill>/scripts/cli.py survie --modele td99 --taux 0.03 --age 60           # tables tunisiennes TD99 / TV99
python <skill>/scripts/cli.py survie --modele sssm --taux 0.04 --age 50 --n 20
python <skill>/scripts/cli.py tarif-vie --modele sssm --taux 0.04 --type vie-entiere --age 50 --capital 100000 \
    --frais-initiaux-pct 0.5 --frais-initiaux-fixe 250 --frais-renouvellement-pct 0.03 --frais-renouvellement-fixe 25 --durees 0,1,2,10
python <skill>/scripts/cli.py rejouer --sortie calcul.json     # refait un calcul archivé et compare
python <skill>/scripts/cli.py registre --sorties sorties/ --note hypotheses.md            # registre des hypothèses du dossier
python <skill>/scripts/cli.py comparer --resultats calcul.json --lister                  # chemins comparables
python <skill>/scripts/cli.py comparer --resultats calcul.json --externe modele.csv      # rapport d'écarts
```

Sortie par défaut : JSON avec `statut` (`ok`, `avertissements` ou `incomplet`), `methode`, `moteur` (version et versions des bibliothèques), `entrees` (fichier + empreinte SHA-256), `options`, `hypotheses`, `resultats`, `avertissements`, `reproduction` (commande exacte) et `empreinte_resultats`. Une valeur `null` dans les résultats est une valeur non définie (par exemple l'erreur relative d'une provision nulle) : ne la remplace pas par un chiffre. En cas d'erreur, la commande ne rend aucun résultat : un JSON `{"statut": "erreur", "erreur": ...}` sur la sortie d'erreur.

## Commandes et fichiers de référence

Avant la première commande d'une famille dans une conversation, lis son fichier de référence : il donne les formats d'entrée, les options et ce qu'il faut demander à l'utilisateur plutôt que deviner.

| Famille | Commandes | À lire avant |
| --- | --- | --- |
| Provisionnement non-vie | `controler`, `triangle`, `chain-ladder`, `bf`, `cape-cod`, `mack`, `odp`, `bootstrap` | `references/provisionnement.md` |
| Assurance vie | `survie`, `tarif-vie` (dont tables tunisiennes TD99 / TV99) | `references/vie.md` |
| Valeurs extrêmes, réassurance XL | `gpd`, `tranche-xl` | `references/extremes-reassurance.md` |
| Crédibilité | `credibilite` | `references/credibilite.md` |
| Solvabilité II | `scr` | `references/scr.md` |
| Réglementation tunisienne | `marge-solvabilite-tn`, `provisions-tn` | `references/tunisie.md` |
| Dossiers et validation | `rejouer`, `registre`, `comparer` | `references/dossiers-validation.md` |

`environnement` vérifie l'installation (Python, numpy, scipy, pandas).

Points à ne jamais deviner (demande-les à l'utilisateur s'ils manquent) :

- triangle : cumulé ou incrémental (`--type`) ; sur un nouveau fichier, lance d'abord `controler` et ne corrige aucune anomalie sans accord ;
- `tranche-xl` : nombre d'années couvertes (`--annees`) et indexation des montants ;
- `scr` : scénario de taux (`scenario_taux`, hausse ou baisse) ;
- `marge-solvabilite-tn` : tout montant manquant, et primes hors taxes et nettes d'annulations ;
- `bootstrap` : donne toujours la graine utilisée.

`references/methodes.md` indique pour chaque méthode la publication qui la valide ; `references/guide-des-methodes.md` donne les formules, conventions, domaines de validité, refus et limites. Consulte-les quand l'utilisateur demande comment un chiffre est calculé ou si une méthode s'applique à son cas. Pour organiser un projet dans Claude Code : `references/modele-CLAUDE.md` (variante tunisienne : `references/modele-CLAUDE-tunisie.md`).
