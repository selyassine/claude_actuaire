# Rapport du passage sur les 16 variantes

Passage du 2026-11-05, 48 sessions sur claude.ai (16 variantes × 3 conditions, un passage par variante et par condition), selon `REGLES.md` et son amendement du 2026-11-05, inscrit avant la première session. Les corrigés viennent de R (ChainLadder, actuar, evir, lifecontingencies) ou d'un calcul explicite, recalculés dans Excel et validés par Yassine avant le passage.

## Résultat

Le skill passe les deux seuils sur la condition C, mais pas l'écart avec B.

| Seuil (REGLES.md) | Visé | Obtenu | Atteint |
| --- | --- | --- | --- |
| C, ensemble | ≥ 95 % | 100 % (59/59) | oui |
| C, chaque famille | ≥ 90 % | 100 % dans les 8 familles | oui |
| Écart C − B | ≥ 30 points | + 6,8 points | non |

Comme au premier passage, la condition B est forte : quand Claude peut écrire son propre Python, il trouve 93,2 % des valeurs. Le skill corrige les 4 erreurs restantes de B (Mack et SCR) et toutes celles de A.

## Scores par famille

| Famille | A (sans code) | B (code, sans skill) | C (skill 0.2.0) |
| --- | --- | --- | --- |
| Chain Ladder | 6/6 | 6/6 | 6/6 |
| BF et Cape Cod | 6/6 | 6/6 | 6/6 |
| Mack | 4/6 | 4/6 | **6/6** |
| Bootstrap et ODP | 7/7 | 7/7 | 7/7 |
| Vie | 4/8 | 8/8 | 8/8 |
| GPD | 5/9 | 9/9 | 9/9 |
| Crédibilité | 9/9 | 9/9 | 9/9 |
| SCR | 6/8 | 6/8 | **8/8** |
| **Ensemble** | **47/59 (79,7 %)** | **55/59 (93,2 %)** | **59/59 (100 %)** |

Commande : `python banc_essai/noter.py --reponses banc_essai/variantes/reponses --taches banc_essai/variantes/taches --conditions A,B,C`. Aucun essai manquant.

## Les erreurs, une par une

### Condition C

Aucune.

### Condition B (4 valeurs fausses)

1. **v-mack-01, erreur de prédiction totale** : 468,72 au lieu de 430,59. Les erreurs par origine sont justes (dont 333,58 pour 2022). Le terme de covariance entre années d'origine est mal calculé.
2. **v-mack-02, erreur relative totale** : 0,199 au lieu de 0,0953. Même cause : Claude écrit que l'erreur totale dépasse celle de chaque origine à cause des covariances, ce qui est faux ici. Les σ² et l'erreur de l'origine 9 sont justes.
3. et 4. **v-scr-01, BSCR et SCR** : 126 636,38 au lieu de 126 644,18 (écart de 7,8). Claude n'a pas utilisé l'exécution de code pour cette tâche et a fait l'agrégation à la main. Les SCR de marché et de vie sont justes.

### Condition A (12 valeurs fausses)

- **GPD (4)** : sur v-gpd-02, 760 dépassements au lieu de 698, donc ξ, σ et le quantile à 99,99 % faux. Sans code, Claude ne peut pas compter 1 900 lignes.
- **Vie (4)** : arrondis au centime faux sur v-vie-01 (prime commerciale, provision nette) et v-vie-02 (provision nette à 10 ans), et provision nette à 25 ans fausse de 0,28.
- **Mack (2)** : sur v-mack-02, erreurs relatives totale et de l'origine 9 approchées.
- **SCR (2)** : sur v-scr-02, BSCR et SCR faux de 124,2 (erreur d'agrégation).

## Conditions du passage

- **Modèle** : le même modèle Claude et le même effort (« Moyen ») pour les 48 sessions.
- **Condition A** : conversations incognito, skill `calcul-actuariel` désactivé, aucune exécution de code. Aucun outil utilisé dans les 16 sessions.
- **Condition B** : conversations normales, exécution de code active, `calcul-actuariel` désactivé. Claude a écrit du Python dans 14 sessions sur 16. Les deux tâches SCR ont été faites sans code.
- **Condition C** : conversations normales, `calcul-actuariel` activé en version 0.2.0. Yassine a réinstallé le zip 0.2.0 pendant le passage B. Avant la première session C, j'ai vérifié que le skill installé était bien la nouvelle version (le `SKILL.md` installé décrit le champ `statut`, ajouté en 0.2.0). Le skill a été chargé dans 15 sessions sur 16. Sur v-bf-02 (Cape Cod), Claude a codé le calcul lui-même sans lire le skill, et a trouvé les bonnes valeurs.
- **Contrôle automatique** : avant chaque envoi, le script de lancement vérifiait le mode incognito (A seulement) et l'état du skill (désactivé en A et B, activé en C). Aucune session n'a été refusée par ce contrôle.
- **Recherche web** : activée dans les trois conditions (réglage du compte), utilisée dans aucune session.
- **Réglages restaurés** : `calcul-actuariel` est de nouveau activé à la fin du passage, comme avant.
- **Réponses** : `reponses/<condition>/<variante>/1.md` contient les outils utilisés et le bloc `resultats` copié tel quel. Les 32 conversations B et C sont dans l'historique claude.ai de Yassine. Les conversations A, incognito, n'y sont pas.

## Ce que ce passage montre

- **Sur des jeux de données que le modèle n'a jamais vus, le skill donne 100 %.** C'est le résultat que le premier passage n'avait pas atteint (94,5 %), en partie à cause d'une version périmée du skill sur claude.ai.
- **Le gain du skill se voit là où le calcul est subtil** : la covariance de Mack et l'agrégation SCR. Sans skill, Claude y fait des erreurs même avec du code. Ces erreurs sont plausibles et difficiles à repérer à la lecture.
- **Sur les méthodes simples** (Chain Ladder, BF, Cape Cod, crédibilité), Claude avec du code est déjà juste. Le skill n'apporte rien de mesurable sur ces familles.
- **L'écart de 30 points avec B ne sera pas atteint** sur des tâches standard de ce type, puisque B est déjà au-dessus de 90 %. Le premier rapport proposait déjà de revoir ce seuil. Ce passage le confirme : la valeur du skill tient à la suppression des dernières erreurs, pas à un grand écart moyen.

## Limites

- Un seul passage par variante et par condition. Un écart de 4 valeurs sur 59 entre B et C peut varier d'un passage à l'autre.
- Les variantes ont été construites par Claude à partir de méthodes publiées. Les corrigés viennent de logiciels indépendants et ont été validés par Yassine, mais les consignes restent proches du premier banc d'essai.
