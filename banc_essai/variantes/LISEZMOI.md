# Variantes du banc d'essai

16 tâches (2 par famille) sur **données nouvelles** : triangles publiés perturbés, sinistres et expériences simulés avec une graine fixe, autres âges, taux, seuils et contrats. Elles reprennent les méthodes des 16 tâches de `taches/`, mais leurs réponses ne se trouvent dans aucune publication : Claude ne peut pas les avoir mémorisées.

Statut : **corrigés en attente de validation par Yassine** (champ `statut` de chaque `corrige.yaml`). Ne pas lancer de passage avant.

## D'où viennent les valeurs attendues

| Tâches | Données | Calcul du corrigé |
| --- | --- | --- |
| v-cl-01, v-cl-02 | RAA × 1,37 ; UKMotor × 0,83, bruit lognormal 8 % sur les incréments | `ChainLadder::chainladder` (v-cl-02 : poids sur les 3 dernières diagonales) |
| v-bf-01, v-bf-02 | GenIns × 0,61, primes simulées, a priori = 66 % de la prime | facteurs `chainladder`, **formules BF et Cape Cod écrites en R** |
| v-mack-01, v-mack-02 | ABC × 0,0021 ; MW2008 × 1,9 | `ChainLadder::MackChainLadder(est.sigma = "Mack")` |
| v-odp-01 | MW2014 × 0,8 | `ChainLadder::glmReserve` (dispersion de Pearson) |
| v-boot-01 | GenIns × 0,0012 | `ChainLadder::BootChainLadder`, 20 000 simulations |
| v-gpd-01, v-gpd-02 | 1 900 sinistres simulés (GPD, ξ = 0,55) | `evir::gpd` et `riskmeasures` ; prime de tranche par `integrate` |
| v-cred-01, v-cred-02 | 6 portefeuilles × 10 ans simulés | `actuar::cm` (Bühlmann-Straub sans biais ; hiérarchique itératif) |
| v-vie-01, v-vie-02 | Makeham A = 0,0002, B = 0,00004, c = 1,11 | `lifecontingencies` (axn, Axn, Exn), **équations de prime et de provision écrites en R** |
| v-scr-01, v-scr-02 | SCR de sous-modules inventés | **agrégation écrite en R** à partir du règlement délégué 2015/35 |

Les lignes en gras ne sortent pas directement d'une fonction de package : la formule a été écrite pour l'occasion. La règle « jamais Claude » demande donc que Yassine recalcule ces valeurs dans Excel avant de les valider : **v-bf-01, v-bf-02, v-vie-01, v-vie-02, v-scr-01, v-scr-02**. Les autres sortent des fonctions des packages ; il suffit de vérifier les consignes et les options.

Versions : R 4.5.3, ChainLadder 0.2.21, actuar 3.3.7, evir 1.7.4, lifecontingencies 1.6.3 (conda-forge et sources CRAN).

## Valeurs attendues

