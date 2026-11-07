"""Écrit les tâches de la famille « pièges » (consigne.md, corrige.yaml, données).

Un piège est une tâche où la bonne réponse n'est pas le calcul naïf : une donnée manque (la valeur attendue est
alors `null`, avec la clé présente), une donnée est piégée (primes TTC, triangle incrémental, recours), ou une règle
réglementaire doit être appliquée (table TV99 pour une rente, plafond de taux de 4 %).

Valeurs numériques : corriges.R (sortie corriges.sortie.txt) ou corrigés déjà validés (variante v-cl-01,
fiche r-tunisie-tv99-annuite-60). Exécution : python banc_essai/pieges/construire_taches.py
"""

import csv
import shutil
from pathlib import Path

import yaml

ICI = Path(__file__).resolve().parent
TACHES = ICI / "taches"
VARIANTES = ICI.parent / "variantes" / "taches"

FIN = ("Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON avec les clés "
       "suivantes (nombres sans séparateur de milliers ; `null` pour une valeur que tu ne peux pas calculer avec "
       "les données fournies, `true` ou `false` pour une question oui / non) :\n\n```resultats\n{cles}\n```\n")

MARGE_INTRO = ("Une société d'assurance non-vie tunisienne (pas d'assurance crédit) prépare le calcul de sa marge de "
               "solvabilité minimale (Code des assurances, art. 58 bis) au 31/12/2025. Montants en milliers de dinars.\n\n")

SPEC = {
    "p-tn-marge-2ex": dict(
        piege="donnée manquante : règlements de 2 exercices au lieu de 3",
        texte=MARGE_INTRO + "- primes émises et acceptées 2025, hors taxes et nettes d'annulations : 52 000 ; primes retenues : 39 000 ;\n"
        "- règlements de sinistres : 2024 : 21 000 ; 2025 : 23 500 ;\n"
        "- provisions pour sinistres à payer : fin 2023 : 48 000 ; fin 2025 : 53 000 ;\n"
        "- recours encaissés sur la période : 900 ; charge de sinistres nette de réassurance sur la même période : 45 000.\n\n"
        "Calcule la marge de solvabilité minimale.",
        cles='{"minimum_reglementaire": 0}',
        valeurs=[dict(nom="minimum_reglementaire", attendu=None)],
        source="art. 58 bis a : moyenne des 3 derniers exercices ; seuls 2 exercices de règlements sont fournis"),
    "p-tn-marge-ttc": dict(
        piege="primes données toutes taxes comprises",
        texte=MARGE_INTRO + "- primes émises et acceptées 2025 toutes taxes comprises, nettes d'annulations : 61 200, dont taxes 9 200 ;\n"
        "- primes retenues (hors taxes) : 20 000 ;\n"
        "- règlements de sinistres : 2023 : 14 000 ; 2024 : 15 500 ; 2025 : 16 000 ;\n"
        "- provisions pour sinistres à payer : fin 2022 : 55 000 ; fin 2025 : 61 000 ;\n"
        "- recours encaissés sur la période : 1 500 ; charge de sinistres nette de réassurance sur la période : 46 000.\n\n"
        "Calcule la marge de solvabilité minimale.",
        cles='{"minimum_reglementaire": 0}',
        valeurs=[dict(nom="minimum_reglementaire", attendu=5200, tolerance_absolue=0.5)],
        source="corriges.R (bloc p-tn-marge-ttc) : base primes sur 52 000 HT"),
    "p-tn-marge-recours": dict(
        piege="recours encaissés à déduire de la charge (le plancher de 50 % rend l'oubli visible)",
        texte=MARGE_INTRO + "- primes émises et acceptées 2025, hors taxes et nettes d'annulations : 20 000 ; primes retenues : 18 000 ;\n"
        "- règlements de sinistres bruts : 2023 : 31 000 ; 2024 : 33 000 ; 2025 : 35 000 ;\n"
        "- provisions pour sinistres à payer : fin 2022 : 70 000 ; fin 2025 : 90 000 ;\n"
        "- recours encaissés de 2023 à 2025 : 12 000 ;\n"
        "- charge de sinistres nette de réassurance sur la période (même définition) : 40 000.\n\n"
        "Calcule la marge de solvabilité minimale.",
        cles='{"minimum_reglementaire": 0}',
        valeurs=[dict(nom="minimum_reglementaire", attendu=4458.333333333333, tolerance_absolue=0.5)],
        source="corriges.R (bloc p-tn-marge-recours)"),
    "p-tn-rente-tv99": dict(
        piege="rente viagère d'un homme : la table réglementaire des contrats en cas de vie est TV99, pas TD99",
        texte="Un assureur vie tunisien tarifie une rente viagère immédiate de 1 000 dinars par an, payable d'avance "
        "(premier terme à la souscription), pour un homme de 60 ans. Taux technique 3 %. Utilise la table réglementaire "
        "tunisienne applicable (arrêté du 27/02/2001).\n\nDonne la prime unique pure.",
        cles='{"prime_unique": 0}',
        valeurs=[dict(nom="prime_unique", attendu=14755.1743042141, tolerance_absolue=0.5)],
        source="fiche validée r-tunisie-tv99-annuite-60 : ä_60 = 14,7551743042141 (TV99, 3 %), × 1 000"),
    "p-tn-taux-5": dict(
        piege="taux technique au-delà du plafond réglementaire de 4 % (arrêté de 2001, art. 5 b)",
        texte="Un assureur vie tunisien veut tarifer un capital décès vie entière de 10 000 dinars pour un homme de 45 ans, "
        "avec un taux technique de 5 % et la table réglementaire tunisienne des contrats en cas de décès.\n\n"
        "Indique si ce taux technique respecte la réglementation tunisienne.",
        cles='{"taux_reglementaire_respecte": true}',
        valeurs=[dict(nom="taux_reglementaire_respecte", attendu=False)],
        source="arrêté du 27/02/2001, art. 5 b : taux au plus égal à 4 % (validé par Yassine le 2026-11-05)"),
    "p-cl-trou": dict(
        piege="cellule manquante au milieu du triangle : un choix de l'utilisateur est nécessaire",
        texte="Le fichier `triangle.csv` contient un triangle de paiements cumulés (années d'origine 2011 à 2020, "
        "10 périodes de développement).\n\nApplique la méthode Chain Ladder standard (facteurs moyens pondérés par les "
        "volumes sur toutes les années, sans queue) et donne la provision totale.",
        cles='{"provision_totale": 0}',
        valeurs=[dict(nom="provision_totale", attendu=None)],
        source="triangle de v-cl-01 avec la cellule 2014 / période 4 vidée ; Chain Ladder non défini sans choix"),
    "p-cl-incremental": dict(
        piege="triangle incrémental présenté comme « paiements de chaque période »",
        texte="Le fichier `triangle.csv` contient, pour chaque année d'origine (2011 à 2020) et chaque période de "
        "développement (1 à 10), le montant payé au cours de la période.\n\nApplique la méthode Chain Ladder standard "
        "(facteurs moyens pondérés par les volumes sur toutes les années, sans queue) et donne la provision totale.",
        cles='{"provision_totale": 0}',
        valeurs=[dict(nom="provision_totale", attendu=71638.923481, tolerance_relative=0.0005)],
        source="triangle de v-cl-01 converti en incréments ; corrigé validé de v-cl-01 (R ChainLadder)"),
    "p-xl-annees": dict(
        piege="nombre d'années d'observation absent : la fréquence annuelle n'est pas estimable",
        texte="Le fichier `sinistres_tempete.csv` contient des sinistres tempête de plus d'un million (en millions), "
        "une ligne par sinistre.\n\nAvec une loi de Pareto généralisée au-delà du seuil de 6 et une fréquence de Poisson, "
        "donne la prime pure annuelle d'une tranche de réassurance 75 XS 25.",
        cles='{"prime_pure_annuelle": 0}',
        valeurs=[dict(nom="prime_pure_annuelle", attendu=None)],
        source="données de v-gpd-01 ; nombre d'années non donné"),
    "p-scr-scenario": dict(
        piege="scénario de taux (hausse ou baisse) non précisé : le paramètre A de l'art. 164 est indéterminé",
        texte="Un assureur vie utilise la formule standard Solvabilité II. Ses SCR bruts de sous-modules de marché "
        "(en milliers d'euros) sont : taux d'intérêt 41 250, actions 63 800, immobilier 9 120, spread 27 400, change 3 350, "
        "concentration 5 100.\n\nCalcule le SCR marché.",
        cles='{"scr_marche": 0}',
        valeurs=[dict(nom="scr_marche", attendu=None)],
        source="règlement délégué 2015/35, art. 164 : la corrélation taux / actions, immobilier, spread dépend du scénario"),
}


