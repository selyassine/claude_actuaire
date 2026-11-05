# Modèle de CLAUDE.md pour un projet actuariel avec le skill calcul-actuariel

Copier ce fichier à la racine du dossier de travail sous le nom `CLAUDE.md`, puis remplir les parties entre crochets. Claude le lit au début de chaque session. Le garder court (moins de 150 lignes) : c'est un index et un ensemble de règles, pas un manuel. Chaque fois qu'une même correction revient deux fois, ajouter une règle ici.

---

# Contexte du projet

- Entité : [nom, type : société d'assurance non-vie / vie / mutuelle / réassureur]
- Objet : [ex. provisions techniques non-vie au 31/12/2026, tarification d'un traité XL, validation d'un modèle interne de provisionnement]
- Référentiel : [Solvabilité II (meilleure estimation), normes locales (préciser), IFRS 17]
- Destinataires du livrable : [direction technique, fonction actuarielle, régulateur, commissaire aux comptes]

# Données (dictionnaire)

Pour chaque fichier de `donnees/` : contenu, unité, période, source, date d'extraction.

| Fichier | Contenu | Unité | Remarques |
| --- | --- | --- | --- |
| `donnees/[triangle_payes.csv]` | Triangle [cumulé / incrémental] des paiements, [branche] | [milliers d'euros] | Origine = [année de survenance / de souscription] ; développement en [mois / années] |
| `donnees/[primes.csv]` | Colonnes `Origine`, `Prime` [, `Ratio`] | [même unité que le triangle] | Primes [acquises / émises], [brutes / nettes] de réassurance |
| `donnees/[sinistres_graves.csv]` | Un sinistre par ligne, colonne `[Montant]` | [euros] | Seuil de collecte [x] ; montants [indexés as-if au 31/12/2026 / non indexés] ; période [2015-2025, 11 ans] |

Conventions :
- Les libellés d'origine sont identiques entre triangle et primes (ex. `2020`, jamais `2020.0`).
- Une cellule vide dans un triangle signifie « pas encore observée » ; un paiement nul s'écrit `0`.
- Aucune donnée nominative : identifiants d'assurés retirés avant le dépôt dans le dossier.

# Règles de calcul

- Tout chiffre actuariel vient du skill `calcul-actuariel` (`python <skill>/scripts/cli.py ...`), jamais d'un calcul de tête ni d'un script écrit pour l'occasion quand la méthode existe dans le moteur.
- Avant tout calcul sur un nouveau fichier : `cli.py controler --nature [triangle|sinistres|primes]`. Les anomalies bloquantes et les alertes me sont présentées ; je décide du traitement. Ne rien corriger sans mon accord, et noter chaque décision dans `hypotheses.md`.
- Chaque sortie JSON du moteur est enregistrée dans `sorties/` sous un nom explicite (`sorties/2026-12-31_mack_auto_payes.json`). Ce sont ces fichiers qui font foi ; les rapports citent leurs chiffres et leur `empreinte_resultats`.
- Pour revérifier un chiffre archivé : `cli.py rejouer --sortie <fichier>`.
- Avant toute synthèse : `cli.py registre --sorties sorties/ --note hypotheses_moteur.md`. Les incohérences sont traitées ou expliquées, les valeurs par défaut sont confirmées par moi.
- Pour valider un autre modèle (Excel, logiciel interne) : `cli.py comparer` contre la sortie du moteur sur les mêmes données ; les écarts sont expliqués ou signalés, jamais effacés.
- Méthode absente du moteur : le dire, calculer en Python explicite dans `scripts/`, et marquer les chiffres « non validés par le moteur ».

# Choix de jugement (à tenir à jour)

Consignés dans `hypotheses.md`, avec date, auteur et justification :
- facteurs exclus ou imposés, facteur de queue, période de calcul des moyennes ;
- ratios a priori (BF) et leur source ;
- seuil GPD, période d'observation et indexation des sinistres graves ;
- graine et nombre de simulations des méthodes stochastiques.

Claude propose, l'actuaire décide. Aucun choix de jugement n'est fait en silence.

# Livrables

- `rapport/` : note technique (méthodes, hypothèses, résultats, limites, sensibilités) et synthèse pour [destinataire].
- Chaque tableau de résultats indique la commande du moteur qui l'a produit.
- Les avertissements du moteur figurent dans la note, avec la décision prise.

# Confidentialité

- Données réelles uniquement dans le cadre autorisé par [la politique de l'entreprise / le service informatique] ; sinon, jeu de données synthétique de même structure.
- Aucun mot de passe, clé ou chaîne de connexion dans les fichiers ni dans les messages.
- Signaler avant exécution tout script qui écrit, déplace ou supprime des fichiers hors de `sorties/` et `rapport/`.

# Ce que j'attends de Claude

- Proposer le plan de travail avant les gros calculs, puis avancer étape par étape.
- Dire clairement ce qui relève d'une hypothèse, d'un résultat du moteur, ou d'une estimation non validée.
- Signaler tout ce qui demande une validation actuarielle avant d'aller plus loin.
