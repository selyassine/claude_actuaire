# claude_actuaire

Moteur de calcul actuariel pour Claude, livré comme skill. Les calculs sont faits par des scripts Python testés contre des résultats publiés, au lieu d'être faits « de tête » par le modèle.

## Pourquoi : un exemple réel

Banc d'essai du 2026-11-05, variante `v-mack-01` (triangle inédit, corrigé calculé par le paquet R `ChainLadder` et validé) : erreur de prédiction totale de Mack.

| | Réponse | Juste ? |
| --- | --- | --- |
| Claude avec Python, sans le skill | 468,72 | non : covariance entre années d'origine mal calculée |
| Claude avec le skill | 430,59 | oui (corrigé R : 430,5906) |

Les erreurs par année d'origine étaient justes dans les deux cas. L'erreur ne se voit pas à la lecture : c'est exactement le type d'erreur plausible que le moteur supprime. Sur les 16 variantes du banc d'essai, le skill obtient 59/59 valeurs justes, contre 55/59 pour Claude avec Python et 47/59 sans code ([rapport](banc_essai/variantes/RAPPORT.md)).

## Principe

- Chaque méthode est validée sur au moins une publication (Mack 1993, England et Verrall 2002, McNeil 1997, AMLCR…). Les valeurs attendues sont recopiées des publications, jamais produites par Claude, puis contrôlées par un actuaire.
- Chaque calcul rend une sortie traçable : entrées (avec empreinte SHA-256), options, hypothèses, résultats, avertissements, versions des bibliothèques, commande exacte et empreinte des résultats. `cli.py rejouer` refait un calcul archivé et prouve qu'il donne les mêmes chiffres sur les mêmes données.
- Le moteur sert aussi de deuxième implémentation pour valider un modèle existant : `cli.py comparer` confronte les résultats d'un modèle externe (Excel, logiciel interne) à une sortie du moteur et classe chaque écart.
- Le moteur refuse de calculer quand les données ou les hypothèses ne le permettent pas (triangle troué, facteur non estimable, table de mortalité incomplète, unité incohérente…) au lieu de rendre un chiffre faux.
- Le [guide des méthodes](docs/guide-des-methodes.md) donne pour chaque méthode les formules, conventions, domaine de validité, refus, limites et la publication qui la valide.
- Un banc d'essai compare Claude sans skill et avec skill ; ses règles sont fixées à l'avance dans [`banc_essai/REGLES.md`](banc_essai/REGLES.md).

## État

| Méthode | Statut |
| --- | --- |
| Lecture et contrôle de triangles | disponible |
| Chain Ladder, BF, Cape Cod | disponible (Friedland 2010, Mack 1993) |
| Mack, ODP analytique, bootstrap ODP | disponible (Mack 1993, England et Verrall 2002) |
| Survie, primes et provisions vie (SSSM d'AMLCR, Zillmer FPT) | disponible (note MLC SN2.3-SN2.4, validée par Yassine) |
| GPD (valeurs extrêmes) | disponible (McNeil 1997, données danoises, validé par Yassine) |
| Tranche de réassurance XL sur un an (Poisson × GPD, Panjer, VaR, CTE, burning cost) | disponible (calcul R indépendant avec evir et actuar, validé par Yassine) |
| Crédibilité (Bühlmann, Bühlmann-Straub, hiérarchique, Hachemeister) | disponible (vignette actuar, données de Hachemeister, validé par Yassine) |
| Agrégation SCR formule standard | disponible (SFCR CCR 2024 et IPBP 2016, validé par Yassine) |
| Marge de solvabilité tunisienne (`marge-solvabilite-tn`) et tables TD99 / TV99 | disponible (cas construits recalculés en R, en attente de validation) |
| Provisions techniques tunisiennes (`provisions-tn`, arrêté du 27/02/2001) | disponible (cas construit recalculé en R, en attente de validation) |
| Contrôle qualité des données sans calcul (`controler`) | disponible : triangles, sinistres, primes ; rien n'est corrigé |
| Registre des hypothèses d'un dossier (`registre`) | disponible : choix de jugement, valeurs par défaut, incohérences entre calculs, note Markdown |
| Comparaison avec un modèle externe (`comparer`) | disponible : rapport d'écarts ligne à ligne, arrondis publiés, facteurs d'unité |

## Installation

**Sur claude.ai** : télécharger `calcul-actuariel.zip` (onglet Actions du dépôt, ou `python outils/construire_zip.py`), puis le téléverser dans les paramètres de Claude, rubrique des skills. L'exécution de code doit être activée.

**Dans Claude Code** :

```
/plugin marketplace add selyassine/claude_actuaire
/plugin install claude-actuaire@claude-actuaire
```

Pour un projet actuariel dans Claude Code, [`docs/modele-CLAUDE.md`](docs/modele-CLAUDE.md) donne un modèle de CLAUDE.md : dictionnaire des données, règles de calcul avec le moteur, registre des choix de jugement, confidentialité. [`docs/modele-CLAUDE-tunisie.md`](docs/modele-CLAUDE-tunisie.md) en donne la variante pour un inventaire tunisien (Code des assurances, arrêté de 2001, règlement CGA 01/2021).

## Développement

```
pip install -r requirements-lock.txt      # versions exactes de la CI (ou requirements-dev.txt : bornes)
ruff check skills tests outils banc_essai
python -m coverage run -m pytest -v -rxs && python -m coverage report   # seuil : 90 %
python banc_essai/variantes/essai_a_blanc.py                           # le moteur seul : 59/59
```

La CI (GitHub Actions) lance à chaque PR : lint, tests et couverture sous Python 3.10 et 3.12 avec les versions verrouillées, tests sous Python 3.13 avec les dernières versions autorisées, audit des vulnérabilités des dépendances (`pip-audit`), banc d'essai à blanc, construction et installation réelle de l'archive du skill. Un tag `vX.Y.Z` publie la version sur GitHub avec l'archive et les notes du CHANGELOG, après avoir vérifié que le tag correspond à la version du moteur.

Pour ajouter une valeur de référence : copier `tests/references/_modele.yaml`, remplir la source exacte (ouvrage, page, tableau), laisser `statut: en_attente` jusqu'au contrôle par un actuaire.

## Confidentialité des données

Le moteur ne fait aucun appel réseau : il lit les fichiers fournis et écrit sa sortie, dans l'environnement d'exécution de Claude. En revanche, les données que l'utilisateur transmet à Claude (fichiers joints, contenu de la conversation) sont soumises aux conditions d'utilisation de Claude et à la politique de l'organisation de l'utilisateur. Pour des données d'assurance confidentielles, utiliser un compte et un espace de travail dont les conditions conviennent, ou anonymiser les données (les méthodes n'ont pas besoin des noms d'assurés).

## Limites

- Outil d'aide au calcul, pas un logiciel certifié : les résultats sont à revoir par un actuaire qualifié avant tout usage réglementaire ou comptable.
- La validation repose sur des publications et sur des logiciels indépendants (R), contrôlés par l'auteur ; une revue par un actuaire externe n'a pas encore été faite.
- Le SCR est agrégé à partir de sous-modules déjà calculés : aucun choc n'est appliqué.

## Organisation

```
.claude-plugin/              manifeste du plugin Claude Code
skills/calcul-actuariel/     le skill : SKILL.md, scripts/, references/
tests/                       tests, données et fiches de référence publiées
banc_essai/                  règles, tâches et notation du banc d'essai
outils/                      construction de l'archive .zip, notes de version
docs/                        guide des méthodes, réponses aux audits
```
