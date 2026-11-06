# Assurance vie

Fichier de référence du skill `calcul-actuariel` pour les commandes `survie` et `tarif-vie`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `survie` | q, espérance de vie, annuités dues, assurances décès, mixte, capital différé | propriétés testées |
| `tarif-vie` | Primes pure et commerciale, provisions nette, brute, de frais et Zillmer FPT | testé : note MLC (Dickson, Hardy, Waters) SN2.3-SN2.4, au centime |

Modèle de survie : `--modele sssm` (défaut, Standard Select Survival Model d'AMLCR), `susm` (ultime), `makeham --A --B --c`, ou `table --table qx.csv` (colonnes `Age`, `qx`). Sélection libre avec `--selection-facteur k --selection-duree d`. Temps discret annuel : capital décès en fin d'année, primes et annuités d'avance. Contrats : `vie-entiere`, `temporaire --duree n`, `mixte --duree n`, avec `--duree-primes`. Les frais initiaux sont payés à la souscription, les frais de renouvellement à chaque échéance suivante. Les provisions sont prospectives, juste avant la prime de l'année t.

Pour la vie tunisienne, utilise `--modele td99` (contrats en cas de décès ; l'arrêté l'appelle TM99) ou `--modele tv99` (contrats en cas de survie), avec `--qx-source lx` (défaut) ou `publie`. Voir aussi `references/tunisie.md`.
