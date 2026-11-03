"""Agrégation du SCR en formule standard Solvabilité II (règlement délégué (UE) 2015/35).

Le moteur agrège des SCR déjà calculés (chocs appliqués par ailleurs) : sous-modules -> modules
-> BSCR -> SCR. Il ne calcule pas les chocs eux-mêmes.

Matrices de corrélation recopiées du règlement délégué 2015/35 :
- BSCR : annexe IV, point 1 ;
- marché : article 164, paramètre A = 0 si le capital pour le risque de taux vient du choc à la hausse,
  A = 0,5 s'il vient du choc à la baisse ;
- défaut de contrepartie : article 200, SCR = racine(T1² + 1,5 T1 T2 + T2²) ;
- vie : article 136 ;
- santé : article 144 (SLT, NSLT, catastrophe), santé SLT : article 151, santé NSLT : article 146
  (primes et provisions, cessation, sans corrélation), catastrophe santé : article 160 (somme quadratique) ;
- non-vie : article 114 ; catastrophe non-vie : article 119 ;
- risque opérationnel : article 204, min(0,3 BSCR ; Op) + 0,25 Exp_ul.
"""

from __future__ import annotations

import math

import numpy as np

BSCR = (["marche", "contrepartie", "vie", "sante", "non_vie"],
        [[1, .25, .25, .25, .25],
         [.25, 1, .25, .25, .5],
         [.25, .25, 1, .25, 0],
         [.25, .25, .25, 1, 0],
         [.25, .5, 0, 0, 1]])


def marche(A: float):
    return (["taux", "actions", "immobilier", "spread", "change", "concentration"],
            [[1, A, A, A, .25, 0],
             [A, 1, .75, .75, .25, 0],
             [A, .75, 1, .5, .25, 0],
             [A, .75, .5, 1, .25, 0],
             [.25, .25, .25, .25, 1, 0],
             [0, 0, 0, 0, 0, 1]])


VIE = (["mortalite", "longevite", "invalidite", "cessation", "frais", "revision", "catastrophe"],
       [[1, -.25, .25, 0, .25, 0, .25],
        [-.25, 1, 0, .25, .25, .25, 0],
        [.25, 0, 1, 0, .5, 0, .25],
        [0, .25, 0, 1, .5, 0, .25],
        [.25, .25, .5, .5, 1, .5, .25],
        [0, .25, 0, 0, .5, 1, 0],
        [.25, 0, .25, .25, .25, 0, 1]])

SANTE_SLT = (VIE[0][:6], [ligne[:6] for ligne in VIE[1][:6]])
SANTE = (["slt", "nslt", "catastrophe"], [[1, .5, .25], [.5, 1, .25], [.25, .25, 1]])
SANTE_NSLT = (["primes_provisions", "cessation"], [[1, 0], [0, 1]])
SANTE_CAT = (["accident_de_masse", "concentration", "pandemie"], np.eye(3).tolist())
NON_VIE = (["primes_provisions", "cessation", "catastrophe"], [[1, 0, .25], [0, 1, 0], [.25, 0, 1]])
SOURCES = {
    "bscr": "annexe IV", "marche": "article 164", "contrepartie": "article 200", "vie": "article 136",
    "sante": "article 144", "sante.slt": "article 151", "sante.nslt": "article 146",
    "sante.catastrophe": "article 160", "non_vie": "article 114", "non_vie.catastrophe": "article 119",
    "operationnel": "article 204",
}


def agreger(valeurs: dict, structure, chemin: str, details: dict) -> float:
    noms, matrice = structure
    inconnus = set(valeurs) - set(noms)
    if inconnus:
        raise ValueError(f"{chemin} : sous-module(s) inconnu(s) {sorted(inconnus)} ; attendus : {noms}")
    v = np.array([float(valeurs.get(n, 0.0) or 0.0) for n in noms])
    if np.any(v < 0):
        raise ValueError(f"{chemin} : un SCR de sous-module est négatif")
    total = float(math.sqrt(max(v @ np.array(matrice, dtype=float) @ v, 0.0)))
    details[chemin] = {"somme": float(v.sum()), "diversification": total - float(v.sum()), "scr": total,
                       "sous_modules": {n: float(x) for n, x in zip(noms, v)}}
    return total