| Tâche | Clé | Attendu | Tolérance |
| --- | --- | --- | --- |
| v-bf-01 | `ultime_total` | 33 731 765,46 | ± 0,05 % |
| v-bf-01 | `ibnr_total` | 12 567 497,46 | ± 0,05 % |
| v-bf-01 | `ultime_2022` | 3 170 016,10 | ± 0,05 % |
| v-bf-02 | `ratio_cape_cod` | 0,6438 | ± 0,0005 |
| v-bf-02 | `ultime_total` | 33 422 650,71 | ± 0,05 % |
| v-bf-02 | `ibnr_total` | 12 258 382,71 | ± 0,05 % |
| v-boot-01 | `provision_moyenne` | 22 181,02 | ± 5 % |
| v-boot-01 | `erreur_prediction` | 3 537,58 | ± 5 % |
| v-boot-01 | `quantile_95` | 28 336 | ± 5 % |
| v-cl-01 | `provision_totale` | 71 638,92 | ± 0,05 % |
| v-cl-01 | `ultime_2020` | 23 448,26 | ± 0,05 % |
| v-cl-01 | `facteur_1_2` | 3,1207 | ± 0,0005 |
| v-cl-02 | `provision_totale` | 25 018,29 | ± 0,05 % |
| v-cl-02 | `cdf_1` | 3,1968 | ± 0,0005 |
| v-cl-02 | `facteur_1_2` | 1,9098 | ± 0,0005 |
| v-cred-01 | `prime_collective` | 2 022,29 | ± 0,5 |
| v-cred-01 | `variance_entre` | 41 991,29 | ± 0,05 % |
| v-cred-01 | `variance_intra` | 64 742 018,10 | ± 0,05 % |
| v-cred-01 | `credibilite_3` | 0,9249 | ± 0,0005 |
| v-cred-01 | `prime_portefeuille_3` | 2 208,02 | ± 0,5 |
| v-cred-02 | `prime_collective` | 2 021,36 | ± 0,5 |
| v-cred-02 | `prime_cohorte_A` | 2 185,15 | ± 0,5 |
| v-cred-02 | `prime_cohorte_B` | 1 857,58 | ± 0,5 |
| v-cred-02 | `prime_portefeuille_5` | 1 906,49 | ± 0,5 |
| v-gpd-01 | `n_depassements` | 186 | ± 0 |
| v-gpd-01 | `xi` | 0,5352 | ± 0,005 |
| v-gpd-01 | `quantile_999` | 85,3190 | ± 1,5 % |
| v-gpd-01 | `prime_tranche` | 0,1930 | ± 1,5 % |
| v-gpd-02 | `n_depassements` | 698 | ± 0 |
| v-gpd-02 | `xi` | 0,5463 | ± 0,005 |
| v-gpd-02 | `sigma` | 1,8632 | ± 0,02 |
| v-gpd-02 | `quantile_995` | 34,7631 | ± 1,5 % |
| v-gpd-02 | `quantile_9999` | 301,48 | ± 1,5 % |
| v-mack-01 | `provision_totale` | 10 941,12 | ± 0,05 % |
| v-mack-01 | `erreur_prediction_totale` | 430,59 | ± 0,05 % |
| v-mack-01 | `erreur_prediction_2022` | 333,58 | ± 0,05 % |
| v-mack-02 | `erreur_relative_totale` | 0,0953 | ± 0,0005 |
| v-mack-02 | `erreur_relative_origine_9` | 0,1321 | ± 0,0005 |
| v-mack-02 | `sigma2_1_2` | 22 508,48 | ± 0,05 % |
| v-odp-01 | `dispersion` | 201,88 | ± 0,05 % |
| v-odp-01 | `provision_totale` | 18 827 | ± 1 |
| v-odp-01 | `erreur_prediction_totale` | 2 928,72 | ± 0,05 % |
| v-odp-01 | `erreur_prediction_2022` | 1 623,60 | ± 0,05 % |
| v-scr-01 | `scr_marche` | 103 078,37 | ± 1 |
| v-scr-01 | `scr_vie` | 46 779,96 | ± 1 |
| v-scr-01 | `bscr` | 126 644,18 | ± 1 |
| v-scr-01 | `scr` | 101 894,18 | ± 1 |
| v-scr-02 | `scr_catastrophe_non_vie` | 27 231,23 | ± 1 |
| v-scr-02 | `scr_non_vie` | 61 506,67 | ± 1 |
| v-scr-02 | `bscr` | 97 258,30 | ± 1 |
| v-scr-02 | `scr` | 86 558,30 | ± 1 |
| v-vie-01 | `prime_commerciale` | 2 218,57 | ± 0,005 |
| v-vie-01 | `prime_pure` | 2 075,16 | ± 0,005 |
| v-vie-01 | `provision_nette_10` | 21 193,99 | ± 0,005 |
| v-vie-01 | `provision_brute_10` | 20 639,78 | ± 0,005 |
| v-vie-02 | `annuite_due_55` | 13,2138 | ± 0,0005 |
| v-vie-02 | `prime_pure` | 3 685,35 | ± 0,005 |
| v-vie-02 | `provision_nette_10` | 29 156,60 | ± 0,005 |
| v-vie-02 | `provision_nette_25` | 68 730,87 | ± 0,005 |

Les tolérances suivent celles de `taches/` : relatives de 0,05 % pour les montants (Claude peut arrondir à l'unité), au centime en vie, 1,5 % pour les quantiles GPD et 5 % pour le bootstrap (simulation).

## Essai à blanc du moteur

`python banc_essai/variantes/essai_a_blanc.py` fait répondre le moteur seul aux 16 tâches et note avec `noter.py` : **59/59 valeurs justes**. Écarts les plus grands : quantile GPD à 99,99 % (301,07 contre 301,48, soit 0,14 %, deux optimiseurs de vraisemblance différents) et bootstrap (moins de 0,5 %, graines différentes). Tout le reste est identique à 10⁻⁶ près.

## Régénérer

```bash
cd banc_essai/variantes
Rscript generer_reserving.R taches && Rscript generer_autres.R taches && Rscript generer_scr.R taches
mv taches/corriges_*.json corriges_r/
python construire_taches.py      # consigne.md et corrige.yaml
python essai_a_blanc.py          # contrôle du moteur
```

## Noter un passage

Les réponses se rangent comme pour le premier passage, dans un dossier à part : `python banc_essai/noter.py --reponses banc_essai/variantes/reponses --taches banc_essai/variantes/taches`.
