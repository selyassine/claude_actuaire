"""Écrit consigne.md et corrige.yaml de chaque variante à partir des corrigés R.

Exécution, après les trois scripts R :
    python banc_essai/variantes/construire_taches.py
"""

import json
from pathlib import Path

import yaml

ICI = Path(__file__).resolve().parent
TACHES = ICI / "taches"

FIN = (
    "Termine ta réponse par un bloc de code `resultats` contenant uniquement un objet JSON "
    "avec les clés suivantes (nombres, sans séparateur de milliers) :\n\n```resultats\n{cles}\n```\n"
)

# Tolérances : relatives pour les montants calculés exactement (Claude peut arrondir à l'unité),
# absolues pour les facteurs, comptes et valeurs au centime. Bootstrap : 5 % (simulation).
REL = {"tolerance_relative": 0.0005}
FACT = {"tolerance_absolue": 0.0005}
CENT = {"tolerance_absolue": 0.005}
EURO = {"tolerance_absolue": 1}

TRI = "Le fichier `triangle.csv` contient un triangle de paiements cumulés"

SPEC = {
    "v-cl-01": dict(
        famille="chain_ladder", source="R ChainLadder::chainladder (facteurs pondérés toutes années)",
        texte=f"{TRI} (années d'origine 2011 à 2020, 10 périodes de développement).\n\n"
        "Applique la méthode Chain Ladder standard (facteurs moyens pondérés par les volumes sur toutes les années, sans queue). "
        "Donne la provision totale, la charge ultime de l'année 2020 et le facteur de développement de la période 1 à 2.",
        valeurs={"provision_totale": ("provision_totale", REL), "ultime_2020": ("ultime_2020", REL),
                 "facteur_1_2": ("facteur_1_2", FACT)}),
    "v-cl-02": dict(
        famille="chain_ladder", source="R ChainLadder::chainladder avec poids sur les 3 dernières diagonales",
        texte=f"{TRI} (années d'origine 2014 à 2020, 7 périodes de développement).\n\n"
        "Applique Chain Ladder avec des facteurs moyens pondérés par les volumes sur les 3 dernières années calendaires "
        "(les 3 derniers facteurs individuels de chaque colonne), en pleine précision, sans queue. "
        "Donne la provision totale, le facteur cumulé (CDF) de l'âge 1 jusqu'à l'ultime et le facteur de la période 1 à 2.",
        valeurs={"provision_totale": ("provision_totale", REL), "cdf_1": ("cdf_1", FACT),
                 "facteur_1_2": ("facteur_1_2", FACT)}),
    "v-bf-01": dict(
        famille="bf_cape_cod", source="facteurs R ChainLadder::chainladder, formule BF explicite en R (à vérifier)",
        texte=f"{TRI} (années d'origine 2013 à 2022, 10 périodes de développement). "
        "Le fichier `primes.csv` donne par année d'origine la prime acquise et une charge ultime a priori (colonne `Ultime_a_priori`).\n\n"
        "Applique la méthode Bornhuetter-Ferguson avec ces ultimes a priori. Cadence : facteurs Chain Ladder moyens pondérés "
        "sur toutes les années, en pleine précision, sans queue. "
        "Donne la charge ultime totale, l'IBNR total et l'ultime de l'année 2022.",
        valeurs={"ultime_total": ("ultime_total", REL), "ibnr_total": ("ibnr_total", REL),
                 "ultime_2022": ("ultime_derniere", REL)}),
    "v-bf-02": dict(
        famille="bf_cape_cod", source="facteurs R ChainLadder::chainladder, formule Cape Cod explicite en R (à vérifier)",
        texte=f"{TRI} (années d'origine 2013 à 2022, 10 périodes de développement). "
        "Le fichier `primes.csv` donne la prime acquise par année d'origine (n'utilise pas la colonne `Ultime_a_priori`).\n\n"
        "Applique la méthode Cape Cod (Stanard-Bühlmann) sans tendance ni ajustement de primes : ratio de sinistralité attendu "
        "estimé sur toutes les années. Cadence : facteurs Chain Ladder moyens pondérés sur toutes les années, en pleine précision, sans queue. "
        "Donne le ratio Cape Cod (en décimal, par exemple 0,65), la charge ultime totale et l'IBNR total.",
        valeurs={"ratio_cape_cod": ("ratio_cape_cod", FACT), "ultime_total": ("ultime_total", REL),
                 "ibnr_total": ("ibnr_total", REL)}),
    "v-mack-01": dict(
        famille="mack", source="R ChainLadder::MackChainLadder(est.sigma = \"Mack\")",
        texte=f"{TRI} (années d'origine 2012 à 2022, 11 périodes de développement).\n\n"
        "Calcule la provision Chain Ladder et son erreur de prédiction (racine de l'erreur quadratique moyenne de prédiction) "
        "selon le modèle de Mack, avec l'extrapolation habituelle de Mack pour le dernier paramètre de variance. "
        "Donne la provision totale, l'erreur de prédiction totale et celle de l'année 2022.",
        valeurs={"provision_totale": ("provision_totale", REL), "erreur_prediction_totale": ("erreur_prediction_totale", REL),
                 "erreur_prediction_2022": ("erreur_prediction_derniere", REL)}),
    "v-mack-02": dict(
        famille="mack", source="R ChainLadder::MackChainLadder(est.sigma = \"Mack\")",
        texte=f"{TRI} (années d'origine 1 à 9, 9 périodes de développement).\n\n"
        "Calcule par le modèle de Mack l'erreur de prédiction de la provision Chain Ladder, avec l'extrapolation habituelle de Mack "
        "pour le dernier paramètre de variance. Exprime les erreurs en pourcentage de la provision correspondante (en décimal : 0,25 pour 25 %). "
        "Donne l'erreur relative totale, l'erreur relative de l'année d'origine 9 et le paramètre de variance sigma² de la période 1 à 2.",
        valeurs={"erreur_relative_totale": ("erreur_relative_totale", FACT),
                 "erreur_relative_origine_9": ("erreur_relative_derniere", FACT),
                 "sigma2_1_2": ("sigma2_1_2", REL)}),
    "v-odp-01": dict(
        famille="bootstrap_odp", source="R ChainLadder::glmReserve(var.power = 1, mse.method = \"formula\")",
        texte="Le fichier `triangle.csv` contient un triangle de sinistres cumulés (années d'origine 2006 à 2022, 17 périodes de développement).\n\n"
        "Ajuste un modèle de Poisson sur-dispersé (GLM log, effets origine et développement) aux montants incrémentaux, "
        "avec un paramètre de dispersion estimé par la statistique du khi-deux de Pearson divisée par les degrés de liberté. "
        "Calcule l'erreur de prédiction analytique de la provision. "
        "Donne le paramètre de dispersion, la provision totale, l'erreur de prédiction totale et celle de l'année 2022.",
        valeurs={"dispersion": ("dispersion", REL), "provision_totale": ("provision_totale", EURO),
                 "erreur_prediction_totale": ("erreur_prediction_totale", REL),
                 "erreur_prediction_2022": ("erreur_prediction_derniere", REL)}),
    "v-boot-01": dict(
        famille="bootstrap_odp", source="R ChainLadder::BootChainLadder(R = 20000, process.distr = \"od.pois\"), set.seed(42)",
        texte="Le fichier `triangle.csv` contient un triangle de sinistres cumulés (années d'origine 2011 à 2020, 10 périodes de développement).\n\n"
        "Réalise un bootstrap du modèle de Poisson sur-dispersé (résidus de Pearson ajustés par les degrés de liberté, 20 000 simulations, "
        "erreur de processus incluse) pour obtenir la distribution de la provision totale. "
        "Donne la moyenne de la provision totale simulée, son erreur de prédiction (écart-type) et son quantile à 95 %.",
        valeurs={k: (k, {"tolerance_relative": 0.05}) for k in ("provision_moyenne", "erreur_prediction", "quantile_95")}),
    "v-gpd-01": dict(
        famille="gpd", source="R evir::gpd et riskmeasures ; prime de tranche par integrate() sur la queue estimée",
        texte="Le fichier `sinistres_tempete.csv` contient 1 900 sinistres tempête de plus d'un million (en millions), une ligne par sinistre.\n\n"
        "Ajuste par maximum de vraisemblance une loi de Pareto généralisée aux excès au-delà du seuil de 6. "
        "Utilise l'estimateur de queue 1 − F(x) = (N_u / n)(1 + ξ (x − u) / σ)^(−1/ξ) pour en déduire le quantile à 99,9 % "
        "de la distribution des sinistres et la prime pure d'une tranche de réassurance 75 XS 25 (priorité 25, limite 100), par sinistre. "
        "Donne le nombre de dépassements, le paramètre de forme ξ, le quantile à 99,9 % et la prime pure de la tranche.",
        valeurs={"n_depassements": ("n_depassements", {"tolerance_absolue": 0}), "xi": ("xi", {"tolerance_absolue": 0.005}),
                 "quantile_999": ("quantile_999", {"tolerance_relative": 0.015}),
                 "prime_tranche": ("prime_tranche", {"tolerance_relative": 0.015})}),
    "v-gpd-02": dict(
        famille="gpd", source="R evir::gpd et riskmeasures",
        texte="Le fichier `sinistres_tempete.csv` contient 1 900 sinistres tempête de plus d'un million (en millions), une ligne par sinistre.\n\n"
        "Ajuste par maximum de vraisemblance une loi de Pareto généralisée aux excès au-delà du seuil de 2,5. "
        "Avec l'estimateur de queue 1 − F(x) = (N_u / n)(1 + ξ (x − u) / σ)^(−1/ξ), calcule les quantiles à 99,5 % et 99,99 % "
        "de la distribution des sinistres. Donne le nombre de dépassements, ξ, σ et les deux quantiles.",
        valeurs={"n_depassements": ("n_depassements", {"tolerance_absolue": 0}), "xi": ("xi", {"tolerance_absolue": 0.005}),
                 "sigma": ("sigma", {"tolerance_absolue": 0.02}),
                 "quantile_995": ("quantile_995", {"tolerance_relative": 0.015}),
                 "quantile_9999": ("quantile_9999", {"tolerance_relative": 0.015})}),
    "v-cred-01": dict(
        famille="credibilite", source="R actuar::cm(~entite), estimateurs sans biais par défaut",
        texte="Le fichier `experience.csv` donne, pour 6 portefeuilles et 10 années, le coût moyen des sinistres (colonne `Ratio`) "
        "et le nombre de sinistres (colonne `Poids`). Ignore la colonne `Cohorte`.\n\n"
        "Applique le modèle de crédibilité de Bühlmann-Straub avec les estimateurs sans biais usuels des paramètres de structure. "
        "Donne la prime collective, la variance entre portefeuilles, la variance intra-portefeuille, le facteur de crédibilité "
        "du portefeuille 3 et sa prime de crédibilité.",
        valeurs={"prime_collective": ("prime_collective", {"tolerance_absolue": 0.5}),
                 "variance_entre": ("variance_entre", REL), "variance_intra": ("variance_intra", REL),
                 "credibilite_3": ("credibilite_3", FACT), "prime_portefeuille_3": ("prime_entite_3", {"tolerance_absolue": 0.5})}),
    "v-cred-02": dict(
        famille="credibilite", source="R actuar::cm(~cohorte + cohorte:entite, method = \"iterative\")",
        texte="Le fichier `experience.csv` donne, pour 6 portefeuilles et 10 années, le coût moyen des sinistres (colonne `Ratio`) "
        "et le nombre de sinistres (colonne `Poids`). Les portefeuilles sont regroupés en deux cohortes "
        "(colonne `Cohorte` : A pour les portefeuilles 1 à 3, B pour 4 à 6).\n\n"
        "Applique le modèle de crédibilité hiérarchique à deux niveaux (Jewell), avec les pseudo-estimateurs itératifs des variances "
        "(type Bichsel-Straub). Donne la prime collective, la prime de crédibilité de la cohorte A, celle de la cohorte B "
        "et celle du portefeuille 5.",
        valeurs={k: (v, {"tolerance_absolue": 0.5}) for k, v in (
            ("prime_collective", "prime_collective"), ("prime_cohorte_A", "prime_cohorte_A"),
            ("prime_cohorte_B", "prime_cohorte_B"), ("prime_portefeuille_5", "prime_entite_5"))}),
    "v-vie-01": dict(
        famille="vie", source="R lifecontingencies (axn, Axn, Exn) sur une table Makeham exacte ; équation des primes explicite",
        texte="Un assureur émet un contrat mixte de 20 ans sur une tête de 45 ans. Capital de 50 000 payable en fin d'année du décès "
        "s'il survient dans les 20 ans, ou à l'échéance en cas de vie. Primes annuelles constantes payables d'avance pendant 20 ans.\n\n"
        "Base : loi de Makeham μ_x = A + B c^x avec A = 0,0002, B = 0,00004, c = 1,11 (pas de sélection), taux d'intérêt de 3 % "
        "effectif annuel. Frais initiaux : 40 % de la prime commerciale plus 150. Frais de renouvellement : 2,5 % de la prime "
        "commerciale plus 20 à chaque échéance de prime après la première.\n\n"
        "Calcule la prime commerciale, la prime pure, et les provisions nette (prime pure) et brute (prime commerciale, frais inclus) "
        "à la durée 10, juste avant le paiement de la prime.",
        valeurs={k: (k, CENT) for k in ("prime_commerciale", "prime_pure", "provision_nette_10", "provision_brute_10")}),
    "v-vie-02": dict(
        famille="vie", source="R lifecontingencies (axn, Axn) sur une table Makeham exacte",
        texte="Un assureur émet un contrat vie entière sur une tête de 55 ans. Capital de 80 000 payable en fin d'année du décès. "
        "Primes annuelles constantes payables d'avance pendant 20 ans au plus. Pas de frais.\n\n"
        "Base : loi de Makeham μ_x = A + B c^x avec A = 0,0002, B = 0,00004, c = 1,11 (pas de sélection), taux d'intérêt de 3,5 % "
        "effectif annuel.\n\n"
        "Calcule l'annuité viagère due ä_55 (vie entière), la prime pure annuelle et la provision nette aux durées 10 et 25, "
        "juste avant le paiement de la prime s'il y en a une.",
        valeurs={k: (k, CENT) for k in ("annuite_due_55", "prime_pure", "provision_nette_10", "provision_nette_25")}
        | {"annuite_due_55": ("annuite_due_55", {"tolerance_absolue": 0.0005})}),
    "v-scr-01": dict(
        famille="scr", source="agrégation formule standard écrite en R (generer_scr.R) : à recalculer par l'actuaire",
        texte="Un assureur vie utilise la formule standard Solvabilité II. Ses SCR bruts de sous-modules (en milliers d'euros) sont :\n\n"
        "- marché : taux d'intérêt 41 250 (le choc à la hausse est le plus défavorable), actions 63 800, immobilier 9 120, "
        "spread 27 400, change 3 350, concentration 5 100 ;\n"
        "- défaut de contrepartie : expositions de type 1 8 640, de type 2 1 270 ;\n"
        "- vie : mortalité 6 200, longévité 18 900, invalidité 0, cessation 31 500, frais 7 800, révision 2 100, catastrophe 4 300 ;\n"
        "- santé : 0 ; non-vie : 0 ; actifs incorporels : 0.\n\n"
        "Risque opérationnel : 6 450. Capacité d'absorption des pertes par les provisions techniques : −9 800 ; "
        "par les impôts différés : −21 400.\n\n"
        "Calcule le SCR marché, le SCR vie, le BSCR et le SCR.",
        valeurs={k: (k, EURO) for k in ("scr_marche", "scr_vie", "bscr", "scr")}),
    "v-scr-02": dict(
        famille="scr", source="agrégation formule standard écrite en R (generer_scr.R) : à recalculer par l'actuaire",
        texte="Un assureur non-vie utilise la formule standard Solvabilité II. Ses SCR bruts de sous-modules (en milliers d'euros) sont :\n\n"
        "- marché : taux d'intérêt 12 300 (le choc à la baisse est le plus défavorable), actions 25 600, immobilier 14 800, "
        "spread 9 700, change 2 200, concentration 0 ;\n"
        "- défaut de contrepartie : expositions de type 1 5 400, de type 2 3 900 ;\n"
        "- non-vie : primes et provisions 48 700, cessation 2 600 ; catastrophe : naturelle 21 500, réassurance non proportionnelle "
        "dommages 3 800, d'origine humaine 9 200, autres 4 100 ;\n"
        "- santé (module déjà agrégé) : 7 300 ; vie : 0 ; actifs incorporels : 0.\n\n"
        "Risque opérationnel : Op = 4 900 avant plafond (article 204), pas de contrats en unités de compte. "
        "Capacité d'absorption des pertes par les provisions techniques : 0 ; par les impôts différés : −15 600.\n\n"
        "Calcule le SCR catastrophe non-vie, le SCR non-vie, le BSCR et le SCR.",
        valeurs={k: (k, EURO) for k in ("scr_catastrophe_non_vie", "scr_non_vie", "bscr", "scr")}),
}