def _module(nom: str, entree, details: dict, avertissements: list) -> float:
    """Un module est un nombre (SCR déjà agrégé) ou un dictionnaire de sous-modules."""
    if entree is None:
        return 0.0
    if isinstance(entree, (int, float)):
        if entree < 0:
            raise ValueError(f"{nom} : SCR négatif")
        return float(entree)
    if not isinstance(entree, dict):
        raise ValueError(f"{nom} : nombre ou dictionnaire attendu")
    e = dict(entree)
    if nom == "marche":
        scenario = e.pop("scenario_taux", None)
        if scenario not in ("hausse", "baisse"):
            if float(e.get("taux", 0) or 0) > 0:
                raise ValueError("marche : préciser scenario_taux = 'hausse' ou 'baisse' (article 164, paramètre A)")
            scenario = "hausse"
        return agreger(e, marche(0.0 if scenario == "hausse" else 0.5), nom, details)
    if nom == "contrepartie":
        inconnus = set(e) - {"type1", "type2"}
        if inconnus:
            raise ValueError(f"contrepartie : clés inconnues {sorted(inconnus)} ; attendues type1, type2")
        t1, t2 = float(e.get("type1", 0) or 0), float(e.get("type2", 0) or 0)
        total = math.sqrt(t1 * t1 + 1.5 * t1 * t2 + t2 * t2)
        details[nom] = {"somme": t1 + t2, "diversification": total - t1 - t2, "scr": total,
                        "sous_modules": {"type1": t1, "type2": t2}}
        return total
    if nom == "vie":
        return agreger(e, VIE, nom, details)
    if nom == "sante":
        sous = {}
        for cle, struct in (("slt", SANTE_SLT), ("nslt", SANTE_NSLT), ("catastrophe", SANTE_CAT)):
            x = e.pop(cle, None)
            sous[cle] = agreger(x, struct, f"sante.{cle}", details) if isinstance(x, dict) else float(x or 0)
        if e:
            raise ValueError(f"sante : clés inconnues {sorted(e)} ; attendues slt, nslt, catastrophe")
        return agreger(sous, SANTE, nom, details)
    if nom == "non_vie":
        cat = e.get("catastrophe")
        if isinstance(cat, dict):
            inconnus = set(cat) - {"naturelle", "reassurance_non_proportionnelle_dommages", "humaine", "autres"}
            if inconnus:
                raise ValueError(f"non_vie.catastrophe : clés inconnues {sorted(inconnus)}")
            nat = float(cat.get("naturelle", 0) or 0) + float(cat.get("reassurance_non_proportionnelle_dommages", 0) or 0)
            mm, autres = float(cat.get("humaine", 0) or 0), float(cat.get("autres", 0) or 0)
            total_cat = math.sqrt(nat ** 2 + mm ** 2 + autres ** 2)
            somme = nat + mm + autres
            details["non_vie.catastrophe"] = {"somme": somme, "diversification": total_cat - somme, "scr": total_cat,
                                              "sous_modules": {k: float(v or 0) for k, v in cat.items()}}
            e["catastrophe"] = total_cat
        return agreger(e, NON_VIE, nom, details)
    raise ValueError(f"module inconnu : {nom}")


def calculer_scr(donnees: dict) -> tuple[dict, list[str]]:
    avert: list[str] = []
    attendus = {"marche", "contrepartie", "vie", "sante", "non_vie", "incorporels", "operationnel", "ajustements"}
    inconnus = set(donnees) - attendus
    if inconnus:
        raise ValueError(f"clés inconnues {sorted(inconnus)} ; attendues : {sorted(attendus)}")
    details: dict = {}
    modules = {n: _module(n, donnees.get(n), details, avert) for n in BSCR[0]}
    agreger(modules, BSCR, "bscr", details)
    incorporels = float(donnees.get("incorporels", 0) or 0)
    bscr = details["bscr"]["scr"] + incorporels

    op_entree = donnees.get("operationnel", 0) or 0
    if isinstance(op_entree, dict):
        inconnus = set(op_entree) - {"op", "exp_ul"}
        if inconnus:
            raise ValueError(f"operationnel : clés inconnues {sorted(inconnus)} ; attendues op, exp_ul")
        op_base = float(op_entree.get("op", 0) or 0)
        exp_ul = float(op_entree.get("exp_ul", 0) or 0)
        op = min(0.3 * bscr, op_base) + 0.25 * exp_ul
        details["operationnel"] = {"op": op_base, "plafond_30_pct_bscr": 0.3 * bscr, "exp_ul": exp_ul, "scr": op}
    else:
        op = float(op_entree)

    aj = dict(donnees.get("ajustements") or {})
    connus = {"provisions_techniques", "impots_differes", "fonds_cantonnes", "capital_supplementaire"}
    inconnus = set(aj) - connus
    if inconnus:
        raise ValueError(f"ajustements : clés inconnues {sorted(inconnus)} ; attendues : {sorted(connus)}")
    adj_pt = float(aj.get("provisions_techniques", 0) or 0)
    adj_id = float(aj.get("impots_differes", 0) or 0)
    if adj_pt > 0 or adj_id > 0:
        raise ValueError("les capacités d'absorption (provisions_techniques, impots_differes) se saisissent en négatif")
    fc = float(aj.get("fonds_cantonnes", 0) or 0)
    add_on = float(aj.get("capital_supplementaire", 0) or 0)
    scr_hors_add_on = bscr + fc + op + adj_pt + adj_id
    return {
        "modules": modules,
        "diversification_bscr": details["bscr"]["diversification"],
        "incorporels": incorporels,
        "bscr": bscr,
        "operationnel": op,
        "ajustements": {"provisions_techniques": adj_pt, "impots_differes": adj_id, "fonds_cantonnes": fc},
        "scr_hors_capital_supplementaire": scr_hors_add_on,
        "capital_supplementaire": add_on,
        "scr": scr_hors_add_on + add_on,
        "details": details,
    }, avert
