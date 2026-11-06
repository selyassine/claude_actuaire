# Crédibilité

Fichier de référence du skill `calcul-actuariel` pour la commande `credibilite`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `credibilite` | Bühlmann, Bühlmann-Straub, hiérarchique (Jewell), régression de Hachemeister : variances structurelles, facteurs et primes de crédibilité | testé : vignette actuar sur les données de Hachemeister (1975) |

Pour `credibilite`, le fichier est au format long : une ligne par entité et période, avec les colonnes `Entite`, `Periode`, `Ratio`, `Poids` (sauf `--modele buhlmann`) et `Cohorte` (modèle `hierarchique`). Estimateurs : `--estimateur sans-biais` (défaut, Bühlmann et Gisler 2005) ou `iteratif` (Bichsel-Straub ; défaut du modèle hiérarchique). Pour la régression, préfère `--barycentre` : sans lui, la droite de crédibilité peut sortir de l'intervalle entre droites individuelle et collective (cas de l'État 4 de Hachemeister).
