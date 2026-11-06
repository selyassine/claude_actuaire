# Réglementation tunisienne

Fichier de référence du skill `calcul-actuariel` pour les commandes `marge-solvabilite-tn` et `provisions-tn` (tables TD99 / TV99 : voir `references/vie.md`). Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `marge-solvabilite-tn` | Marge de solvabilité minimale du Code des assurances tunisien (art. 58 bis : non-vie, vie, mixte) et taux de couverture (art. 58) | testé : cas construits recalculés en R, fiches validées par Yassine |
| `provisions-tn` | Règles de provisions non-vie de l'arrêté tunisien du 27/02/2001 : PPNA prorata temporis, PRC, minimum de 5 % des frais de gestion des sinistres, auto matériels (la plus haute de trois évaluations), équilibrage, égalisation grêle, rentes + 5 % | testé : cas construit recalculé en R, fiche validée par Yassine |

Pour `marge-solvabilite-tn`, le fichier JSON donne les primes, les règlements de chaque exercice (3, ou 7 pour l'assurance crédit), les PSAP de début et de fin, les recours encaissés, la charge nette, et pour la vie les PM et capitaux brut et net (voir le guide des méthodes, § 8 bis). Ne complète pas un montant manquant : demande-le. Les primes sont hors taxes et nettes d'annulations : vérifie-le avec l'utilisateur. Pour la vie tunisienne, utilise `--modele td99` (contrats en cas de décès) ou `--modele tv99` (contrats en cas de survie) : voir `references/vie.md`.

Pour `provisions-tn`, chaque bloc est facultatif (voir le guide des méthodes, § 8 ter). Pour les sinistres matériels automobile, lance d'abord `chain-ladder` sur le triangle des règlements, enregistre la sortie, puis passe-la avec `--cadences`. Rapporte les trois évaluations et celle retenue, et les interprétations rendues en hypothèses.

Pour organiser un inventaire tunisien dans Claude Code, `references/modele-CLAUDE-tunisie.md` donne un modèle de CLAUDE.md. Les formules et interprétations sont détaillées dans `references/guide-des-methodes.md` (§ 8 bis et 8 ter).

Référence publiée reproduite : la marge constituée de STAR (rapport annuel 2025, 378 525 kDT) est retrouvée en excluant le fonds social des réserves (fiche `ra-star-2025-marge-constituee`). Le fonds social, réserve à affectation sociale, n'est pas un élément de l'art. 58.
