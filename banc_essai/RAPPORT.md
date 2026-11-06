# Rapport du banc d'essai réduit (premier passage)

Passage du 2026-11-04, 48 sessions sur claude.ai (16 tâches × 3 conditions, un passage par tâche et par condition), selon `REGLES.md` et son amendement du 2026-11-03.

## Résultat

Le skill ne passe pas les seuils fixés à l'avance.

| Seuil (REGLES.md) | Visé | Obtenu | Atteint |
| --- | --- | --- | --- |
| C, ensemble | ≥ 95 % | 94,5 % (52/55) | non |
| C, chaque famille | ≥ 90 % | 2 familles sous 90 % (SCR 71 %, GPD 89 %) | non |
| Écart C − B | ≥ 30 points | + 1,8 point | non |

La raison principale est que la condition B est déjà très forte : quand Claude peut écrire son propre Python, il trouve 92,7 % des valeurs. L'écart de 30 points visé supposait un B bien plus faible.

## Scores par famille

| Famille | A (sans code) | B (code, sans skill) | C (skill) |
| --- | --- | --- | --- |
| Chain Ladder | 4/6 | 6/6 | 6/6 |
| BF et Cape Cod | 6/6 | 6/6 | 6/6 |
| Mack | 6/6 | 6/6 | 6/6 |
| Bootstrap et ODP | 3/6 | 3/6 | **6/6** |
| Vie | 1/8 | 8/8 | 8/8 |
| GPD | 9/9 | 8/9 | 8/9 |
| Crédibilité | 6/7 | 7/7 | 7/7 |
| SCR | 7/7 | 7/7 | **5/7** |
| **Ensemble** | **42/55 (76,4 %)** | **51/55 (92,7 %)** | **52/55 (94,5 %)** |

## Les erreurs, une par une

### Condition C (3 valeurs fausses)

1. **scr-02, BSCR et SCR** (écart de 369 421 €). Le skill installé sur claude.ai n'était pas la dernière version : Claude écrit dans sa réponse que « l'agrégation SCR n'existe pas encore dans le moteur (prévue en phase 5) ». Il a donc codé l'agrégation lui-même et s'est trompé. La version de `calcul-actuariel.zip` qui contient la commande `scr` n'avait pas été réinstallée dans claude.ai. Le même problème touche scr-01, où Claude a aussi codé lui-même, mais sans erreur.
2. **gpd-02, erreur type de ξ** : 0,0967 au lieu de 0,09 (tolérance 0,005). Le moteur rend 0,0904, la formule asymptotique de McNeil, qui serait juste. Claude a préféré l'erreur type tirée de la hessienne observée (celle de `evir`) et l'a mise dans le bloc `resultats`. Le skill doit dire plus clairement de rendre la valeur du moteur.

### Condition B (4 valeurs fausses)

- **odp-01** (3 valeurs) : dispersion 1 044,07 au lieu de 1 049,8. Claude a estimé la dispersion par le khi-deux de Pearson, alors que la consigne demande la déviance. Les erreurs de prédiction en découlent.
- **gpd-02, erreur type de ξ** : même valeur que C (0,0967).

### Condition A (13 valeurs fausses)

- **vie-01 et vie-02** (7 valeurs) : écarts de 1 à 10 centimes, des erreurs de calcul de tête.
- **odp-01** (3 valeurs) : même confusion Pearson / déviance qu'en B.
- **cl-01** (2 valeurs) : ultime faux de 546 413 €, une erreur d'arithmétique.
- **cred-01** (1 valeur) : variance intra arrondie trop tôt (139 120 033 au lieu de 139 120 026).

## Ce que le skill apporte, et ce qu'il n'apporte pas

- **Gain net sur le bootstrap et l'ODP** (3/6 → 6/6) : le moteur applique la bonne convention de dispersion (déviance), que Claude sans skill ne choisit pas.
- **Aucun gain mesurable** sur Chain Ladder, BF, Mack, vie, crédibilité : B est déjà à 100 %.
- **Perte sur le SCR**, due à une version périmée du skill sur claude.ai, pas au moteur : le moteur reproduit les deux corrigés SCR à l'essai à blanc.
- Le code seul (B contre A) apporte 16 points, surtout en vie (1/8 → 8/8) et Chain Ladder.