def _triangle_v_cl_01():
    with open(VARIANTES / "v-cl-01" / "triangle.csv", encoding="utf-8") as f:
        return list(csv.reader(f))


def _ecrire_triangle(lignes, chemin):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(lignes)


def donnees(tid, dossier):
    if tid == "p-cl-trou":
        t = _triangle_v_cl_01()
        t[4][4] = ""  # 2014, période 4
        _ecrire_triangle(t, dossier / "triangle.csv")
    elif tid == "p-cl-incremental":
        t = _triangle_v_cl_01()
        for ligne in t[1:]:
            vals = [float(v) for v in ligne[1:] if v]
            inc = [vals[0]] + [b - a for a, b in zip(vals[:-1], vals[1:], strict=True)]
            ligne[1:] = [f"{x:g}" for x in inc] + [""] * (len(ligne) - 1 - len(inc))
        _ecrire_triangle(t, dossier / "triangle.csv")
    elif tid == "p-xl-annees":
        shutil.copy(VARIANTES / "v-gpd-01" / "sinistres_tempete.csv", dossier / "sinistres_tempete.csv")


def main():
    for tid, s in SPEC.items():
        d = TACHES / tid
        d.mkdir(parents=True, exist_ok=True)
        (d / "consigne.md").write_text(s["texte"] + "\n\n" + FIN.format(cles=s["cles"]), encoding="utf-8")
        donnees(tid, d)
        corrige = {"famille": "pieges", "piege": s["piege"], "source": s["source"], "statut": "valide",
                   "valide_par": "Yassine Selmi", "date_validation": "2026-11-07", "valeurs": s["valeurs"]}
        (d / "corrige.yaml").write_text(yaml.safe_dump(corrige, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
