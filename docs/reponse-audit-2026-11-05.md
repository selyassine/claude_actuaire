# Réponse à l'audit du 2026-11-05

Chaque point de l'audit a été vérifié dans le code de `main` (commit 79f6d1f). Corrections dans la version 0.2.0 (voir `CHANGELOG.md`), tests dans `tests/test_rejets.py` (60 tests).

## Défauts du code

| N° | Point | Constat | Suite |
| --- | --- | --- | --- |
| 1 | Trou dans un triangle incrémental | Confirmé : `nancumsum` comptait le trou comme 0 | Corrigé : refus |
| 2 | Anomalies seulement signalées | Confirmé pour les trous et lignes vides | Corrigé : bloquants. Valeurs négatives et ordre des lignes restent des avertissements (un triangle cumulé peut baisser, cas RAA) |
| 3 | Détection cumulé / incrémental | Déjà présentée comme un indice | Avertissement désormais systématique |
| — | Doublons, infinis | Confirmé | Corrigé : refus |
| 4 | Facteur 1 sans observation | Confirmé | Corrigé : erreur, sauf facteur imposé |
| 5 | Facteurs imposés non contrôlés | Confirmé | Corrigé |
| 6 | Dénominateurs | Confirmé | Corrigé |
| 7 | Facteur de queue | Confirmé | Corrigé |
| 8 | Entrées BF et Cape Cod | Confirmé | Corrigé |
| 9 | Poids négatifs en crédibilité | Confirmé : contrôle impossible à déclencher | Corrigé |
| 10 | Infinis en crédibilité | Confirmé | Corrigé |
| 11 | Singularité Hachemeister | Rang des matrices individuelles déjà contrôlé | Conditionnement : non traité |
| 12 | Convergence itérative | Déjà en place : nombre d'itérations rendu, erreur si non convergé | Inchangé |
| 13 | NaN et infinis dans le SCR | Confirmé | Corrigé, à tous les niveaux |
| 14 | Contrepartie négative | Confirmé | Corrigé |
| 15 | Risque opérationnel, ajustements | Confirmé | Corrigé (finitude, signe) |
| 16 | Conformité réglementaire | Limite connue | Relecture par un actuaire externe : à décider |
| 17 | Mack sur petits triangles | Confirmé, et l'option `precedent` était ignorée sous 4 × 4 | Corrigé |
| 18 | ODP dégénéré | Confirmé | Corrigé (taille, facteurs, valeurs ajustées). Conditionnement de X'WX : non traité |
| 19 | Pearson ou déviance | Défaut Pearson silencieux (cause d'erreur en condition B du premier passage) | Avertissement si non précisé |
| 20 | Bootstrap | Confirmé (dispersion nulle, pseudo-facteurs) | Corrigé |
| 21 | Un seul point de départ GPD | Confirmé | Corrigé : 4 départs, meilleur optimum |
| 22 | Diagnostic de convergence | Confirmé | Corrigé : vraisemblance, itérations, statut, écart entre départs |
| 23 | Choix du seuil | Partiel | ξ et σ par seuil ajoutés ; graphiques et QQ-plot non traités |
| 24 | Données de pertes | Confirmé pour les infinis | Corrigé ; moins de 50 dépassements déjà signalé |
| 25 | Paramètres Makeham | Confirmé | Corrigé |
| 26 | Tables de mortalité | Confirmé (trous, doublons) | Corrigé ; la fermeture de table était déjà une hypothèse affichée |
| 27 | Paramètres du contrat | Confirmé | Corrigé |
| 28 | Dénominateur de la prime commerciale | Garde ajoutée. Il reste positif dès que les taux de frais sont sous 100 %, désormais imposé | Corrigé |
| 29 | NaN rendus null sans le dire | Confirmé | Corrigé : `statut: incomplet` et avertissement nommé |
| 30 | Exceptions de la CLI | Confirmé | Corrigé : toute erreur sort en JSON, sans résultat partiel |
| 4.4 | Notation sans liste d'essais attendus | Confirmé | Corrigé : essai manquant compté faux |

## Points qui ne relèvent pas du code, à décider

- Produit logiciel (API, base d'audit, interface, utilisateurs) : c'est un changement d'objectif, pas une correction.
- Paquet Python (`pyproject.toml`, versions épinglées), CI avec lint, typage et couverture.
- Jeu de test privé, campagne avec répétitions, rapports séparés par passage.
- Statuts de validation détaillés (référence, logiciel, Excel, interne, externe) et revue par un actuaire externe.

L'audit reconnaît lui-même que la validation Excel des 6 corrigés est un contrôle croisé et non une validation indépendante : c'est exact, et c'est écrit ainsi dans `banc_essai/variantes/LISEZMOI.md`.