## Risque de mémorisation

Toutes les tâches utilisent des données publiées (Taylor-Ashe, données danoises de McNeil, Hachemeister, AMLCR, SFCR). La condition A le montre :

- en GPD, A trouve 9/9 sans code. Pour gpd-01, Claude écrit en B incognito qu'il n'a pas pu exécuter de code et donne « les estimations publiées pour ce jeu » ;
- en SCR, A trouve 7/7.

Les scores A et B sont donc probablement surestimés par rapport à des données nouvelles. Seules des variantes (données décalées, autre seuil, autre taux), prévues dans les règles d'origine, permettraient de mesurer l'écart réel.

## Conditions de passage et écarts au protocole

- **Modèle** : le modèle par défaut de claude.ai au 2026-11-04, effort « Moyen », identique pour les 48 sessions (nom exact noté dans le fil du projet). Compte Pro de Yassine.
- **Lancement** : sessions lancées automatiquement depuis le navigateur (extension Claude in Chrome), consigne et fichiers de données joints automatiquement. Aucune intervention pendant les réponses.
- **Condition A** : conversations incognito, skills `calcul-actuariel` et `actuarial-review` désactivés, exécution de code désactivée. Aucun outil utilisé.
- **Conditions B et C** : conversations normales. Le mode incognito bloque l'exécution de code : les 3 premières tâches B, d'abord jouées en incognito, ont été rejouées en conversation normale, et seules ces réponses sont notées. Les 32 conversations B et C sont dans l'historique claude.ai de Yassine.
- **Condition C** : seul `calcul-actuariel` activé (`actuarial-review` désactivé). Le skill a été appelé dans les 16 sessions.
- **Recherche web** : activée dans les trois conditions (réglage du compte), utilisée dans aucune session. La recherche dans les anciennes conversations était aussi activée en B et C, sans être utilisée.
- **mack-02 en A** : deux messages de réponse (suite automatique) ; le dernier bloc `resultats` est noté.
- **Version du skill** : version du 2026-11-03 sans la commande `scr` (voir plus haut). C'est le principal écart.
- **Hypothèses citées** : non mesuré dans ce passage.
- **Textes complets** : `reponses/` ne garde que le bloc `resultats` et les outils utilisés. Les textes complets sont restés dans le navigateur de Yassine.

## Suites proposées

1. Réinstaller `calcul-actuariel.zip` à jour sur claude.ai et rejouer C sur scr-01 et scr-02, en passage complémentaire signalé comme tel.
2. Dans SKILL.md, demander de reporter dans le résultat la valeur du moteur, et de signaler à part une autre estimation (cas de l'erreur type GPD).
3. Pour mesurer un vrai écart C − B, construire les variantes prévues par les règles d'origine (données modifiées, corrigés tirés de R) : ce sont elles qui neutralisent la mémorisation.
4. Revoir le seuil de 30 points : avec l'exécution de code, Claude sans skill est déjà à 93 % sur ces tâches standard.

## Passage complémentaire du 2026-11-05 : SCR avec le skill à jour

Signalé comme complémentaire : il n'entre pas dans les scores officiels ci-dessus.

Yassine a réinstallé `calcul-actuariel.zip` (version avec la commande `scr`) le 2026-11-05. scr-01 et scr-02 ont été rejoués en condition C, dans des conversations neuves, avec les mêmes réglages. Le skill a été appelé dans les deux sessions.

| Tâche | Valeurs justes |
| --- | --- |
| scr-01 | 3/3 |
| scr-02 | 4/4 |

Avec le skill à jour, la famille SCR passe de 5/7 à 7/7 en C. Si l'on remplaçait les deux réponses SCR du passage officiel par celles-ci, C serait à 54/55 (98,2 %) et seule la famille GPD resterait sous 90 % (8/9). L'écart C − B resterait faible (+5,5 points), loin des 30 points visés.

Réponses : `banc_essai/reponses_complementaires/C/`.
