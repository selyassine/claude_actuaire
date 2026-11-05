---
name: calcul-actuariel
description: Moteur de calcul actuariel testé sur des résultats publiés. À utiliser pour tout chiffre actuariel (provisions, IBNR, triangles, Chain Ladder, Mack, bootstrap, Bornhuetter-Ferguson, tables de mortalité, annuités, provisions vie, GPD, tarification de tranche de réassurance XL, crédibilité, SCR, comparaison avec un modèle externe) au lieu de calculer de tête. Use for any actuarial calculation (reserving, life contingencies, EVT, XL reinsurance layer pricing, credibility, SCR, model validation).
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
python <skill>/scripts/cli.py survie --modele sssm --taux 0.04 --age 50 --n 20
python <skill>/scripts/cli.py tarif-vie --modele sssm --taux 0.04 --type vie-entiere --age 50 --capital 100000 \
    --frais-initiaux-pct 0.5 --frais-initiaux-fixe 250 --frais-renouvellement-pct 0.03 --frais-renouvellement-fixe 25 --durees 0,1,2,10
python <skill>/scripts/cli.py rejouer --sortie calcul.json     # refait un calcul archivé et compare
python <skill>/scripts/cli.py registre --sorties sorties/ --note hypotheses.md            # registre des hypothèses du dossier
python <skill>/scripts/cli.py comparer --resultats calcul.json --lister                  # chemins comparables
python <skill>/scripts/cli.py comparer --resultats calcul.json --externe modele.csv      # rapport d'écarts
```

Sortie par défaut : JSON avec `statut` (`ok`, `avertissements` ou `incomplet`), `methode`, `moteur` (version et versions des bibliothèques), `entrees` (fichier + empreinte SHA-256), `options`, `hypotheses`, `resultats`, `avertissements`, `reproduction` (commande exacte) et `empreinte_resultats`. Une valeur `null` dans les résultats est une valeur non définie (par exemple l'erreur relative d'une provision nulle) : ne la remplace pas par un chiffre. En cas d'erreur, la commande ne rend aucun résultat : un JSON `{"statut": "erreur", "erreur": ...}` sur la sortie d'erreur.

## Formats d'entrée

- **Triangle** : CSV (séparateur `,` `;` ou tabulation, détecté) ou Excel. Première colonne = année d'origine, en-têtes = périodes de développement, cellules futures vides. Avec `;` comme séparateur, la virgule décimale est acceptée. Précise toujours `--type cumule` ou `--type incremental` quand tu le sais : la détection automatique n'est qu'un indice.
- **Primes** (BF, Cape Cod) : colonnes `Origine`, `Prime`, et pour BF `Ratio` ou `Ultime_a_priori` (ou l'option `--ratio`). Une origine par ligne, les mêmes libellés que le triangle, la même unité monétaire (le moteur alerte si le ratio ultime / prime semble indiquer une unité différente).

Si les données de l'utilisateur sont dans un autre format, convertis-les d'abord dans ce format en fichier, puis appelle le script.

Sur un nouveau fichier, lance d'abord `controler`. Présente les anomalies bloquantes et les alertes à l'utilisateur et demande-lui comment les traiter : ne corrige rien toi-même (ne complète pas un trou, ne retire pas un doublon, n'exclus pas un facteur atypique) sans son accord, puis passe sa décision en option explicite de la méthode. Pour organiser un projet actuariel dans Claude Code, `references/modele-CLAUDE.md` donne un modèle de CLAUDE.md.

## Commandes disponibles

| Commande | Rôle | Statut |
| --- | --- | --- |
| `environnement` | Vérifie Python, numpy, scipy, pandas | disponible |
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

| Commande | Rôle | Statut |
| --- | --- | --- |
| `mack` | Erreur de prédiction de Chain Ladder (Mack 1993), par année et totale | testé : Mack (1993) tableau 3, England et Verrall (2002) tableaux 13-14 |
| `odp` | Poisson sur-dispersé, erreur de prédiction analytique | testé : England et Verrall (2002) tableau 3 |
| `bootstrap` | Bootstrap ODP : moyenne, erreur de prédiction, quantiles (dont 99,5 %) | testé : England et Verrall (2002) tableaux 33-34, à 5 % près |

Ces trois commandes exigent un triangle carré complet et utilisent les facteurs Chain Ladder standards (sans queue ni exclusion). Options : `mack --sigma-dernier mack|precedent`, `odp --dispersion pearson|deviance`, `bootstrap --simulations N --graine G`. Donne toujours la graine utilisée : elle rend le résultat reproductible.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `survie` | q, espérance de vie, annuités dues, assurances décès, mixte, capital différé | propriétés testées |
| `tarif-vie` | Primes pure et commerciale, provisions nette, brute, de frais et Zillmer FPT | testé : note MLC (Dickson, Hardy, Waters) SN2.3-SN2.4, au centime |

Modèle de survie : `--modele sssm` (défaut, Standard Select Survival Model d'AMLCR), `susm` (ultime), `makeham --A --B --c`, ou `table --table qx.csv` (colonnes `Age`, `qx`). Sélection libre avec `--selection-facteur k --selection-duree d`. Temps discret annuel : capital décès en fin d'année, primes et annuités d'avance. Contrats : `vie-entiere`, `temporaire --duree n`, `mixte --duree n`, avec `--duree-primes`. Les frais initiaux sont payés à la souscription, les frais de renouvellement à chaque échéance suivante. Les provisions sont prospectives, juste avant la prime de l'année t.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `gpd` | Loi de Pareto généralisée au-delà d'un seuil : xi, sigma, erreurs types, quantiles, primes pures de tranches | testé : McNeil (1997) tableau 1, données danoises |

Pour `gpd`, le fichier contient une ligne par sinistre (colonne choisie avec `--colonne`, sinon la première colonne numérique). Le seuil est un choix de jugement : utilise `--diagnostic-seuils` (excès moyen empirique) et compare plusieurs seuils avant de conclure, comme McNeil. Les quantiles et les primes de tranche portent sur la distribution des sinistres du fichier (au-delà de son seuil de collecte). Une tranche s'écrit `priorité,limite` et sa priorité doit dépasser le seuil. Les erreurs types rendues sont les erreurs asymptotiques de McNeil, (1 + ξ)/√N_u pour ξ : ce sont elles qu'il faut reporter. Pour l'incertitude sur ξ, cite aussi `intervalle_95_xi_profil` (vraisemblance profilée), plus fiable que l'intervalle de Wald sur de petits échantillons. Pour juger l'ajustement, lance `--test-ajustement 999` et cite la p-valeur d'Anderson-Darling ; si elle est sous 5 %, dis que la GPD s'ajuste mal à ce seuil.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `tranche-xl` | Tranche XL par risque sur un an : fréquence de Poisson × sévérité GPD, prime pure et écart type exacts, VaR et CTE (Panjer), burning cost, franchise et limite annuelles | testé : calcul indépendant R (evir, actuar), fiches validées |

Pour `tranche-xl`, même fichier de sinistres que `gpd`. `--annees` (nombre d'années couvertes par le fichier) est obligatoire : demande-le s'il manque, ne le devine pas. `--tranche priorité,limite` donne la limite haute (portée = limite − priorité) et la priorité doit être au moins égale au seuil. Les montants sont pris tels quels : si l'utilisateur ne précise pas qu'ils sont indexés (as-if), dis-le. La prime pure et l'écart type sont exacts ; la VaR et la CTE sont lues sur une grille de pas `--pas` (défaut portée / 1000). Cite le burning cost à côté de la prime du modèle et commente leur rapport. `--parametres xi,sigma` impose la GPD (étude de sensibilité) ; avec un xi négatif, écris `--parametres=-0.2,5`.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `registre` | Registre des hypothèses d'un dossier : consolide les sorties archivées, classe les hypothèses (choix de jugement, valeurs par défaut, méthode), détecte les incohérences, écrit la note d'hypothèses | disponible |
| `comparer` | Rapport d'écarts ligne à ligne entre les résultats d'un modèle externe et une sortie archivée du moteur | testé (propriétés et refus) |

Pour un dossier de plusieurs calculs, enregistre chaque sortie JSON dans un même dossier (par exemple `sorties/`), puis lance `registre --sorties sorties/ --note hypotheses.md` avant de rédiger la synthèse. Présente d'abord les incohérences, puis les valeurs par défaut à faire confirmer par l'utilisateur. Ne présente pas une note dont la conclusion est `bloquant`.

Pour valider le modèle d'un utilisateur (Excel, logiciel interne) : 1) lance la méthode du moteur sur les mêmes données et enregistre la sortie JSON dans un fichier ; 2) lance `comparer --lister` pour voir les chemins ; 3) écris un CSV `chemin;valeur` (colonnes facultatives `libelle`, `tolerance_relative`) en recopiant les valeurs du modèle externe telles quelles, sans les arrondir ni les convertir ; 4) lance `comparer`. Rapporte la conclusion, chaque ligne `ecart` avec sa valeur moteur et externe, et les avertissements (facteur d'unité, convention de signe, hypothèse commune). Une ligne `arrondi` est conforme à l'arrondi publié près. N'explique jamais un écart sans l'avoir vérifié : propose des causes, présente-les comme des pistes.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `credibilite` | Bühlmann, Bühlmann-Straub, hiérarchique (Jewell), régression de Hachemeister : variances structurelles, facteurs et primes de crédibilité | testé : vignette actuar sur les données de Hachemeister (1975) |

Pour `credibilite`, le fichier est au format long : une ligne par entité et période, avec les colonnes `Entite`, `Periode`, `Ratio`, `Poids` (sauf `--modele buhlmann`) et `Cohorte` (modèle `hierarchique`). Estimateurs : `--estimateur sans-biais` (défaut, Bühlmann et Gisler 2005) ou `iteratif` (Bichsel-Straub ; défaut du modèle hiérarchique). Pour la régression, préfère `--barycentre` : sans lui, la droite de crédibilité peut sortir de l'intervalle entre droites individuelle et collective (cas de l'État 4 de Hachemeister).

| Commande | Rôle | Statut |
| --- | --- | --- |
| `scr` | Agrégation formule standard : sous-modules, modules, BSCR, risque opérationnel, ajustements, SCR | testé : SFCR CCR 2024 (S.25.01) et IPBP 2016, à l'euro |

`scr` agrège des SCR déjà calculés (il n'applique pas les chocs). Entrée JSON, chaque module étant un nombre ou un dictionnaire de sous-modules :

```json
{"marche": {"scenario_taux": "baisse", "taux": 65.0, "actions": 49.2, "immobilier": 7.4, "spread": 20.1, "change": 1.9, "concentration": 4.0},
 "contrepartie": {"type1": 11.2, "type2": 0.05},
 "vie": {"mortalite": 0, "longevite": 30.3, "invalidite": 0, "cessation": 0, "frais": 19.3, "revision": 0, "catastrophe": 0},
 "sante": {"slt": {"longevite": 1.6, "frais": 0.3, "revision": 3.4}, "nslt": {"primes_provisions": 9.4, "cessation": 0}, "catastrophe": {"accident_de_masse": 1.0, "concentration": 0.75, "pandemie": 1.0}},
 "non_vie": {"primes_provisions": 50, "cessation": 5, "catastrophe": {"naturelle": 30, "reassurance_non_proportionnelle_dommages": 0, "humaine": 20, "autres": 5}},
 "incorporels": 0,
 "operationnel": {"op": 4.0, "exp_ul": 0},
 "ajustements": {"provisions_techniques": -4.2, "impots_differes": -11.2, "fonds_cantonnes": 0}}
```

`scenario_taux` (`hausse` ou `baisse`) fixe le paramètre A de l'article 164 : demande-le à l'utilisateur s'il manque, ne le devine pas. Les capacités d'absorption se saisissent en négatif. `operationnel` peut aussi être un montant déjà calculé. Le fichier `references/methodes.md` indique pour chaque méthode la publication qui la valide ; `references/guide-des-methodes.md` donne les formules, conventions, domaines de validité, refus et limites. Consulte-le quand l'utilisateur demande comment un chiffre est calculé ou si une méthode s'applique à son cas.
