# Valeurs extrêmes et réassurance XL

Fichier de référence du skill `calcul-actuariel` pour les commandes `gpd` et `tranche-xl`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `gpd` | Loi de Pareto généralisée au-delà d'un seuil : xi, sigma, erreurs types, quantiles, primes pures de tranches | testé : McNeil (1997) tableau 1, données danoises |

Pour `gpd`, le fichier contient une ligne par sinistre (colonne choisie avec `--colonne`, sinon la première colonne numérique). Le seuil est un choix de jugement : utilise `--diagnostic-seuils` (excès moyen empirique) et compare plusieurs seuils avant de conclure, comme McNeil. Les quantiles et les primes de tranche portent sur la distribution des sinistres du fichier (au-delà de son seuil de collecte). Une tranche s'écrit `priorité,limite` et sa priorité doit dépasser le seuil. Les erreurs types rendues sont les erreurs asymptotiques de McNeil, (1 + ξ)/√N_u pour ξ : ce sont elles qu'il faut reporter. Pour l'incertitude sur ξ, cite aussi `intervalle_95_xi_profil` (vraisemblance profilée), plus fiable que l'intervalle de Wald sur de petits échantillons. Pour juger l'ajustement, lance `--test-ajustement 999` et cite la p-valeur d'Anderson-Darling ; si elle est sous 5 %, dis que la GPD s'ajuste mal à ce seuil.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `tranche-xl` | Tranche XL par risque sur un an : fréquence de Poisson × sévérité GPD, prime pure et écart type exacts, VaR et CTE (Panjer), burning cost, franchise et limite annuelles | testé : calcul indépendant R (evir, actuar), fiches validées |

Pour `tranche-xl`, même fichier de sinistres que `gpd`. `--annees` (nombre d'années couvertes par le fichier) est obligatoire : demande-le s'il manque, ne le devine pas. `--tranche priorité,limite` donne la limite haute (portée = limite − priorité) et la priorité doit être au moins égale au seuil. Les montants sont pris tels quels : si l'utilisateur ne précise pas qu'ils sont indexés (as-if), dis-le. La prime pure et l'écart type sont exacts ; la VaR et la CTE sont lues sur une grille de pas `--pas` (défaut portée / 1000). Cite le burning cost à côté de la prime du modèle et commente leur rapport. `--parametres xi,sigma` impose la GPD (étude de sensibilité) ; avec un xi négatif, écris `--parametres=-0.2,5`.
