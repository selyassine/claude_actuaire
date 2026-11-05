# Historique des versions

## 0.2.0 (2026-11-05) : fiabilité numérique

Le moteur refuse désormais les entrées invalides et les cas dégénérés au lieu de rendre un chiffre faux. Les résultats publiés et les 16 variantes sont reproduits à l'identique (59/59).

- Triangles : un trou avant la dernière valeur observée, une ligne vide, une valeur infinie, une origine ou une période en double arrêtent le calcul (avant : le trou était compté comme 0). Le type deviné automatiquement est toujours signalé.
- Facteurs de développement : un facteur sans observation déclenche une erreur au lieu de valoir 1, sauf s'il est imposé. Les facteurs imposés et le facteur de queue doivent être finis et strictement positifs. Un dénominateur nul ou négatif est refusé.
- BF et Cape Cod : ultimes a priori et primes contrôlés (dimensions, finitude, signe).
- Crédibilité : les poids négatifs sont refusés (le contrôle précédent ne pouvait jamais se déclencher), de même que les ratios et poids infinis.
- SCR : chaque montant doit être un nombre fini, positif (négatif pour les capacités d'absorption), y compris en contrepartie, catastrophe, risque opérationnel et ajustements. NaN et infini sont refusés.
- Mack : taille minimale 4 × 4 (3 × 3 avec `--sigma-dernier precedent`, qui était ignoré sous 4 × 4). Aucun paramètre de variance non défini n'atteint le résultat.
- ODP et bootstrap : taille minimale 3 × 3, facteurs définis, valeurs ajustées strictement positives, dispersion non nulle, nombre de simulations et niveaux de quantile contrôlés. Avertissement si la convention de dispersion n'est pas précisée.
- GPD : quatre points de départ pour la vraisemblance, meilleur optimum retenu, diagnostic d'optimisation dans le résultat ; stabilité de ξ et σ par seuil dans `--diagnostic-seuils` ; pertes infinies refusées.
- Vie : paramètres de Makeham (B > 0, c > 1, A + B ≥ 0), tables (âges consécutifs, sans doublon, q dans [0, 1]), taux, et contrat (âge, capital, durées, frais) contrôlés.
- Sortie : nouveau champ `statut` (`ok`, `avertissements`, `incomplet`) ; une valeur NaN ou infinie dans les résultats est signalée nommément. Toute erreur, même inattendue, sort en JSON `{"statut": "erreur"}` sans résultat partiel.
- Banc d'essai : `noter.py` construit la liste complète des essais attendus et compte un essai manquant comme faux (options `--conditions`, `--seulement`, `--repetitions`).
- SKILL.md : règle 5, un refus du moteur n'est pas contourné par un calcul à la main.
- Correction : `tarif-vie --help` plantait.

## 0.1.0 (2026-11-03)

Première version : provisionnement, Mack, ODP, bootstrap, vie, GPD, crédibilité, agrégation SCR, testés sur des résultats publiés.
