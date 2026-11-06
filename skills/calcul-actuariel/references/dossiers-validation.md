# Dossiers, traçabilité et validation de modèles

Fichier de référence du skill `calcul-actuariel` pour les commandes `rejouer`, `registre` et `comparer`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `registre` | Registre des hypothèses d'un dossier : consolide les sorties archivées, classe les hypothèses (choix de jugement, valeurs par défaut, méthode), détecte les incohérences, écrit la note d'hypothèses | disponible |
| `comparer` | Rapport d'écarts ligne à ligne entre les résultats d'un modèle externe et une sortie archivée du moteur | testé (propriétés et refus) |

`rejouer --sortie calcul.json` refait un calcul archivé à partir de sa commande de reproduction et compare les résultats ; une sortie sans `empreinte_resultats` (version ≥ 0.3.0) est refusée.

Pour un dossier de plusieurs calculs, enregistre chaque sortie JSON dans un même dossier (par exemple `sorties/`), puis lance `registre --sorties sorties/ --note hypotheses.md` avant de rédiger la synthèse. Présente d'abord les incohérences, puis les valeurs par défaut à faire confirmer par l'utilisateur. Ne présente pas une note dont la conclusion est `bloquant`.

Pour valider le modèle d'un utilisateur (Excel, logiciel interne) : 1) lance la méthode du moteur sur les mêmes données et enregistre la sortie JSON dans un fichier ; 2) lance `comparer --lister` pour voir les chemins ; 3) écris un CSV `chemin;valeur` (colonnes facultatives `libelle`, `tolerance_relative`) en recopiant les valeurs du modèle externe telles quelles, sans les arrondir ni les convertir ; 4) lance `comparer`. Rapporte la conclusion, chaque ligne `ecart` avec sa valeur moteur et externe, et les avertissements (facteur d'unité, convention de signe, hypothèse commune). Une ligne `arrondi` est conforme à l'arrondi publié près. N'explique jamais un écart sans l'avoir vérifié : propose des causes, présente-les comme des pistes.


Pour organiser un projet actuariel dans Claude Code, `references/modele-CLAUDE.md` donne un modèle de CLAUDE.md.
