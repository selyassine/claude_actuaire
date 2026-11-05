# Guide des méthodes du moteur

Ce guide décrit, pour chaque méthode, ce que le moteur calcule, sous quelles conventions, dans quel domaine il refuse de calculer et comment le résultat a été validé. Les valeurs citées en exemple sont les valeurs **publiées** ; le moteur les reproduit dans les tolérances indiquées (fiches de `tests/references/`, tests de `tests/test_publications.py`).

Version du moteur décrite : 0.3.0.

## Sommaire

1. [Règles communes](#1-règles-communes)
2. [Chain Ladder, Bornhuetter-Ferguson, Cape Cod](#2-chain-ladder-bornhuetter-ferguson-cape-cod)
3. [Mack](#3-mack)
4. [ODP analytique et bootstrap ODP](#4-odp-analytique-et-bootstrap-odp)
5. [Vie : survie, primes, provisions](#5-vie--survie-primes-provisions)
6. [Valeurs extrêmes : GPD](#6-valeurs-extrêmes--gpd)
7. [Crédibilité](#7-crédibilité)
8. [Agrégation du SCR](#8-agrégation-du-scr)
9. [Traçabilité et reproduction d'un calcul](#9-traçabilité-et-reproduction-dun-calcul)

---

## 1. Règles communes

- **Unités.** Le moteur ne convertit aucune unité. Triangle, primes et ultimes a priori doivent être dans la même devise et la même échelle (euros ou milliers d'euros). Pour BF et Cape Cod, un ratio médian « ultime Chain Ladder / prime » hors de [0,02 ; 50] déclenche une alerte d'unité.
- **Libellés.** Les années d'origine et les périodes sont des libellés texte. `2020.0` (lecture Excel) est ramené à `2020`. Une origine sans libellé, en double, ou absente du fichier de primes arrête le calcul.
- **Nombres.** `1 234,56`, `1.234,56` et `1,234.56` sont lus correctement. Un texte non numérique dans une donnée de calcul arrête le calcul ; seule la colonne des sinistres de `gpd` ignore les textes, en le signalant.
- **Refus.** Une entrée hors du domaine de la méthode produit `{"statut": "erreur"}` sur la sortie d'erreur, code 2, sans aucun résultat partiel. Une erreur inattendue donne le code 3.
- **Statut.** `ok` : aucun avertissement. `avertissements` : résultat utilisable, à lire avec les alertes. `incomplet` : une valeur non définie (NaN, infini) est apparue ; elle est rendue `null` et nommée, et ne doit pas être reportée. Les seuls « non définis » attendus (erreur relative d'une provision nulle) sont rendus `null` par la méthode elle-même et ne déclenchent pas `incomplet`.

## 2. Chain Ladder, Bornhuetter-Ferguson, Cape Cod

Commandes : `chain-ladder`, `bf`, `cape-cod`.

**Formules.** Sur le triangle cumulé \(C_{i,k}\) :

- facteur pondéré \(f_k = \sum_i C_{i,k+1} / \sum_i C_{i,k}\) sur les couples observés (option `--moyenne simple` : moyenne arithmétique des facteurs individuels) ;
- facteur cumulé \(F_k = f_k f_{k+1} \cdots f_{n-1} \times\) queue ;
- Chain Ladder : ultime \(U_i = C_{i,\text{dernier}} \times F_{\text{dernier}}\), provision \(R_i = U_i - C_{i,\text{dernier}}\) ;
- BF : \(U_i = C_{i,\text{dernier}} + U^{a\,priori}_i (1 - 1/F)\), avec \(U^{a\,priori}_i\) = prime × ratio ou ultime a priori fourni ;
- Cape Cod : ratio \(\hat{\ell} = \sum_i C_{i,\text{dernier}} / \sum_i P_i / F_i\), puis BF avec \(U^{a\,priori}_i = \hat{\ell} P_i\).

**Choix de jugement**, tous rendus dans `hypotheses` : `--periode N` (N dernières années calendaires), `--exclure origine@facteur`, `--facteurs-imposes facteur=valeur`, `--queue`, `--arrondi` (convention des exhibits de Friedland).

**Domaine et refus.** Triangle sans trou avant la dernière valeur de chaque ligne, sans ligne vide, sans valeur infinie, sans doublon, au moins deux périodes. Un facteur sans aucune observation utilisable (données, période ou exclusions) arrête le calcul au lieu de valoir 1 : il faut l'imposer en le justifiant. Facteurs imposés et queue : finis et strictement positifs. BF : ultimes a priori finis et positifs. Cape Cod : primes finies et strictement positives.

**Limites.** Pas d'ajustement d'inflation ni de niveau tarifaire : les primes du Cape Cod doivent être ramenées au même niveau avant l'appel. Le type de triangle deviné (`--type auto`) n'est qu'un indice, toujours signalé.

**Validation.** Friedland (2010), chapitres 7, 9 et 10, Exhibit I, données US Auto, au dollar près. Mack (1993), tableau 2, Taylor-Ashe. Exemple publié (Friedland ch. 9, BF sur sinistres déclarés, 3 dernières années, facteurs arrondis à 3 décimales) : provision totale 25 609 761.

```bash
python cli.py bf --entree friedland_us_auto_declares.csv --type cumule --primes friedland_us_auto_primes.csv --periode 3 --arrondi 3
```

## 3. Mack

Commande : `mack`.

**Formules (Mack 1993).** \(\hat\sigma_k^2 = \frac{1}{n-k-1} \sum_i C_{i,k} (C_{i,k+1}/C_{i,k} - f_k)^2\). Erreur de prédiction par origine :
\(\widehat{\mathrm{mse}}(R_i) = U_i^2 \sum_k \frac{\hat\sigma_k^2}{f_k^2} \left( \frac{1}{\hat C_{i,k}} + \frac{1}{\sum_j C_{j,k}} \right)\).
L'erreur totale ajoute les covariances entre années d'origine, qui partagent les mêmes facteurs estimés :
\(\widehat{\mathrm{mse}}(R) = \sum_i \left[ \widehat{\mathrm{mse}}(R_i) + U_i \Big(\sum_{j>i} U_j\Big) \sum_k \frac{2 \hat\sigma_k^2 / f_k^2}{\sum_{l} C_{l,k}} \right]\).
Le dernier \(\sigma^2\) est extrapolé par \(\min(\sigma_{n-2}^4/\sigma_{n-3}^2, \sigma_{n-3}^2, \sigma_{n-2}^2)\) (`--sigma-dernier mack`, défaut) ou égal au précédent (`precedent`, convention d'England et Verrall).

**Domaine et refus.** Triangle carré complet, au moins 4 × 4 (3 × 3 avec `precedent`), facteurs Chain Ladder standards sans queue ni exclusion, paramètres de variance finis.

**Limites.** Hypothèses de Mack (indépendance des années d'origine, variance proportionnelle à \(C_{i,k}\)) non testées par le moteur. Pas de queue stochastique.

**Pourquoi c'est utile.** Au banc d'essai sur les variantes, Claude sans skill mais avec Python s'est trompé deux fois sur l'erreur totale (terme de covariance) ; le moteur l'a rendue juste.

**Validation.** Mack (1993) tableau 3, Taylor-Ashe ; England et Verrall (2002) tableaux 13 et 14, RAA. Exemple publié (E&V tableau 14, RAA, `--sigma-dernier precedent`) : erreur de prédiction totale 27 172.

## 4. ODP analytique et bootstrap ODP

Commandes : `odp`, `bootstrap`.

**Formules (England et Verrall 2002).** Incréments \(X_{i,k}\) ~ Poisson sur-dispersé, \(E = m_{i,k}\), \(V = \phi m_{i,k}\), ajustés par les facteurs Chain Ladder. Dispersion \(\phi\) de Pearson ou de déviance divisée par \(n - p\) degrés de liberté. Erreur de prédiction analytique : \(\mathrm{mse} = \phi R + \mathrm{Var}(\hat R)\), la variance d'estimation étant obtenue par la méthode delta sur la matrice de covariance des paramètres du modèle log-linéaire (England et Verrall 2002, § 7.2). Bootstrap : rééchantillonnage des résidus de Pearson ajustés (facteur \(\sqrt{n/(n-p)}\)), réestimation, puis bruit de processus gamma de variance \(\phi m\).

**Domaine et refus.** Triangle carré au moins 3 × 3, facteurs définis, valeurs ajustées passées strictement positives, \(\phi > 0\), au moins 2 simulations, quantiles dans ]0, 1[. Sans `--dispersion`, le moteur prend Pearson et le signale.

**Limites.** Le bootstrap dépend de la graine (défaut 2026, toujours rendue) ; à 10 000 simulations, l'écart Monte-Carlo sur l'erreur de prédiction atteint 2 % : la tolérance de validation est 5 %.

**Validation.** E&V (2002) tableau 3 (ODP analytique, déviance, \(\phi\) = 1 049,8 ; erreur totale publiée 18 193) et tableaux 33-34 (bootstrap ; quantile à 95 % publié 87 668, à 5 %).

## 5. Vie : survie, primes, provisions

Commandes : `survie`, `tarif-vie`.

**Modèles de survie.** SSSM d'AMLCR par défaut (Makeham \(\mu_x = A + B c^x\), A = 0,00022, B = 2,7 × 10⁻⁶, c = 1,124, sélection \(0{,}9^{2-s}\) appliquée à la force de mortalité pendant 2 ans) ; `susm` (sans sélection) ; `makeham` (paramètres fournis) ; `table` (q_x fournis). Avec une table, la sélection s'applique à q (années entières).

**Conventions.** Temps discret annuel. Capital décès payé en fin d'année du décès ; primes et annuités payables d'avance. Frais initiaux à la souscription, frais de renouvellement à chaque échéance suivante. Provisions prospectives, juste avant la prime de l'année t : nette (base de la prime pure), brute (prime commerciale et frais), de frais (brute − nette), Zillmer complet (FPT).

**Domaine et refus.** Makeham : B > 0, c > 1, A + B ≥ 0. Table : âges entiers, consécutifs, sans doublon, q dans [0, 1]. Un âge avant le début de la table, ou un âge de départ après sa fin, arrête le calcul. Une sélection qui rendrait q > 1 arrête le calcul. Taux > −100 %. Capital positif, durées cohérentes (durée des primes ≤ durée du contrat), frais en pourcentage < 100 %.

**Limites.** Pas de temps continu, pas de fractionnement des primes, pas de participation aux bénéfices ni de chargements sur encours. Au-delà du dernier âge de la table, q = 1 (hypothèse rendue).

**Validation.** Note MLC de Dickson, Hardy et Waters (SOA 2012), exemples SN2.3 et SN2.4, au centime. Exemple publié (vie entière, âge 50, capital 100 000, 4 %, frais 50 % + 250 puis 3 % + 25) : provision FPT à 10 ans 13 313,34.

## 6. Valeurs extrêmes : GPD

Commande : `gpd`.

**Formules (McNeil 1997).** Excès \(Y = X - u\) des pertes \(X > u\), ajustés par maximum de vraisemblance à la GPD \(G_{\xi,\sigma}(y) = 1 - (1 + \xi y/\sigma)^{-1/\xi}\). Queue \(1 - F(x) = (N_u/n)(1 + \xi (x-u)/\sigma)^{-1/\xi}\). Quantile \(x_p = u + \frac{\sigma}{\xi}\left[\left(\frac{n}{N_u}(1-p)\right)^{-\xi} - 1\right]\). Prime pure de la tranche (r, R) : \(\int_r^R (1 - F(x))\,dx\).

**Incertitude et ajustement (nouveau en 0.3.0).**

- Erreurs types asymptotiques de McNeil, \((1+\xi)/\sqrt{N_u}\) pour ξ, et intervalles de Wald à 95 %.
- Intervalle à 95 % de ξ par **vraisemblance profilée** (Coles 2001, § 4.3.4), plus fiable que Wald pour les petits échantillons et les queues lourdes. Une alerte est émise si les deux intervalles diffèrent nettement.
- Statistiques de Kolmogorov-Smirnov et d'Anderson-Darling des excès contre la GPD ajustée. Avec `--test-ajustement N` (par exemple 999), p-valeur d'Anderson-Darling par bootstrap paramétrique (les paramètres étant estimés, les tables usuelles ne s'appliquent pas). Alerte si p < 5 %.
- `--diagnostic-seuils` : excès moyen empirique et ξ, σ réestimés à chaque seuil, pour vérifier la stabilité.

**Optimisation.** Quatre points de départ ; le meilleur optimum est retenu, et le diagnostic (`diagnostic_optimisation`) signale des optima distincts.

**Domaine et refus.** Pertes positives et finies, au moins deux excès, tranches de priorité ≥ seuil. Alertes : moins de 50 dépassements, ξ ≤ −0,5 (erreurs types non valables), ξ ≥ 1 (espérance infinie), quantile au-delà du double du maximum observé.

**Limites.** Le choix du seuil reste un jugement. Pas de dépendance temporelle ni de déclustering.

**Validation.** McNeil (1997) tableau 1, données danoises du paquet R `evir` (2 167 observations au lieu des 2 156 de l'article : dépassements et ξ exacts, quantiles à 1,5 %). Exemple publié (u = 10) : quantile à 99,9 % ≈ 95, prime de la tranche (50, 200) ≈ 0,13. Les intervalles profilés et les statistiques d'ajustement sont recalculés indépendamment avec scipy dans `tests/test_production.py`.

## 7. Crédibilité

Commande : `credibilite`.

**Modèles.** Bühlmann (poids égaux), Bühlmann-Straub, hiérarchique de Jewell (cohortes), régression de Hachemeister (tendance linéaire), avec intercept au barycentre en option (Bühlmann et Gisler 2005, § 8.4). Prime de crédibilité \(z_i \bar X_i + (1 - z_i) \hat\mu\), \(z_i = w_i / (w_i + s^2/a)\).

**Estimateurs.** Sans biais (Bühlmann et Gisler 2005), tronqué à 0, ou itératif de Bichsel-Straub (défaut du modèle hiérarchique).

**Domaine et refus.** Au moins deux entités ; pas de doublon entité-période ; période renseignée et numérique ; poids positifs ou nuls et finis ; une entité dans une seule cohorte. Les couples entité-période absents sont ignorés et comptés dans un avertissement.

**Limites.** Moins de 5 entités : variances structurelles très imprécises (alerte). Variance entre entités nulle : toutes les primes valent la prime collective (alerte).

**Validation.** Vignette « Credibility theory features of actuar » (Dutang, Goulet, Milhaud, Pigeon), données de Hachemeister (1975). Exemple publié (Bühlmann-Straub) : prime collective 1 684, variance entre 89 639, variance intra 139 120 026.

## 8. Agrégation du SCR

Commande : `scr`.

**Ce que le moteur fait.** Il agrège des SCR de sous-modules **déjà calculés** avec les matrices de corrélation de la formule standard (règlement délégué (UE) 2015/35, annexe IV et articles 114, 119, 136, 144, 146, 151, 160, 164), ajoute les incorporels, le risque opérationnel (art. 204 : min(0,3 BSCR ; Op) + 0,25 Exp_ul) et les ajustements pour capacité d'absorption des provisions techniques et des impôts différés.

**Ce qu'il ne fait pas.** Il n'applique aucun choc : les SCR de taux, actions, longévité, etc. sont des entrées. Il ne calcule pas les fonds propres éligibles ni le ratio de solvabilité.

**Domaine et refus.** Clés inconnues refusées (une faute de frappe ne passe pas inaperçue) ; montants finis, positifs, sauf les capacités d'absorption (négatives) ; `scenario_taux` obligatoire dès que le module marché est détaillé (paramètre A de l'article 164).

**Validation.** SFCR publiés de CCR (2024, état S.25.01) et de l'IPBP (2016), à l'euro. Exemple publié (CCR 2024, milliers d'euros) : BSCR 2 738 047, SCR 2 414 456. Les matrices non-vie (art. 114, 119) sont contrôlées contre le règlement mais sans cas publié détaillé.

## 9. Traçabilité et reproduction d'un calcul

Chaque sortie contient :

- `moteur.version` et `moteur.environnement` (versions de Python, numpy, scipy, pandas) ;
- `horodatage_utc` ;
- `entrees` : chaque fichier avec son empreinte SHA-256 ;
- `options`, `hypotheses`, `resultats`, `avertissements`, `statut` ;
- `reproduction.arguments` et `reproduction.commande` : la commande exacte à relancer ;
- `empreinte_resultats` : SHA-256 du bloc `resultats` sérialisé de façon canonique.

**Rejouer un calcul archivé.**

```bash
python cli.py chain-ladder --entree payes.csv --type cumule > calcul.json
python cli.py rejouer --sortie calcul.json
```

`rejouer` vérifie d'abord que le bloc `resultats` n'a pas été retouché (empreinte), puis que chaque fichier d'entrée n'a pas changé (SHA-256). Il relance ensuite la commande archivée et compare les résultats à 10⁻⁹ près en relatif (`--tolerance`). La sortie liste les écarts et signale un changement de version du moteur ou des bibliothèques.

**Ce que la traçabilité ne prouve pas.** Une empreinte prouve l'identité d'un fichier, pas la qualité des données ni l'identité de la personne qui a lancé le calcul. La validation humaine d'un résultat reste à tracer dans le processus de l'utilisateur.
