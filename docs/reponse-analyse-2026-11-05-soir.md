# Réponse à l'analyse du 2026-11-05 (soir)

Chaque point a été vérifié dans le code avant correction. « Fait » renvoie à la version 0.3.0 (voir `CHANGELOG.md`).

## Problèmes techniques cités

| # | Point | Vérifié | Suite |
| --- | --- | --- | --- |
| 1 | `cmd_triangle` n'appelle pas `verifier_forme()` | confirmé | Fait : mêmes contrôles bloquants que les méthodes. Tests : trou, ligne vide. |
| 2 | `_non_finis()` exempte tous les champs `_pct` | confirmé | Fait : plus aucune exemption ; les ratios non définis attendus sont rendus `null` par la méthode. Trois des cinq champs `_pct` pouvaient produire un NaN réel. |
| 3 | Dépendances non verrouillées | confirmé | Fait : bornes (`requirements.txt`), versions exactes (`requirements-lock.txt`), audit `pip-audit` en CI. L'audit a trouvé une vulnérabilité dans pytest 8.4.2 : version 9.0.3 retenue. |
| 4 | `plugin.json` en 0.1.0 | confirmé | Fait : 0.3.0 partout, test qui impose la synchronisation. |
| 5 | Contrôles métier transversaux | confirmé (doublons de primes écrasés en silence) | Fait : doublons, origines manquantes ou en trop, colonne Prime, alerte d'unité, libellés Excel, cohortes contradictoires, périodes vides. |

## Défauts supplémentaires trouvés en sondant le moteur

| Défaut | Avant | Après |
| --- | --- | --- |
| Table de mortalité avec facteur de sélection > 1 | q = 1,8, espérance de vie −0,52, statut `ok` | refus explicite |
| Âge avant le début de la table | décès immédiat supposé, sans alerte | refus explicite |
| Âge de départ au-delà de la table | résultats à 0, statut `ok` | refus explicite |
| Texte dans le fichier de sinistres GPD | échec de lecture, alors que la doc promettait de l'ignorer | ignoré et compté dans un avertissement |
| `zip()` non stricts (14) | troncature silencieuse possible | tous stricts |

## Recommandations

| Recommandation | Suite |
| --- | --- |
| Diagnostics GPD (intervalles, ajustement, sensibilité au seuil) | Fait : intervalles de Wald et profilés, KS, Anderson-Darling avec p-valeur par bootstrap paramétrique ; la sensibilité au seuil existait (`--diagnostic-seuils`). Vérifiés indépendamment avec scipy. |
| Auditabilité complète (versions, dépendances, paramètres, date) | Fait : versions des bibliothèques, commande exacte, empreinte des résultats, commande `rejouer`. L'identité du validateur humain reste hors du moteur (voir guide, § 9). |
| Ruff, couverture, mypy, Bandit, pip-audit, test du zip | Fait : ruff, couverture (seuil 90 %, 91 % atteint), pip-audit, installation réelle du zip. Non fait : mypy (le code n'est pas annoté de bout en bout ; à ajouter module par module) et Bandit (le moteur n'exécute aucune commande, n'ouvre aucun réseau et ne désérialise que du JSON et du CSV ; peu de valeur aujourd'hui). |
| Publication de versions | Fait : un tag `vX.Y.Z` publie la version GitHub avec l'archive et les notes du CHANGELOG. |
| Documentation par méthode | Fait : `docs/guide-des-methodes.md`, inclus dans le skill. |
| Démonstration avant/après | Fait : README, cas réel du banc d'essai (Mack, covariance). |
| Description et topics GitHub | À faire dans les réglages du dépôt sur GitHub : description et topics `actuarial-science`, `insurance`, `python`, `claude`, `claude-skills`, `reserving`, `solvency-ii`, `risk-management`. |
| SCR : dire clairement qu'aucun choc n'est appliqué | Fait : guide § 8 et README, section Limites. |
| Sécurité des données | Fait : section Confidentialité du README. |

## Ce qui ne peut pas être fait dans le dépôt

- **Validation par un actuaire externe.** C'est la condition principale pour parler d'un outil de production. Elle demande une personne indépendante ; le guide des méthodes et les fiches de `tests/references/` sont prêts pour cette revue.
- **Benchmark de 100 à 200 tâches avec répétitions et plusieurs versions de Claude.** Faisable, mais c'est un chantier en soi (plusieurs centaines de sessions). Le protocole et la notation existent déjà (`banc_essai/`).
- **Gestion des utilisateurs, circuit de validation, monitoring.** Ce sont des fonctions d'une plateforme, pas d'un skill. Elles n'ont de sens que si le projet devient un service.
