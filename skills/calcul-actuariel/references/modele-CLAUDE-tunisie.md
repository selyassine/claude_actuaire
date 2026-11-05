# Modèle de CLAUDE.md pour un inventaire d'une société d'assurance tunisienne

Ce modèle est la variante tunisienne de `modele-CLAUDE.md`. Pour l'utiliser :

1. Copier ce fichier à la racine du dossier de travail sous le nom `CLAUDE.md`.
2. Remplir les parties entre crochets.

Claude le lit au début de chaque session. Le garder court : c'est un index et un ensemble de règles. Quand une même correction revient deux fois, en faire une règle ici.

---

# Contexte du projet

- Entité : [nom], société d'assurance [non-vie / vie / mixte / Takaful], agréée par le Comité Général des Assurances (CGA).
- Objet : [inventaire au 31/12/2026 : provisions techniques, marge de solvabilité, rapport annuel au CGA].
- Référentiel :
  - Code des assurances (loi n° 92-24 et textes modificatifs), notamment l'art. 58 (éléments de la marge), l'art. 58 bis (minimum de marge), l'art. 59 (provisions) et l'art. 60 (rapport annuel) ;
  - arrêté du ministre des finances du 27 février 2001 (liste, calcul et représentation des provisions techniques), modifié notamment le 5 janvier 2009, le 6 juin 2011, le 3 mars 2012 et le 1er mars 2016 ;
  - règlement CGA n° 01/2021 (reporting et rapport annuel, exercice 2022 et suivants) ;
  - décision CGA n° 01/2016 (bonne gouvernance).
- Destinataires : [spécialiste des sciences actuarielles (décision 01/2016, art. 14), comité de gestion des risques, direction générale, commissaires aux comptes, CGA].
- Unité monétaire : [dinars / milliers de dinars (mD) / millions de dinars (MD)], la même dans tous les fichiers.

# Données (dictionnaire)

| Fichier | Contenu | Unité | Remarques |
| --- | --- | --- | --- |
| `donnees/[contrats.csv]` | Un contrat par ligne : catégorie, date d'effet, date d'échéance, prime commerciale | [mD] | Pour la PPNA (art. 17). Dates au format AAAA-MM-JJ |
| `donnees/[auto_materiels_payes.csv]` | Triangle cumulé des règlements, sinistres matériels automobile | [mD] | Pour les cadences de l'art. 22. Origine = exercice de survenance. Cohérent avec le tableau B6-4-1 du rapport annuel |
| `donnees/[sinistres_graves.csv]` | Dossiers importants, un sinistre par ligne | [dinars] | Cohérent avec le tableau B6-6 |
| `donnees/[marge.json]` | Primes émises et retenues, règlements des 3 derniers exercices (7 pour l'assurance crédit), PSAP de début et de fin, recours encaissés, charge nette ; PM et capitaux brut et net ; éléments de l'art. 58 | [mD] | Source : états A1 à A5, tableaux B1 et B8 |
| `donnees/[provisions.json]` | Blocs `ppna`, `prc`, `frais_gestion_sinistres`, `auto_materiels`, `equilibrage`, `egalisation_grele`, `rentes` | [mD] | PRC : cohérent avec le tableau B11 |

Conventions :

- Une catégorie s'écrit partout de la même façon (`automobile`, `incendie`, `groupe_maladie`, etc.).
- Une cellule vide dans un triangle signifie « pas encore observée » ; un paiement nul s'écrit `0`.
- Aucune donnée nominative : les identifiants d'assurés et de victimes sont retirés avant le dépôt dans le dossier.

# Règles de calcul

- Tout chiffre actuariel vient du skill `calcul-actuariel` (`python <skill>/scripts/cli.py ...`), jamais d'un calcul de tête.
- Avant tout calcul sur un nouveau fichier :
  - lancer `cli.py controler --nature [triangle|sinistres|primes]` ;
  - présenter les anomalies ;
  - je décide du traitement, et la décision est notée dans `hypotheses.md`.
- Commandes tunisiennes :
  - `marge-solvabilite-tn --entree donnees/marge.json` : minimum de l'art. 58 bis et taux de couverture ;
  - `provisions-tn --entree donnees/provisions.json --cadences sorties/<chain-ladder auto matériels>.json` : règles de l'arrêté de 2001 ;
  - `survie` ou `tarif-vie` avec `--modele td99` (contrats en cas de décès) ou `--modele tv99` (contrats en cas de survie).
- Auto matériels (art. 22) :
  - lancer d'abord `chain-ladder` sur le triangle des règlements et enregistrer sa sortie ;
  - lancer ensuite `provisions-tn`, qui retient la plus élevée des trois évaluations.
- Taux technique vie :
  - le moteur signale un taux au-dessus de 4 % ;
  - le plafond de 70 % du taux moyen des titres d'État est à vérifier à part, avec le taux moyen de l'année noté dans `hypotheses.md`.
- Chaque sortie JSON est enregistrée dans `sorties/` sous un nom explicite, par exemple `sorties/2026-12-31_marge.json`. Ce sont ces fichiers qui font foi.
- Avant toute synthèse : `cli.py registre --sorties sorties/ --note hypotheses_moteur.md`.
- Méthode absente du moteur (TGEN99, conversion des rentes du décret 2007-1871, limites de représentation des art. 29 à 31) :
  - le dire ;
  - calculer en Python explicite dans `scripts/` ;
  - marquer les chiffres « non validés par le moteur ».

# Interprétations réglementaires (à confirmer par le spécialiste actuariel)

Consignées dans `hypotheses.md`, avec date, auteur et justification :

- art. 58 bis : recours encaissés déduits de la charge de sinistres ; rapport de rétention sinistres = charge nette / charge brute de la période ;
- art. 19 : primes acquises fournies déjà corrigées (primes restant à émettre, primes à annuler, variation de PPNA) ;
- art. 21 : base du minimum de 5 % (PSAP frais compris par défaut, ou hors frais) ;
- art. 24 et 25 : imputation d'une perte technique sur la provision d'équilibrage ou d'égalisation ;
- tables TD99 et TV99 : q_x tirés des l_x (par défaut) ou q_x imprimés (`--qx-source publie`).

Claude propose, l'actuaire décide. Aucun choix de jugement n'est fait en silence.

# Livrables

- `rapport/` contient la partie « Provisions techniques » du rapport de solvabilité (règlement 01/2021, art. 8) :
  - méthodes utilisées ;
  - nombre de sinistres tardifs et évaluation de leur coût ;
  - liquidation des provisions.
- `rapport/` contient aussi la partie « Marge de solvabilité » : analyse prospective et conformité à la législation.
- Chaque tableau indique la commande du moteur qui l'a produit et l'`empreinte_resultats` de la sortie.
- Les avertissements du moteur figurent dans la note, avec la décision prise.

# Confidentialité

- Les tableaux statistiques B et les renseignements RG du rapport annuel ne sont pas publiables (règlement 01/2021, art. 4). Ils restent dans le dossier de travail.
- Données réelles uniquement dans le cadre autorisé par [la politique de l'entreprise] ; sinon, jeu de données synthétique de même structure.
- Aucun mot de passe, clé ou chaîne de connexion dans les fichiers ni dans les messages.

# Ce que j'attends de Claude

- Proposer le plan de travail avant les gros calculs, puis avancer étape par étape.
- Dire clairement ce qui relève d'une hypothèse, d'un résultat du moteur, d'une interprétation réglementaire ou d'une estimation non validée.
- Citer l'article du Code ou de l'arrêté pour chaque règle appliquée.
