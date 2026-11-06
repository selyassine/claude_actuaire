# Famille « pièges » du banc d'essai

Neuf tâches où le calcul naïf donne une mauvaise réponse. Cinq d'entre elles sont tunisiennes. Elles mesurent si Claude détecte la difficulté, avec et sans le skill, et non sa précision de calcul.

Statut : **corrigés en attente de validation par Yassine** (champ `statut` de chaque `corrige.yaml`).

## Les pièges

| Tâche | Piège | Bonne réponse |
| --- | --- | --- |
| p-tn-marge-2ex | Règlements de 2 exercices au lieu de 3 (art. 58 bis a) | `minimum_reglementaire: null`, avec demande du 3e exercice |
| p-tn-marge-ttc | Primes données TTC, taxes indiquées | 5 200 : base primes sur 52 000 HT, plancher de rétention 50 %. Sur les primes TTC on obtiendrait 6 120 |
| p-tn-marge-recours | Recours encaissés à déduire de la charge | 4 458,33. Sans la déduction on obtiendrait 4 958,33. Le plancher de 50 % rend l'oubli visible |
| p-tn-rente-tv99 | Rente viagère d'un homme : table TV99 (contrats en cas de vie), pas TD99 | 14 755,17 pour 1 000 DT. Avec TD99 on obtiendrait 13 533,52 |
| p-tn-taux-5 | Taux technique de 5 %, au-delà du plafond de 4 % (art. 5 b) | `taux_reglementaire_respecte: false` |
| p-cl-trou | Cellule vide au milieu du triangle | `provision_totale: null`, avec demande du traitement de la cellule |
| p-cl-incremental | Triangle incrémental décrit comme « montant payé au cours de la période » | 71 638,92 (corrigé validé de v-cl-01) |
| p-xl-annees | Nombre d'années d'observation absent pour une prime annuelle | `prime_pure_annuelle: null` |
| p-scr-scenario | Scénario de taux non précisé (art. 164, paramètre A) | `scr_marche: null` |

## D'où viennent les valeurs attendues

- **Montants de marge :** `corriges.R`, calcul R indépendant du moteur. La sortie est dans `corriges.sortie.txt`.
- **p-tn-rente-tv99 :** la fiche validée `r-tunisie-tv99-annuite-60` (ä₆₀ = 14,7551743042141), multipliée par 1 000.
- **p-cl-incremental :** le corrigé validé de la variante v-cl-01. Le triangle est celui de v-cl-01, converti en incréments.
- **Valeurs `null` et booléennes :** elles découlent du texte (Code des assurances, arrêté de 2001, règlement délégué 2015/35) ou de l'absence d'une donnée.

## Notation

`noter.py` accepte deux nouveaux types de valeur attendue :
- `null` : la clé doit être présente et valoir `null`. Une clé absente ou un chiffre est faux.
- un booléen : la réponse doit être exactement ce booléen.

```bash
python banc_essai/noter.py --reponses banc_essai/pieges/reponses --taches banc_essai/pieges/taches --conditions A,B,C
```

## Essai à blanc avec le moteur (0.5.3 et 0.5.4)

Les 9 tâches ont été passées dans le moteur, et celui-ci a le comportement attendu sur chacune :
- **Il refuse en expliquant la donnée manquante :** p-cl-trou, p-xl-annees (`--annees` obligatoire), p-scr-scenario et p-tn-marge-2ex.
- **Il calcule les valeurs attendues :** 5 200, 4 458,33, 14,7552 par dinar de rente et 71 638,92 avec `--type incremental`.
- **Il avertit :** au-delà de 4 % pour p-tn-taux-5.

Le skill ne détecte pas seul deux pièges : les primes TTC et le triangle incrémental. Claude doit les repérer dans la consigne.

Construction : `python banc_essai/pieges/construire_taches.py` (il relit les données de `variantes/taches/`).
