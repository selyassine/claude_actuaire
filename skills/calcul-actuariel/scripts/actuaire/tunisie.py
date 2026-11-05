"""Réglementation tunisienne des assurances : marge de solvabilité et tables de mortalité TD99 / TV99.

Sources (Code des assurances, version consolidée, Imprimerie Officielle de la République Tunisienne) :
- article 58 : éléments constitutifs de la marge de solvabilité ;
- article 58 bis (loi n° 2002-37 du 1er avril 2002) : montant minimum réglementaire ;
- arrêté du ministre des finances du 27 février 2001, article 5 (modifié le 5 janvier 2009) :
  tables TD99 (décès, hommes) et TV99 (survie, femmes), plafonds de taux et de frais.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

FICHIER_TABLES = Path(__file__).with_name("donnees") / "tables_tunisie_99.csv"
TABLES = {"td99": "TD99", "tv99": "TV99"}
ALIAS = {"tm99": "td99"}  # l'arrêté nomme « TM99 » la table imprimée sous le nom « TD99 »

ARTICLE_58_BIS = "Code des assurances, art. 58 bis (loi n° 2002-37 du 1er avril 2002)"


def _nombre(d: dict, cle: str, chemin: str, defaut: float | None = None) -> float:
    if cle not in d or d[cle] is None:
        if defaut is not None:
            return defaut
        raise ValueError(f"{chemin}.{cle} manquant")
    v = d[cle]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{chemin}.{cle} doit être un nombre fini (reçu {v!r})")
    return float(v)


def _rapport(net: float, brut: float, plancher: float, quoi: str, avert: list[str]) -> dict:
    if brut <= 0:
        raise ValueError(f"{quoi} brut doit être strictement positif")
    if net < 0:
        raise ValueError(f"{quoi} net ne peut pas être négatif")
    brut_rapport = net / brut
    if brut_rapport > 1:
        avert.append(f"{quoi} : le net ({net:g}) dépasse le brut ({brut:g}) ; rapport {brut_rapport:.4f} > 1 conservé.")
    retenu = max(brut_rapport, plancher)
    return {"net": net, "brut": brut, "rapport": brut_rapport, "plancher": plancher, "rapport_retenu": retenu,
            "plancher_applique": brut_rapport < plancher}


def marge_non_vie(d: dict, avert: list[str]) -> dict:
    """Art. 58 bis a : max(base primes, base sinistres)."""
    c = "non_vie"
    primes = _nombre(d, "primes_emises_acceptees", c)
    retenues = _nombre(d, "primes_retenues", c)
    if primes <= 0:
        raise ValueError("non_vie.primes_emises_acceptees doit être strictement positif")
    rp = _rapport(retenues, primes, 0.5, "primes", avert)
    base_primes = 0.20 * primes * rp["rapport_retenu"]

    s = d.get("sinistres")
    if not isinstance(s, dict):
        raise ValueError("non_vie.sinistres manquant (règlements, PSAP de début et de fin, recours encaissés)")
    cs = "non_vie.sinistres"
    assurance_credit = bool(d.get("assurance_credit", False))
    n_attendu = 7 if assurance_credit else 3
    regl = s.get("reglements")
    if not isinstance(regl, list) or not regl:
        raise ValueError(f"{cs}.reglements : liste des règlements de chaque exercice attendue")
    for v in regl:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{cs}.reglements : valeur non numérique {v!r}")
    if len(regl) != n_attendu:
        raise ValueError(f"{cs}.reglements : {len(regl)} exercice(s) fourni(s), {n_attendu} attendus "
                         + ("(assurance crédit à titre principal : 7 derniers exercices)" if assurance_credit
                            else "(3 derniers exercices)"))
    psap_fin = _nombre(s, "psap_fin", cs)
    psap_debut = _nombre(s, "psap_debut", cs)
    recours = _nombre(s, "recours_encaisses", cs, 0.0)
    charge = float(sum(regl)) + psap_fin - psap_debut - recours
    charge_moyenne = charge / n_attendu
    if charge_moyenne < 0:
        avert.append("Charge moyenne de sinistres négative : la base sinistres est ramenée à 0.")
    if "charge_nette" in s:
        net = _nombre(s, "charge_nette", cs)
        rs = _rapport(net, charge, 0.5, "charge de sinistres", avert) if charge > 0 else None
    else:
        raise ValueError(f"{cs}.charge_nette manquant : charge de la période après cessions et rétrocessions, "
                         "même définition que la charge brute")
    if rs is None:
        rs = {"net": net, "brut": charge, "rapport": None, "plancher": 0.5, "rapport_retenu": 0.5,
              "plancher_applique": True}
    base_sinistres = 0.25 * max(charge_moyenne, 0.0) * rs["rapport_retenu"]
    return {
        "base_primes": {"primes_emises_acceptees": primes, "taux": 0.20, "rapport_retention": rp,
                        "montant": base_primes},
        "base_sinistres": {
            "reglements": [float(v) for v in regl], "psap_fin": psap_fin, "psap_debut": psap_debut,
            "recours_encaisses": recours, "charge_periode": charge, "nombre_exercices": n_attendu,
            "charge_moyenne_annuelle": charge_moyenne, "taux": 0.25, "rapport_retention": rs,
            "montant": base_sinistres},
        "methode_retenue": "primes" if base_primes >= base_sinistres else "sinistres",
        "minimum": max(base_primes, base_sinistres),
    }


def marge_vie(d: dict, avert: list[str]) -> dict:
    """Art. 58 bis b : 4 % des PM + 3 pour mille des capitaux sous risque."""
    c = "vie"
    pm_b = _nombre(d, "provisions_mathematiques_brutes", c)
    pm_n = _nombre(d, "provisions_mathematiques_nettes", c)
    rpm = _rapport(pm_n, pm_b, 0.85, "provisions mathématiques", avert)
    if "capitaux_sous_risque_bruts" in d:
        csr_b = _nombre(d, "capitaux_sous_risque_bruts", c)
        origine = "donnée d'entrée"
    else:
        csr_b = _nombre(d, "capitaux_assures_bruts", c) - pm_b
        origine = "capitaux assurés bruts − provisions mathématiques brutes"
    csr_n = _nombre(d, "capitaux_sous_risque_nets", c)
    if csr_b < 0:
        raise ValueError(f"capitaux sous risque bruts négatifs ({csr_b:g})")
    if csr_b == 0:
        rcsr = {"net": csr_n, "brut": 0.0, "rapport": None, "plancher": 0.5, "rapport_retenu": 0.5,
                "plancher_applique": True}
    else:
        rcsr = _rapport(csr_n, csr_b, 0.5, "capitaux sous risque", avert)
    a = 0.04 * pm_b * rpm["rapport_retenu"]
    b = 0.003 * csr_b * rcsr["rapport_retenu"]
    return {
        "provisions_mathematiques": {"brutes": pm_b, "taux": 0.04, "rapport_retention": rpm, "montant": a},
        "capitaux_sous_risque": {"bruts": csr_b, "origine": origine, "taux": 0.003, "rapport_retention": rcsr,
                                 "montant": b},
        "minimum": a + b,
    }


ELEMENTS_58 = {
    "capital_libere": +1.0,
    "capital_non_libere": +0.5,
    "reserves": +1.0,
    "benefices_reportes": +1.0,
    "plus_values_agreees": +1.0,
    "autres_elements_agrees": +1.0,
    "provision_equilibrage_takaful": +1.0,
    "pertes": -1.0,
    "actifs_incorporels": -1.0,
}


def marge_constituee(d: dict) -> dict:
    """Art. 58 : somme des éléments fournis ; le moteur ne les évalue pas."""
    inconnus = sorted(set(d) - set(ELEMENTS_58))
    if inconnus:
        raise ValueError(f"marge_constituee : éléments inconnus {inconnus} ; attendus {sorted(ELEMENTS_58)}")
    detail = {}
    total = 0.0
    for k, signe in ELEMENTS_58.items():
        if k in d:
            v = _nombre(d, k, "marge_constituee")
            if v < 0:
                raise ValueError(f"marge_constituee.{k} : montant positif attendu (le signe est appliqué par le moteur)")
            detail[k] = {"montant": v, "coefficient": signe, "contribution": signe * v}
            total += signe * v
    return {"elements": detail, "total": total}


def calculer_marge(donnees: dict) -> tuple[dict, list[str]]:
    avert: list[str] = []
    if not isinstance(donnees, dict):
        raise ValueError("le fichier d'entrée doit contenir un objet JSON")
    inconnus = sorted(set(donnees) - {"non_vie", "vie", "marge_constituee", "unite", "commentaire"})
    if inconnus:
        raise ValueError(f"clés inconnues {inconnus} ; attendues : non_vie, vie, marge_constituee")
    if "non_vie" not in donnees and "vie" not in donnees:
        raise ValueError("au moins une des activités non_vie ou vie est requise")
    r: dict = {}
    minimum = 0.0
    if "non_vie" in donnees:
        r["non_vie"] = marge_non_vie(donnees["non_vie"], avert)
        minimum += r["non_vie"]["minimum"]
    if "vie" in donnees:
        r["vie"] = marge_vie(donnees["vie"], avert)
        minimum += r["vie"]["minimum"]
    r["activite"] = ("mixte" if len({"non_vie", "vie"} & set(donnees)) == 2
                     else ("non_vie" if "non_vie" in donnees else "vie"))
    r["minimum_reglementaire"] = minimum
    if "marge_constituee" in donnees:
        mc = marge_constituee(donnees["marge_constituee"])
        r["marge_constituee"] = mc
        r["excedent"] = mc["total"] - minimum
        r["taux_couverture"] = mc["total"] / minimum if minimum > 0 else None
        if minimum > 0 and mc["total"] < minimum:
            avert.append(f"Marge constituée ({mc['total']:g}) inférieure au minimum réglementaire ({minimum:g}).")
    return r, avert


# --- Tables de mortalité TD99 / TV99 ---------------------------------------------------------

def lire_tables() -> dict[str, dict[int, tuple[int, float | None]]]:
    """{'TD99': {age: (lx, qx publié en fraction ou None)}, 'TV99': {...}}."""
    out: dict[str, dict[int, tuple[int, float | None]]] = {"TD99": {}, "TV99": {}}
    with FICHIER_TABLES.open(encoding="utf-8") as f:
        for ligne in csv.DictReader(f, delimiter=";"):
            age = int(ligne["Age"])
            for nom in out:
                lx = ligne[f"lx_{nom}"]
                if lx == "":
                    continue
                q = ligne[f"qx_pct_{nom}_publie"]
                out[nom][age] = (int(lx), float(q) / 100.0 if q else None)
    return out


def qx_table(nom: str, source: str = "lx") -> dict[int, float]:
    """q_x de la table : source 'lx' (1 − l_{x+1}/l_x) ou 'publie' (colonne imprimée, arrondie à 0,01 %)."""
    cle = ALIAS.get(nom.lower(), nom.lower())
    if cle not in TABLES:
        raise ValueError(f"table inconnue {nom!r} ; disponibles : TD99 (alias TM99), TV99")
    t = lire_tables()[TABLES[cle]]
    ages = sorted(a for a, (lx, _) in t.items() if lx > 0)
    if source == "lx":
        return {a: 1.0 - t[a + 1][0] / t[a][0] for a in ages}
    if source == "publie":
        q = {a: t[a][1] for a in ages}
        if any(v is None for v in q.values()):
            raise ValueError("q_x publié manquant pour un âge de la table")
        return q  # type: ignore[return-value]
    raise ValueError(f"source de q_x inconnue {source!r} (lx ou publie)")
