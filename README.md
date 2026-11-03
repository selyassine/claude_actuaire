# claude_actuaire

Moteur de calcul actuariel pour Claude, livré comme skill. Les calculs sont faits par des scripts Python testés contre des résultats publiés, au lieu d'être faits « de tête » par le modèle.

## Principe

- Chaque méthode est validée sur au moins une publication (Mack 1993, England et Verrall 2002, McNeil 1997, AMLCR…). Les valeurs attendues sont recopiées des publications, jamais produites par Claude, puis contrôlées par un actuaire.
- Chaque calcul rend une sortie traçable : entrées (avec empreinte SHA-256), options, hypothèses, résultats, avertissements.
- Un banc d'essai compare Claude sans skill et avec skill ; ses règles sont fixées à l'avance dans [`banc_essai/REGLES.md`](banc_essai/REGLES.md).

## État

| Méthode | Statut |
| --- | --- |
| Lecture et contrôle de triangles | disponible |
| Chain Ladder, BF, Cape Cod | disponible (Friedland 2010, Mack 1993) |
| Mack, ODP analytique, bootstrap ODP | disponible (Mack 1993, England et Verrall 2002) |
| Survie, primes et provisions vie (SSSM d'AMLCR, Zillmer FPT) | disponible (note MLC SN2.3-SN2.4, validée par Yassine) |
| GPD (valeurs extrêmes) | disponible (McNeil 1997, données danoises, validé par Yassine) |
| Crédibilité (Bühlmann, Bühlmann-Straub, hiérarchique, Hachemeister) | disponible (vignette actuar, données de Hachemeister, validé par Yassine) |
| Agrégation SCR formule standard | testé, en attente de validation (SFCR CCR 2024 et IPBP 2016) |

## Installation

**Sur claude.ai** : télécharger `calcul-actuariel.zip` (onglet Actions du dépôt, ou `python outils/construire_zip.py`), puis le téléverser dans les paramètres de Claude, rubrique des skills. L'exécution de code doit être activée.

**Dans Claude Code** :

```
/plugin marketplace add selyassine/claude_actuaire
/plugin install claude-actuaire@claude-actuaire
```

## Développement

```
pip install -r requirements-dev.txt
python -m pytest -v -rxs
```

Pour ajouter une valeur de référence : copier `tests/references/_modele.yaml`, remplir la source exacte (ouvrage, page, tableau), laisser `statut: en_attente` jusqu'au contrôle par un actuaire.

## Organisation

```
.claude-plugin/              manifeste du plugin Claude Code
skills/calcul-actuariel/     le skill : SKILL.md, scripts/, references/
tests/                       tests, données et fiches de référence publiées
banc_essai/                  règles, tâches et notation du banc d'essai
outils/                      construction de l'archive .zip
```
