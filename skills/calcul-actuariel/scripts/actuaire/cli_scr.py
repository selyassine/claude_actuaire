"""Commande scr de la ligne de commande."""

from __future__ import annotations

import argparse
import json

from .scr import SOURCES, calculer_scr
from .sortie import Hypothese, Resultat


def args_scr(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True,
                    help="Fichier JSON : modules (marche, contrepartie, vie, sante, non_vie), incorporels, "
                         "operationnel, ajustements. Chaque module est un nombre ou un dictionnaire de sous-modules.")


def cmd_scr(args) -> Resultat:
    with open(args.entree, encoding="utf-8") as f:
        donnees = json.load(f)
    res = Resultat("scr", {}, options={})
    res.ajouter_entree(args.entree)
    r, avert = calculer_scr(donnees)
    res.avertissements += avert
    res.hypotheses.append(Hypothese(
        "matrices", {k: f"règlement délégué (UE) 2015/35, {v}" for k, v in SOURCES.items()},
        "Agrégation par matrices de corrélation de la formule standard ; les SCR des sous-modules "
        "(chocs) sont des données d'entrée, non recalculés.", "méthode"))
    marche = donnees.get("marche")
    if isinstance(marche, dict) and marche.get("scenario_taux"):
        res.hypotheses.append(Hypothese(
            "scenario_taux", marche["scenario_taux"],
            "Article 164 : A = 0 si le capital de taux vient du choc à la hausse, 0,5 s'il vient du choc à la baisse.",
            "donnée d'entrée"))
    if isinstance(donnees.get("operationnel"), dict):
        res.hypotheses.append(Hypothese(
            "operationnel", "min(0,3 BSCR ; Op) + 0,25 Exp_ul",
            "Article 204 ; Op (composantes primes et provisions) et Exp_ul sont des données d'entrée.", "méthode"))
    res.resultats = r
    return res


COMMANDES = {
    "scr": (cmd_scr, "Agrégation du SCR en formule standard (règlement délégué 2015/35) : modules, BSCR, SCR.", args_scr),
}
