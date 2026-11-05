"""Essai à blanc : le moteur seul répond aux 16 variantes, noté par noter.py.

Exécution : python banc_essai/variantes/essai_a_blanc.py
Les réponses du moteur sont écrites dans un dossier temporaire puis notées.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
from noter import noter  # noqa: E402

CLI = ICI.parents[1] / "skills" / "calcul-actuariel" / "scripts" / "cli.py"
T = ICI / "taches"
MAKEHAM = ["--modele", "makeham", "--A", "0.0002", "--B", "0.00004", "--c", "1.11"]

SCR_01 = {"marche": {"scenario_taux": "hausse", "taux": 41250, "actions": 63800, "immobilier": 9120, "spread": 27400,
                     "change": 3350, "concentration": 5100},
          "contrepartie": {"type1": 8640, "type2": 1270},
          "vie": {"mortalite": 6200, "longevite": 18900, "invalidite": 0, "cessation": 31500, "frais": 7800,
                  "revision": 2100, "catastrophe": 4300},
          "sante": 0, "non_vie": 0, "incorporels": 0, "operationnel": 6450,
          "ajustements": {"provisions_techniques": -9800, "impots_differes": -21400}}
SCR_02 = {"marche": {"scenario_taux": "baisse", "taux": 12300, "actions": 25600, "immobilier": 14800, "spread": 9700,
                     "change": 2200, "concentration": 0},
          "contrepartie": {"type1": 5400, "type2": 3900}, "vie": 0, "sante": 7300,
          "non_vie": {"primes_provisions": 48700, "cessation": 2600,
                      "catastrophe": {"naturelle": 21500, "reassurance_non_proportionnelle_dommages": 3800,
                                      "humaine": 9200, "autres": 4100}},
          "incorporels": 0, "operationnel": {"op": 4900, "exp_ul": 0},
          "ajustements": {"provisions_techniques": 0, "impots_differes": -15600}}


def moteur(*args) -> dict:
    sortie = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True, check=True)
    return json.loads(sortie.stdout)["resultats"]


def derniere(par_origine: dict, cle: str):
    return list(par_origine.values())[-1][cle]


def reponses(tmp: Path) -> dict:
    r = {}
    tri = lambda t: ["--entree", T / t / "triangle.csv", "--type", "cumule"]  # noqa: E731
    cl = moteur("chain-ladder", *tri("v-cl-01"))
    r["v-cl-01"] = {"provision_totale": cl["total"]["provision"], "ultime_2020": cl["par_origine"]["2020"]["ultime"],
                    "facteur_1_2": cl["facteurs"]["1-2"]}
    cl = moteur("chain-ladder", *tri("v-cl-02"), "--periode", 3)
    r["v-cl-02"] = {"provision_totale": cl["total"]["provision"], "cdf_1": cl["cdf_par_age"]["1"],
                    "facteur_1_2": cl["facteurs"]["1-2"]}
    bf = moteur("bf", *tri("v-bf-01"), "--primes", T / "v-bf-01" / "primes.csv")
    r["v-bf-01"] = {"ultime_total": bf["total"]["ultime"], "ibnr_total": bf["total"]["provision"],
                    "ultime_2022": bf["par_origine"]["2022"]["ultime"]}
    cc = moteur("cape-cod", *tri("v-bf-02"), "--primes", T / "v-bf-02" / "primes.csv")
    r["v-bf-02"] = {"ratio_cape_cod": cc["ratio_cape_cod"], "ultime_total": cc["total"]["ultime"],
                    "ibnr_total": cc["total"]["provision"]}
    m = moteur("mack", *tri("v-mack-01"))
    r["v-mack-01"] = {"provision_totale": m["total"]["provision"], "erreur_prediction_totale": m["total"]["erreur_prediction"],
                      "erreur_prediction_2022": m["par_origine"]["2022"]["erreur_prediction"]}
    m = moteur("mack", *tri("v-mack-02"))
    r["v-mack-02"] = {"erreur_relative_totale": m["total"]["erreur_prediction_pct"],
                      "erreur_relative_origine_9": m["par_origine"]["9"]["erreur_prediction_pct"],
                      "sigma2_1_2": m["sigma2"][0]}
    o = moteur("odp", *tri("v-odp-01"), "--dispersion", "pearson")
    r["v-odp-01"] = {"dispersion": o["phi"], "provision_totale": o["total"]["provision"],
                     "erreur_prediction_totale": o["total"]["erreur_prediction"],
                     "erreur_prediction_2022": o["par_origine"]["2022"]["erreur_prediction"]}
    b = moteur("bootstrap", *tri("v-boot-01"), "--simulations", 20000, "--graine", 2026)
    r["v-boot-01"] = {"provision_moyenne": b["total"]["moyenne"], "erreur_prediction": b["total"]["erreur_prediction"],
                      "quantile_95": b["total"]["quantiles"]["0.95"]}
    g = moteur("gpd", "--entree", T / "v-gpd-01" / "sinistres_tempete.csv", "--seuil", 6, "--quantiles", "0.999",
               "--tranche", "25,100")
    r["v-gpd-01"] = {"n_depassements": g["n_depassements"], "xi": g["xi"], "quantile_999": g["quantiles"]["0.999"],
                     "prime_tranche": g["tranches"]["25-100"]["prime_pure"]}
    g = moteur("gpd", "--entree", T / "v-gpd-02" / "sinistres_tempete.csv", "--seuil", 2.5, "--quantiles", "0.995,0.9999")
    r["v-gpd-02"] = {"n_depassements": g["n_depassements"], "xi": g["xi"], "sigma": g["sigma"],
                     "quantile_995": g["quantiles"]["0.995"], "quantile_9999": g["quantiles"]["0.9999"]}
    c = moteur("credibilite", "--entree", T / "v-cred-01" / "experience.csv", "--modele", "buhlmann-straub")
    e3 = next(e for e in c["entites"] if e["entite"] == "3")
    r["v-cred-01"] = {"prime_collective": c["prime_collective"], "variance_entre": c["variance_entre"],
                      "variance_intra": c["variance_intra"], "credibilite_3": e3["credibilite"],
                      "prime_portefeuille_3": e3["prime"]}
    c = moteur("credibilite", "--entree", T / "v-cred-02" / "experience.csv", "--modele", "hierarchique")
    e5 = next(e for e in c["entites"] if e["entite"] == "5")
    r["v-cred-02"] = {"prime_collective": c["prime_collective"], "prime_cohorte_A": c["cohortes"]["A"]["prime"],
                      "prime_cohorte_B": c["cohortes"]["B"]["prime"], "prime_portefeuille_5": e5["prime"]}
    v = moteur("tarif-vie", *MAKEHAM, "--taux", 0.03, "--type", "mixte", "--duree", 20, "--age", 45, "--capital", 50000,
               "--frais-initiaux-pct", 0.4, "--frais-initiaux-fixe", 150, "--frais-renouvellement-pct", 0.025,
               "--frais-renouvellement-fixe", 20, "--durees", 10)
    r["v-vie-01"] = {"prime_commerciale": v["prime_commerciale"], "prime_pure": v["prime_nette"],
                     "provision_nette_10": v["provisions"]["10"]["nette"], "provision_brute_10": v["provisions"]["10"]["brute"]}
    v = moteur("tarif-vie", *MAKEHAM, "--taux", 0.035, "--type", "vie-entiere", "--duree-primes", 20, "--age", 55,
               "--capital", 80000, "--durees", "10,25")
    s = moteur("survie", *MAKEHAM, "--taux", 0.035, "--age", 55)
    r["v-vie-02"] = {"annuite_due_55": s["annuite_due_vie_entiere"], "prime_pure": v["prime_nette"],
                     "provision_nette_10": v["provisions"]["10"]["nette"], "provision_nette_25": v["provisions"]["25"]["nette"]}
    for id_, donnees in (("v-scr-01", SCR_01), ("v-scr-02", SCR_02)):
        f = tmp / f"{id_}.json"
        f.write_text(json.dumps(donnees), "utf-8")
        s = moteur("scr", "--entree", f)
        r[id_] = {"bscr": s["bscr"], "scr": s["scr"]}
        if id_ == "v-scr-01":
            r[id_] |= {"scr_marche": s["modules"]["marche"], "scr_vie": s["modules"]["vie"]}
        else:
            r[id_] |= {"scr_catastrophe_non_vie": s["details"]["non_vie.catastrophe"]["scr"],
                       "scr_non_vie": s["modules"]["non_vie"]}
    return r


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for id_, res in reponses(tmp).items():
            dossier = tmp / "reponses" / "moteur" / id_
            dossier.mkdir(parents=True)
            (dossier / "1.md").write_text(f"```resultats\n{json.dumps(res)}\n```\n", "utf-8")
        print(json.dumps(noter(tmp / "reponses", T), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