def main() -> None:
    corriges = {}
    for f in sorted((ICI / "corriges_r").glob("corriges_*.json")):
        corriges |= json.loads(f.read_text("utf-8"))
    for id_, s in SPEC.items():
        d = TACHES / id_
        d.mkdir(parents=True, exist_ok=True)
        cles = "{" + ", ".join(f'"{k}": 0' for k in s["valeurs"]) + "}"
        texte = s["texte"].replace(". Donne", ".\n\nDonne").replace(". Calcule", ".\n\nCalcule") \
            if "\n\nDonne" not in s["texte"] and "\n\nCalcule" not in s["texte"] else s["texte"]
        (d / "consigne.md").write_text(texte + "\n\n" + FIN.format(cles=cles), "utf-8")
        valeurs = []
        for cle, (src, tol) in s["valeurs"].items():
            v = corriges[id_][src]
            valeurs.append({"nom": cle, "attendu": round(float(v), 6), **tol})
        corrige = {"famille": s["famille"], "fiche_source": f"variante-{id_[2:]}", "source_r": s["source"],
                   "statut": "en_attente_validation", "valeurs": valeurs}
        (d / "corrige.yaml").write_text(yaml.safe_dump(corrige, allow_unicode=True, sort_keys=False), "utf-8")
    print(f"{len(SPEC)} tâches écrites dans {TACHES}")


if __name__ == "__main__":
    main()
