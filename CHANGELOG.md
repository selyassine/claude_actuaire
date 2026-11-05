# Historique des versions

## 0.4.2 (2026-11-05) : registre des hypothèses d'un dossier

Nouvelle commande `registre` :

- Relit les sorties JSON archivées d'un dossier (fichiers ou répertoires) et rend les calculs, les données utilisées avec leur empreinte, et les hypothèses classées en choix de jugement, valeurs par défaut à confirmer et hypothèses de méthode.
- Détecte les incohérences du dossier : résultats retouchés, même fichier de données avec des contenus différents, données modifiées depuis le calcul, même hypothèse avec deux valeurs sur les mêmes données, versions du moteur différentes, calculs incomplets.
- `--note` écrit la note d'hypothèses en Markdown (incohérences, calculs et commandes de reproduction, données, hypothèses, avertissements).

Tests : 342.

## 0.4.1 (2026-11-05) : contrôle qualité des données, modèle de CLAUDE.md

Nouvelle commande `controler` :

- Audit d'un triangle, d'un fichier de sinistres ou d'un fichier de primes, sans calcul. Chaque anomalie a une gravité (bloquant, alerte, info), un lieu et un message ; rien n'est corrigé.
- Triangle : trous, lignes vides, doublons, textes, infinis, baisses du cumulé, cumulé nul puis positif, facteurs individuels atypiques (médiane et MAD des log-facteurs, avec l'option `--exclure` à utiliser si l'actuaire le décide).
- Sinistres : négatifs, nuls, textes, montants répétés, maximum isolé. Primes : colonne absente, doublons, valeurs manquantes ou négatives, ratio saisi en pourcentage, origines manquantes ou en trop par rapport au triangle.

Défaut corrigé :

- Une période de développement en double dans l'en-tête d'un triangle était renommée en silence par pandas (« 2 » devenait « 2.1 ») et le calcul passait. Les en-têtes sont désormais lus tels quels : période en double refusée par les méthodes de triangle, colonne en double refusée ailleurs.

Documentation et publication :

