# Rapport du passage sur la famille « pièges »

Passage du 2026-11-07, 27 sessions sur claude.ai (9 tâches × 3 conditions, un passage par tâche et par condition), selon `REGLES.md` et son amendement du 2026-11-06. Les corrigés ont été validés par Yassine le 2026-11-07, avant la première session.

- Modèle : Opus 5.5 (`claude-opus-5-5`), effort « Moyen », identique pour les 27 sessions.
- Skill : `calcul-actuariel` 0.5.5, réinstallé le 2026-11-07 (zip identique à `skills/calcul-actuariel` sur main).
- A : conversation incognito, skill désactivé, sans exécution de code. La recherche web restait disponible.
- B : conversation normale, exécution de code active, skill désactivé.
- C : conversation normale, skill activé.
- Consigne : le texte de `consigne.md` et les fichiers de données de la tâche, sans autre indication.

## Résultat

| Seuil (amendement du 2026-11-06) | Visé | Obtenu | Atteint |
| --- | --- | --- | --- |
| C | ≥ 8/9 | 9/9 | oui |
| Écart C − B (mesuré à part) | — | + 44,4 points | — |

| Tâche | Piège | A | B | C |
| --- | --- | --- | --- | --- |
| p-tn-marge-2ex | 2 exercices au lieu de 3 | faux (7 800) | juste (`null`) | juste (`null`) |
| p-tn-marge-ttc | primes TTC | faux (9 568) | faux (9 568) | juste (5 200) |
| p-tn-marge-recours | recours à déduire | juste | juste | juste |
| p-tn-rente-tv99 | table TV99 et non TD99 | faux (`null`) | faux (`null`) | juste (14 755,17) |
| p-tn-taux-5 | taux technique de 5 % > 4 % | juste | juste | juste |
| p-cl-trou | cellule vide | faux (71 860) | faux (71 860,2) | juste (`null`) |
| p-cl-incremental | triangle incrémental | juste (71 639) | juste | juste |
| p-xl-annees | nombre d'années absent | juste | juste | juste |
| p-scr-scenario | scénario de taux absent | faux (121 505) | faux (121 505) | juste (`null`) |
| **Total** | | **4/9** | **5/9** | **9/9** |

Commande : `python banc_essai/noter.py --reponses banc_essai/pieges/reponses --taches banc_essai/pieges/taches --conditions A,B,C`. Aucun essai manquant.

## Les erreurs, une par une

### Condition C

Aucune. Le skill a été lu dans les 9 sessions. Sur les deux pièges que le moteur ne détecte pas seul (primes TTC, triangle incrémental), Claude les a repérés dans la consigne et a passé les bonnes options.

### Conditions A et B

- **p-scr-scenario (A et B).** Les deux réponses notent que le sens du choc de taux n'est pas donné. Elles chiffrent quand même : 121 505 avec le choc à la baisse, 103 078 avec la hausse, puis retiennent la baisse. La consigne demande `null` pour une valeur non calculable.
- **p-cl-trou (A et B).** La cellule vide est comblée ou ignorée, et une provision est chiffrée (71 860).
- **p-tn-marge-ttc (A et B).** Les deux réponses retirent bien les taxes (52 000 HT). L'écart vient du rapport de rétention de la base primes. Elles appliquent la charge nette sur la charge brute (46 000 / 50 000 = 92 %), alors que le corrigé applique les primes retenues sur les primes émises (20 000 / 52 000), ramenées au plancher de 50 %. Le piège TTC lui-même est donc détecté. C'est une question d'interprétation de l'art. 58 bis, tranchée par l'interprétation validée le 2026-11-05. Voir « À trancher » ci-dessous.
- **p-tn-rente-tv99 (A et B).** Les deux réponses cherchent la table de l'arrêté du 27/02/2001 sur le web, ne trouvent pas ses valeurs et répondent `null`. Ce refus est prudent, mais il est faux : la table fait partie du texte réglementaire, et l'attendu est 14 755,17.
- **p-tn-marge-2ex (A seulement).** Calcul sur 2 exercices (7 800) au lieu d'un refus. B a refusé correctement.

## Lecture

- Le skill apporte surtout le **refus motivé** : trou dans le triangle, scénario SCR absent. Sans skill, Claude remarque souvent la donnée manquante, mais il chiffre quand même avec une hypothèse.
- Il apporte aussi les **données réglementaires tunisiennes** (table TV99), introuvables pour Claude sans le skill.
- Les pièges sur les recours, le taux technique, le nombre d'années XL et le triangle incrémental sont détectés sans le skill.

## À trancher

Sur p-tn-marge-ttc, A et B appliquent le rapport sinistres à la base primes, comme dans la directive européenne de 1973. Le moteur et le corrigé utilisent le rapport des primes retenues. Si le texte tunisien vise un seul rapport (sinistres) pour les deux bases, le corrigé et le moteur sont à revoir. Avec ce rapport, le minimum serait 9 568 et non 5 200. À vérifier par Yassine sur le texte de l'art. 58 bis.

## Sessions

Les identifiants des conversations sont dans l'historique claude.ai (B et C). Les sessions A, en incognito, n'y figurent pas.
