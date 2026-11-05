# Guide des méthodes du moteur

Ce guide décrit, pour chaque méthode, ce que le moteur calcule, sous quelles conventions, dans quel domaine il refuse de calculer et comment le résultat a été validé. Les valeurs citées en exemple sont les valeurs **publiées** ; le moteur les reproduit dans les tolérances indiquées (fiches de `tests/references/`, tests de `tests/test_publications.py`).

Version du moteur décrite : 0.5.3.

## Sommaire

1. [Règles communes](#1-règles-communes)
2. [Chain Ladder, Bornhuetter-Ferguson, Cape Cod](#2-chain-ladder-bornhuetter-ferguson-cape-cod)
3. [Mack](#3-mack)
4. [ODP analytique et bootstrap ODP](#4-odp-analytique-et-bootstrap-odp)
5. [Vie : survie, primes, provisions](#5-vie--survie-primes-provisions)
6. [Valeurs extrêmes : GPD](#6-valeurs-extrêmes--gpd)
   - [6 bis. Tranche de réassurance XL sur un an](#6-bis-tranche-de-réassurance-xl-sur-un-an)
7. [Crédibilité](#7-crédibilité)
8. [Agrégation du SCR](#8-agrégation-du-scr)
   - [8 bis. Marge de solvabilité tunisienne](#8-bis-marge-de-solvabilité-tunisienne)
   - [8 ter. Provisions techniques tunisiennes](#8-ter-provisions-techniques-tunisiennes)
9. [Traçabilité et reproduction d'un calcul](#9-traçabilité-et-reproduction-dun-calcul)
10. [Validation d'un modèle externe : comparer](#10-validation-dun-modèle-externe--comparer)
11. [Contrôle qualité des données : controler](#11-contrôle-qualité-des-données--controler)
12. [Registre des hypothèses d'un dossier : registre](#12-registre-des-hypothèses-dun-dossier--registre)

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

**Modèles de survie.** SSSM d'AMLCR par défaut (Makeham \(\mu_x = A + B c^x\), A = 0,00022, B = 2,7 × 10⁻⁶, c = 1,124, sélection \(0{,}9^{2-s}\) appliquée à la force de mortalité pendant 2 ans) ; `susm` (sans sélection) ; `makeham` (paramètres fournis) ; `table` (q_x fournis) ; `td99` (alias `tm99`) et `tv99`, tables réglementaires tunisiennes de l'arrêté du 27 février 2001 (art. 5, modifié le 5 janvier 2009), TD99 pour les contrats en cas de décès et TV99 pour les contrats en cas de survie. Avec une table, la sélection s'applique à q (années entières).

**Tables tunisiennes.** Transcrites des pages 200 à 207 du Code des assurances (Imprimerie Officielle) dans `scripts/actuaire/donnees/tables_tunisie_99.csv`. Par défaut q_x = 1 − l_{x+1}/l_x ; `--qx-source publie` prend la colonne q_x imprimée, arrondie à 0,01 %, qui s'écarte des l_x à partir de 92 ans. Un taux technique au-dessus de 4 % est signalé (plafond de l'art. 5 b pour les contrats de plus de 10 ans) ; le plafond de 70 % du taux moyen des titres d'État n'est pas vérifié.

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

## 6 bis. Tranche de réassurance XL sur un an

Commande : `tranche-xl` (nouveau en 0.4.0).

**Modèle collectif.** Nombre annuel de sinistres au-delà du seuil u : Poisson de paramètre \(\lambda = N_u / \text{années}\). Montant d'un tel sinistre : \(u + \text{GPD}(\xi, \sigma)\), ajustée comme dans `gpd` ou imposée (`--parametres`). Charge d'un sinistre pour la tranche (r, R) : \(L = \min(\max(X - r, 0), R - r)\). Charge annuelle \(S = L_1 + \dots + L_N\).

**Calculs.**

- Prime pure et écart type exacts : \(E[S] = \lambda \int_r^R \bar F_u(x)\,dx\) et \(\mathrm{Var}[S] = \lambda \int_r^R 2(x - r) \bar F_u(x)\,dx\), où \(\bar F_u\) est la survie GPD conditionnelle au seuil. La prime annuelle est égale à la prime par sinistre de `gpd` (McNeil 1997, § 4.5) multipliée par le nombre de sinistres par an : un test l'impose.
- Loi de S : discrétisation de L par la méthode des arrondis (pas h, défaut portée / 1000 ; la masse des sinistres qui épuisent la tranche est portée par le point R − r), puis récurrence de Panjer (1981) arrêtée quand la masse restante est sous 1e-12. VaR : plus petite valeur de la grille où la fonction de répartition atteint le niveau. CTE : \(E[S \mid S > \text{VaR}]\), définition d'actuar.
- Franchise annuelle D et limite annuelle L (AAD, AAL) : \(\min(\max(S - D, 0), L)\) sur la loi discrète.
- Burning cost : charge historique moyenne de la tranche par an, sans indexation, avec le nombre de sinistres historiques touchant et épuisant la tranche.

**Domaine et refus.** Années d'observation > 0 ; priorité ≥ seuil ; limite > priorité ; pas qui divise la portée ; niveaux dans ]0, 1[ ; σ > 0 ; franchise ≥ 0 ; limite annuelle > 0 ; au moins un dépassement. Fréquence trop élevée pour Panjer (P(S = 0) nulle en précision machine) : refus, avec la piste d'un seuil ou d'une priorité plus haute.

**Alertes.** Moins de 50 dépassements ; moins de 5 sinistres historiques dans la tranche (burning cost non fiable) ; prime du modèle hors de [0,5 ; 2] fois le burning cost ; discrétisation qui écarte la prime de plus de 0,1 % ; plus d'un sinistre sur deux épuisant la tranche.

**Limites.** Pas d'indexation (les montants doivent être mis en as-if avant l'appel), fréquence stable sans tendance ni surdispersion, pas de reconstitutions payantes, pas de clause d'indexation du traité.

**Validation.** Calcul indépendant en R (script `tests/references/r/tranche_xl.R`, sortie archivée à côté) : evir 1.7.4 pour l'ajustement GPD des données danoises, actuar 3.3.7 pour `discretize`, `aggregateDist` (méthode récursive), `quantile` et `CTE`. Trois fiches : paramètres d'evir imposés (accord à 1e-9 près), cas exponentiel ξ = 0 (accord à 1e-9 près), chaîne complète avec ajustement par le moteur (accord à 0,5 %, les deux optimiseurs trouvant ξ = 0,4970 et 0,4968). Fiches validées par Yassine le 2026-11-05. Exemple (données danoises, u = 10, 11 ans, tranche 50-200) : prime pure annuelle 25,94, écart type 47,47, VaR à 99,5 % 232,8 ; burning cost 34,23.

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

## 8 bis. Marge de solvabilité tunisienne

Commande : `marge-solvabilite-tn` (nouveau en 0.5.0).

**Ce que le moteur fait.** Il calcule le montant minimum réglementaire de la marge de solvabilité du Code des assurances tunisien (art. 58 bis, loi n° 2002-37 du 1er avril 2002) :

- non-vie : le plus élevé de 20 % des primes émises et acceptées × max(primes retenues / primes émises ; 50 %) et de 25 % de la charge annuelle moyenne des sinistres × max(charge nette / charge brute ; 50 %) ;
- la charge de la période = règlements des 3 derniers exercices (7 pour l'assurance crédit à titre principal) + PSAP de fin − PSAP de début − recours encaissés ;
- vie : 4 % des provisions mathématiques × max(net / brut ; 85 %) + 3 ‰ des capitaux sous risque × max(net / brut ; 50 %), les capitaux sous risque étant les capitaux assurés moins les provisions mathématiques ;
- société mixte : somme des deux.

Avec `marge_constituee`, il additionne les éléments de l'article 58 (50 % du capital non libéré, pertes et incorporels déduits) et rend l'excédent et le taux de couverture.

**Ce qu'il ne fait pas.** Il n'évalue pas les éléments constitutifs et ne vérifie pas l'accord du CGA sur les plus-values ou les autres éléments. Il ne calcule pas les provisions : PSAP, PM et capitaux sont des entrées.

**Entrée.** Un fichier JSON :

```json
{"non_vie": {"primes_emises_acceptees": 100000, "primes_retenues": 60000,
             "sinistres": {"reglements": [40000, 45000, 50000], "psap_debut": 70000, "psap_fin": 80000,
                           "recours_encaisses": 5000, "charge_nette": 56000}},
 "vie": {"provisions_mathematiques_brutes": 500000, "provisions_mathematiques_nettes": 400000,
         "capitaux_assures_bruts": 2500000, "capitaux_sous_risque_nets": 1200000},
 "marge_constituee": {"capital_libere": 10000, "reserves": 3000, "actifs_incorporels": 500}}
```

**Règles et choix rendus comme hypothèses.** Les primes sont « nettes d'impôts et d'annulations » (art. 58 bis a) : des primes TTC surestiment le minimum. Les recours encaissés sont déduits de la charge, comme l'écrit le texte. Le rapport de rétention sinistres est la charge nette sur la charge brute de la même période (choix). Le texte fixe un plancher au rapport net / brut mais pas de plafond : un rapport supérieur à 1 est conservé et signalé (choix).

**Domaine et refus.** Clés inconnues refusées ; nombre d'exercices de règlements égal à 3 (7 avec `assurance_credit`) ; primes et bruts strictement positifs ; montants de la marge constituée positifs (le signe est appliqué par le moteur). Un net supérieur au brut est signalé. Une marge constituée inférieure au minimum est signalée.

**Validation.** Aucun texte ne publie d'exemple chiffré : trois cas construits (non-vie, vie, mixte avec assurance crédit) sont recalculés indépendamment en R (`tests/references/r/marge_tunisie.R`), fiches et interprétations validées par Yassine le 2026-11-05.

## 8 ter. Provisions techniques tunisiennes

Commande : `provisions-tn` (nouveau en 0.5.1). Règles non-vie de l'arrêté du ministre des finances du 27 février 2001. Le fichier JSON contient un ou plusieurs blocs :

| Bloc | Article | Ce que fait le moteur |
| --- | --- | --- |
| `ppna` | 17 | Prorata temporis contrat par contrat sur la prime commerciale, en jours exacts (convention ci-dessous) : prime × (échéance − inventaire) / (échéance − effet) ; toute la prime pour un contrat à effet futur, rien pour un contrat échu. Totaux par catégorie. |
| `prc` | 19 | Par catégorie : ratio = (charge de sinistres + frais) / primes acquises des deux derniers exercices ; PRC = max(ratio − 1 ; 0) × PPNA. |
| `frais_gestion_sinistres` | 21 | Frais retenus = max(frais estimés ; minimum de 5 %). Par défaut le minimum porte sur la PSAP frais compris (frais ≥ 5/95 de la PSAP hors frais) ; `"base_minimum": "psap_hors_frais"` le calcule sur la PSAP hors frais. |
| `auto_materiels` | 22 | La plus élevée de trois évaluations : dossier par dossier (fournie), coût moyen (nombre de dossiers × coût moyen), cadences de règlement (provision totale d'une sortie `chain-ladder` archivée, passée par `--cadences`). |
| `equilibrage` | 24 | Crédit et caution : dotation = min(75 % de l'excédent technique ; plafond − provision), plafond = 150 % de la plus forte prime nette des 5 exercices précédents. |
| `egalisation_grele` | 25 | Grêle : même règle, plafond = 200 % des primes de l'exercice. |
| `rentes` | 27 | Provision mathématique des rentes × 1,05. |

**Textes.** Arrêté du 27 février 2001 dans sa version consolidée du Code des assurances (édition IORT 2020), modifié par les arrêtés du 28 mars 2005 (art. 33, représentation), du 5 janvier 2009 (art. 5 et 8, bases techniques vie), du 6 juin 2011 (art. 25, al. 2, égalisation pour sinistralité exceptionnelle), du 3 mars 2012 (art. 19, al. 2, révision de la PRC autorisée par le CGA pour événements exceptionnels, non modélisée) et du 1er mars 2016 (art. 31 et 31 bis, représentation).

**Conventions.** PPNA : fraction non acquise = (échéance − inventaire) / (échéance − effet) en jours ; la date d'effet est le premier jour couvert, la date d'échéance le premier jour non couvert, et le jour d'inventaire est acquis.

**Interprétations rendues comme hypothèses.** Les primes acquises de la PRC sont fournies déjà corrigées (primes restant à émettre, primes à annuler, variation de PPNA). La base du minimum de frais est la PSAP frais compris, sauf option. Une perte technique est imputée sur la provision d'équilibrage ou d'égalisation, dans la limite de son montant (l'arrêté ne décrit pas la reprise).

**Ce qu'il ne fait pas.** Il n'évalue pas les dossiers un par un, ne calcule pas le coût moyen des exercices antérieurs, et ne calcule pas les PM de rentes (utiliser `survie` ou `tarif-vie`).

**Domaine et refus.** Clés inconnues refusées ; dates au format AAAA-MM-JJ, échéance après l'effet ; primes acquises strictement positives ; 5 exercices de primes pour l'équilibrage ; `--cadences` obligatoire pour `auto_materiels` et limitée à une sortie `chain-ladder` dont l'empreinte est intacte et dont le statut n'est pas `incomplet` ; ses avertissements sont recopiés. Le moteur ne peut pas vérifier que les trois évaluations portent sur le même périmètre (exercices, unité, tardifs) : il le rend en hypothèse et signale un écart de plus du simple au double.

**Validation.** Aucun texte ne publie d'exemple chiffré : un cas construit couvrant les sept règles est recalculé indépendamment en R (`tests/references/r/provisions_tunisie.R`), fiche et interprétations validées par Yassine le 2026-11-05.

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

## 10. Validation d'un modèle externe : comparer

Commande : `comparer` (nouveau en 0.4.0).

C'est la validation par réplication indépendante : le modèle de l'utilisateur et le moteur calculent sur les mêmes données, et chaque écart désigne une erreur, une hypothèse divergente, une ambiguïté de spécification ou un arrondi.

**Entrées.** Une sortie JSON du moteur (son empreinte de résultats est vérifiée : un fichier retouché est refusé) et un CSV ou Excel du modèle externe avec les colonnes `chemin` et `valeur`, et en option `libelle` et `tolerance_relative` (qui remplace la tolérance générale pour la ligne). `--lister` donne tous les chemins numériques de la sortie du moteur.

**Classement de chaque ligne.**

- `conforme` : \(|e - m| \le \max(\text{tolérance absolue}, \text{tolérance relative} \times |m|)\), défauts 0 et 0,1 %.
- `arrondi` : hors tolérance, mais l'écart est au plus la demi-unité de la dernière décimale écrite dans le fichier externe (« 18 402,4 » couvre ± 0,05). Seulement pour une valeur écrite en texte (CSV) ; une cellule Excel numérique n'a pas de décimales publiées.
- `ecart`, `chemin_absent`, `valeur_externe_invalide`, `non_numerique_moteur`.

**Conclusion.** `conforme` si toutes les lignes sont conformes ou arrondies, sinon `ecarts_a_analyser`. Le rapport donne le décompte, l'écart relatif maximal et le nombre de chemins du moteur non comparés.

**Diagnostic des écarts.** Si au moins trois écarts suivent le même rapport externe / moteur à 1 % près, une alerte le signale : facteur d'unité (1 000, 1 000 000, 100 et leurs inverses), convention de signe (rapport −1) ou hypothèse commune divergente (taux, exposition). Ce sont des pistes, pas des conclusions.

**Limites.** Le moteur compare des chiffres, il ne lit pas la spécification du modèle externe : la correspondance entre les grandeurs (le fichier `chemin;valeur`) est un travail d'analyse à vérifier.

## 11. Contrôle qualité des données : controler

Commande : `controler` (nouveau en 0.4.1). Aucun calcul actuariel : le moteur signale et compte, il ne corrige rien. Chaque traitement reste une décision de l'actuaire, à passer ensuite en option explicite de la méthode (`--exclure`, cellule complétée, ligne retirée) et à documenter.

**Gravités.** `bloquant` : la méthode refusera le fichier tel quel. `alerte` : le calcul passera, mais le résultat peut être faussé. `info` : caractéristique à connaître. Conclusion : `bloquant`, `a_examiner` ou `pret`.

**Triangle** (`--nature triangle --type cumule|incremental`).

- Bloquant : triangle vide ou d'une seule période, origine sans libellé ou en double, période en double, texte non numérique, valeur infinie, ligne vide, trou avant la dernière valeur observée.
- Alerte : forme inattendue (nombre de valeurs observées croissant d'une origine à la suivante), montant négatif, baisse du cumulé, cumulé nul puis positif (facteur infini), facteur individuel atypique.
- Facteur atypique : pour chaque passage, médiane m et MAD normalisée s (1,4826 × médiane des écarts absolus) des log-facteurs individuels, avec au moins 4 facteurs ; signalé si \(|\ln f - m| > 3{,}5\,s\). Le message donne l'option `--exclure` correspondante. Sur le triangle RAA, seul le facteur 1982, 3-4 (1,977 contre une médiane de 1,163) est signalé.

**Sinistres** (`--nature sinistres`). Bloquant : montant négatif, valeur infinie, aucune colonne numérique, colonne en double. Alerte : texte non numérique (ignoré par `gpd` et `tranche-xl`), montants nuls, montants répétés (double saisie ou forfait). Info : cellules vides, maximum plus de dix fois supérieur au suivant.

**Primes** (`--nature primes`, avec `--triangle` pour confronter les origines). Bloquant : colonne `Prime` absente, origine sans libellé ou en double, prime manquante, valeur non numérique ou négative, origine du triangle absente. Alerte : prime nulle, ratio a priori supérieur à 3 (pourcentage saisi au lieu d'une fraction), origines en trop.

**Cohérence avec les méthodes.** Ce que `controler` classe bloquant, les méthodes le refusent : un test l'impose sur un triangle à trou.

**En-têtes en double (correction 0.4.1).** pandas renommait en silence une colonne en double (« 24 » devenait « 24.1 »), si bien qu'une période dupliquée passait pour une période nouvelle. Les en-têtes sont désormais lus tels quels : une période en double est refusée par les méthodes de triangle, une colonne en double par les autres lectures.

## 12. Registre des hypothèses d'un dossier : registre

Commande : `registre` (nouveau en 0.4.2). Un dossier (inventaire, étude de provisions, tarification) réunit plusieurs calculs faits à des moments différents. Le registre relit toutes leurs sorties JSON archivées et contrôle que le dossier tient ensemble.

**Entrées.** `--sorties` : fichiers JSON du moteur ou dossiers (tous leurs `.json`, sous-dossiers compris). Les fichiers qui ne sont pas des sorties du moteur sont ignorés et comptés. `--note` écrit la note d'hypothèses en Markdown ; `--titre` la nomme.

**Ce qu'il rend.**

- Les calculs : méthode, statut, version, date, commande de reproduction, empreinte des résultats vérifiée.
- Les données : chaque fichier, son empreinte, les calculs qui l'utilisent et son état actuel (inchangé, modifié depuis, introuvable).
- Les hypothèses en trois groupes : **choix de jugement** (options passées explicitement, à justifier), **valeurs par défaut à confirmer** (retenues par le moteur faute d'option) et **hypothèses de méthode**.

**Incohérences détectées.**

- Bloquant : résultats retouchés (empreinte qui ne correspond plus) ; même fichier de données avec des contenus différents d'un calcul à l'autre.
- Alerte : fichier de données modifié depuis le calcul (relancer avec `rejouer`) ; même hypothèse avec deux valeurs sur les mêmes données (par exemple un facteur de queue de 1 dans un calcul et 1,05 dans un autre : sensibilité voulue ou incohérence) ; plusieurs versions du moteur ; calcul incomplet.
- Info : données introuvables depuis le dossier courant, environnements différents, sortie sans empreinte (antérieure à 0.3.0).

**Limites.** Le registre ne juge pas la pertinence d'un choix : il le rend visible. Les justifications métier (source d'un ratio a priori, raison d'une exclusion) restent à écrire et à signer par l'actuaire dans la note.