- `docs/modele-CLAUDE.md` (inclus dans l'archive du skill) : modèle de CLAUDE.md pour un projet actuariel avec le skill.
- La publication sur tag accepte une version déjà créée depuis l'interface GitHub : elle y joint l'archive et les notes.
- Fiches de la tranche XL validées par Yassine.

Tests : 330.

## 0.4.0 (2026-11-05) : tranche de réassurance XL et validation d'un modèle externe

Deux usages tirés du guide « Claude Code for Actuaries » (Nzati et Schraub, 2026), cas 15 et 30, réalisés selon les règles du moteur : valeurs attendues calculées sans le moteur, refus explicites, sortie traçable.

Nouvelle commande `tranche-xl` :

- Tranche XL par risque sur un an : fréquence de Poisson des dépassements du seuil, sévérité GPD (ajustée ou imposée avec `--parametres`).
- Prime pure et écart type exacts ; loi de la charge annuelle par discrétisation (méthode des arrondis) et récurrence de Panjer ; VaR et CTE ; probabilité d'une année sans charge.
- Franchise et limite annuelles (`--franchise-annuelle`, `--limite-annuelle`).
- Burning cost historique et rapport prime du modèle / burning cost.
- Alertes : peu de dépassements, peu de sinistres historiques dans la tranche, écart au burning cost, discrétisation trop grossière, tranche épuisée par la plupart des sinistres. Refus : priorité sous le seuil, années ou pas invalides, paramètres impossibles, fréquence hors de portée de Panjer.
- Validation : trois fiches calculées indépendamment en R (evir et actuar ; script et sortie dans `tests/references/r/`), validées par Yassine le 2026-11-05. Accord à 1e-9 près à paramètres égaux.

Nouvelle commande `comparer` :

- Confronte les résultats d'un modèle externe (CSV ou Excel `chemin;valeur`) à une sortie archivée du moteur, dont l'empreinte est vérifiée.
- Classe chaque ligne : conforme, arrondi (écart couvert par la dernière décimale écrite), écart, chemin absent, valeur invalide ; conclusion et écart relatif maximal.
- Repère un facteur commun aux écarts (unités, signe, hypothèse commune). `--lister` donne les chemins comparables.

Tests : 314 (259 en 0.3.0).

## 0.3.0 (2026-11-05) : contrôles métier, reproductibilité, industrialisation

Réponse à l'analyse du 2026-11-05 au soir. Les résultats publiés et les 16 variantes restent reproduits à l'identique (59/59).

Défauts corrigés :

- `triangle` : applique désormais les mêmes contrôles bloquants que les méthodes (trou, ligne vide, valeur infinie, doublon) au lieu de résumer un triangle invalide.
- Sortie : plus aucun champ n'échappe au contrôle des valeurs non finies (les champs `_pct` étaient exemptés). Les erreurs relatives d'une provision nulle sont rendues `null` explicitement par la méthode.
- Vie : une sélection qui rendait q > 1 sur une table donnait q = 1,8 et une espérance de vie négative avec le statut `ok` ; elle est refusée. Un âge avant le début d'une table supposait un décès immédiat ; il est refusé. Un âge de départ au-delà de la table, `--n 0`, `--depuis` négatif et une liste `--durees` mal formée sont refusés.
- GPD : un texte dans le fichier de sinistres faisait échouer la lecture ; il est ignoré et compté dans un avertissement, comme annoncé.
- Versions synchronisées (moteur, plugin, CHANGELOG), avec un test qui l'impose.

Contrôles métier :

- Fichier de primes : colonne `Prime` obligatoire, origine en double refusée, origine du triangle absente refusée, origines en trop signalées.
- Alerte d'unité si le ratio médian ultime Chain Ladder / prime sort de [0,02 ; 50] (triangle et primes dans des unités différentes).
- Libellés lus dans Excel (`2020.0`) ramenés à `2020`. Origine ou entité sans libellé refusée.
- Options `--exclure` et `--facteurs-imposes` mal formées, ou facteur imposé deux fois : message explicite. Valeur non numérique : message explicite.
- Crédibilité : période vide refusée, entité rattachée à deux cohortes refusée.
- Triangle d'une seule période refusé.
- Tous les `zip()` du moteur sont stricts : deux listes de longueurs différentes arrêtent le calcul au lieu d'être tronquées.

Valeurs extrêmes :

- Intervalles de confiance à 95 % de ξ et σ (Wald) et de ξ par vraisemblance profilée (Coles 2001).
- Statistiques de Kolmogorov-Smirnov et d'Anderson-Darling ; p-valeur d'Anderson-Darling par bootstrap paramétrique (`--test-ajustement N`, `--graine`).

Reproductibilité et audit :

- Chaque sortie contient les versions de Python, numpy, scipy et pandas, la commande exacte (`reproduction`) et l'empreinte SHA-256 des résultats.
- Nouvelle commande `rejouer` : vérifie que les résultats archivés n'ont pas été retouchés et que les fichiers d'entrée n'ont pas changé, refait le calcul et liste les écarts.

Industrialisation :

- `requirements.txt` (bornes des versions supportées), `requirements-dev.txt`, `requirements-lock.txt` (versions exactes de la CI).
- CI : ruff, couverture avec seuil de 90 % (91 % atteint), tests sous Python 3.10 et 3.12 (versions verrouillées) et 3.13 (dernières versions autorisées), `pip-audit`, banc d'essai à blanc, test d'installation réelle de l'archive, publication automatique d'une version GitHub sur tag `vX.Y.Z`.
- 259 tests (195 en 0.2.0).

Documentation :

- `docs/guide-des-methodes.md` : formules, conventions, domaine de validité, refus, limites et validation de chaque méthode ; inclus dans l'archive du skill.
- README : exemple réel avant/après tiré du banc d'essai, confidentialité des données, limites.

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
