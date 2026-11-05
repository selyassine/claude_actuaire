"""Commande controler : audit de qualité d'un fichier de données, sans aucun calcul actuariel.

Le moteur signale et compte, il ne corrige rien : chaque traitement (compléter un trou, retirer
un doublon, exclure un facteur) reste une décision de l'actuaire, à passer ensuite en option
explicite de la méthode. Chaque anomalie a une gravité :
- bloquant : la méthode refusera le fichier tel quel ;
- alerte : le calcul passera, mais le résultat peut être faussé ;
- info : caractéristique à connaître.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter

import numpy as np

from .sortie import Resultat
from .triangle import libelle, lire_tableau, nombre_ou_nan

SEUIL_ATYPIQUE = 3.5  # écarts robustes (MAD normalisée) au-delà desquels un facteur individuel est signalé


def _anomalie(gravite: str, code: str, lieu: str, message: str, valeur=None) -> dict:
    return {"gravite": gravite, "code": code, "lieu": lieu, "valeur": valeur, "message": message}


def _vide(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in ("", "nan", "None")


def _cellules(df) -> tuple[np.ndarray, list[tuple[int, int, str]]]:
    """Valeurs numériques (NaN si vide ou texte) et liste des cellules en texte non numérique."""
    textes = []
    vals = np.full(df.shape, np.nan)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            v = df.iat[i, j]
            if _vide(v):
                continue
            x = nombre_ou_nan(v)
            if math.isnan(x) and str(v).strip().lower() not in ("nan", "na", "-"):
                textes.append((i, j, str(v)))
            vals[i, j] = x
    return vals, textes


# --- triangle ------------------------------------------------------------------------------

def controler_triangle(df, type_triangle: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    if df.shape[1] < 2 or df.shape[0] < 1:
        return [_anomalie("bloquant", "triangle_vide", "fichier",
                          "Il faut une colonne de libellés et au moins une période.")], {}
    origines = [libelle(v) for v in df.iloc[:, 0].tolist()]
    devs = [libelle(c) for c in df.columns[1:]]
    vals, textes = _cellules(df.iloc[:, 1:])
    lieu = lambda i, j: f"origine {origines[i]}, période {devs[j]}"  # noqa: E731

    for i, o in enumerate(origines):
        if o in ("", "nan", "None"):
            out.append(_anomalie("bloquant", "origine_sans_libelle", f"ligne {i + 2} du fichier",
                                 "Année d'origine sans libellé."))
    for o, n in Counter(origines).items():
        if n > 1 and o not in ("", "nan", "None"):
            out.append(_anomalie("bloquant", "origine_en_double", f"origine {o}", f"Origine présente {n} fois."))
    for d, n in Counter(devs).items():
        if n > 1:
            out.append(_anomalie("bloquant", "periode_en_double", f"période {d}", f"Période présente {n} fois."))
    if len(devs) < 2:
        out.append(_anomalie("bloquant", "une_seule_periode", "fichier", "Une seule période : aucun facteur estimable."))
    for i, j, t in textes:
        out.append(_anomalie("bloquant", "texte_non_numerique", lieu(i, j), "Valeur non numérique.", t))
    for i, j in zip(*np.where(np.isinf(vals)), strict=True):
        out.append(_anomalie("bloquant", "valeur_infinie", lieu(i, j), "Valeur infinie."))

    obs = ~np.isnan(vals)
    for i in range(len(origines)):
        idx = np.where(obs[i])[0]
        if idx.size == 0:
            out.append(_anomalie("bloquant", "ligne_vide", f"origine {origines[i]}", "Aucune valeur observée."))
            continue
        for j in range(idx[-1]):
            if not obs[i, j]:
                out.append(_anomalie("bloquant", "trou", lieu(i, j),
                                     "Cellule vide avant la dernière valeur observée de la ligne (0 si aucun paiement ?)."))
    longueurs = obs.sum(axis=1)
    if np.any(np.diff(longueurs) > 0):
        out.append(_anomalie("alerte", "forme_inattendue", "fichier",
                             "Le nombre de valeurs observées augmente d'une origine à la suivante : ordre des origines "
                             "ou cellules futures remplies ?"))

    finis = np.where(np.isfinite(vals), vals, np.nan)
    d = np.diff(finis, axis=1)
    part_croissante = float(np.mean(d[~np.isnan(d)] >= 0)) if np.any(~np.isnan(d)) else 1.0
    cumule = type_triangle == "cumule" or (type_triangle == "auto" and part_croissante >= 0.8)

    for i, j in zip(*np.where(finis < 0), strict=True):
        out.append(_anomalie("alerte", "valeur_negative", lieu(i, j),
                             "Montant négatif (recours, annulation ou erreur de saisie ?).", float(finis[i, j])))
    cum = finis if cumule else np.where(obs, np.nancumsum(np.nan_to_num(finis), axis=1), np.nan)
    if cumule:
        for i, j in zip(*np.where(d < 0), strict=True):
            out.append(_anomalie("alerte", "baisse_du_cumule", lieu(i, j + 1),
                                 "Le cumulé baisse par rapport à la période précédente.", float(d[i, j])))
    for i in range(cum.shape[0]):
        for j in range(cum.shape[1] - 1):
            a, b = cum[i, j], cum[i, j + 1]
            if a == 0 and not math.isnan(b) and b > 0:
                out.append(_anomalie("alerte", "zero_puis_positif", lieu(i, j + 1),
                                     "Cumulé nul puis positif : facteur individuel infini, exclu des moyennes.", float(b)))

    # facteurs individuels atypiques, colonne par colonne (médiane et MAD des log-facteurs)
    for j in range(cum.shape[1] - 1):
        a, b = cum[:, j], cum[:, j + 1]
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        if ok.sum() < 4:
            continue
        lf = np.log(b[ok] / a[ok])
        med = float(np.median(lf))
        mad = 1.4826 * float(np.median(np.abs(lf - med)))
        if mad <= 0:
            continue
        for k, i in enumerate(np.where(ok)[0]):
            z = (lf[k] - med) / mad
            if abs(z) > SEUIL_ATYPIQUE:
                out.append(_anomalie("alerte", "facteur_atypique", f"origine {origines[i]}, facteur {devs[j]}-{devs[j + 1]}",
                                     f"Facteur individuel {math.exp(lf[k]):.4g} contre une médiane de {math.exp(med):.4g} "
                                     f"({z:+.1f} écarts robustes) : à examiner, éventuellement à exclure (--exclure "
                                     f"'{origines[i]}@{devs[j]}-{devs[j + 1]}').", math.exp(lf[k])))

    resume = {"n_origines": len(origines), "n_periodes": len(devs), "cellules_observees": int(obs.sum()),
              "part_des_passages_croissants": part_croissante,
              "type_retenu_pour_les_controles": "cumule" if cumule else "incremental"}
    if type_triangle == "auto":
        out.append(_anomalie("info", "type_devine", "fichier",
                             f"Type supposé {resume['type_retenu_pour_les_controles']} ({part_croissante:.0%} de "
                             "passages croissants) : préciser --type pour des contrôles certains."))
    return out, resume


# --- sinistres individuels ---------------------------------------------------------------------

def controler_sinistres(df, colonne: str | None) -> tuple[list[dict], dict]:
    out: list[dict] = []
    if df.empty:
        return [_anomalie("bloquant", "fichier_vide", "fichier", "Aucune ligne.")], {}
    if colonne:
        if colonne not in df.columns:
            return [_anomalie("bloquant", "colonne_introuvable", "fichier", f"Colonne introuvable : {colonne}.")], {}
        col = colonne
    else:
        col = next((c for c in df.columns if np.isfinite([nombre_ou_nan(v) for v in df[c]]).mean() > 0.5), None)
        if col is None:
            return [_anomalie("bloquant", "aucune_colonne_numerique", "fichier", "Aucune colonne numérique.")], {}
    brut = df[col].tolist()
    x = np.array([nombre_ou_nan(v) for v in brut], dtype=float)
    for k, v in enumerate(brut):
        if math.isnan(x[k]) and not _vide(v):
            out.append(_anomalie("alerte", "texte_non_numerique", f"ligne {k + 2} du fichier",
                                 "Valeur non numérique, ignorée par gpd et tranche-xl.", str(v)))
    vides = sum(1 for v in brut if _vide(v))
    if vides:
        out.append(_anomalie("info", "cellules_vides", f"colonne {col}", f"{vides} cellule(s) vide(s), ignorée(s).", vides))
    for k in np.where(np.isinf(x))[0]:
        out.append(_anomalie("bloquant", "valeur_infinie", f"ligne {k + 2} du fichier", "Valeur infinie."))
    for k in np.where(x < 0)[0]:
        out.append(_anomalie("bloquant", "montant_negatif", f"ligne {k + 2} du fichier",
                             "Montant négatif : gpd et tranche-xl refusent le fichier.", float(x[k])))
    v = x[np.isfinite(x)]
    nuls = int((v == 0).sum())
    if nuls:
        out.append(_anomalie("alerte", "montants_nuls", f"colonne {col}",
                             f"{nuls} sinistre(s) de montant nul (sinistres classés sans suite ?).", nuls))
    doublons = {val: n for val, n in Counter(v[v > 0].tolist()).items() if n > 1}
    if doublons:
        top = sorted(doublons.items(), key=lambda t: (-t[1], -t[0]))[:10]
        out.append(_anomalie("alerte", "montants_repetes", f"colonne {col}",
                             f"{len(doublons)} montant(s) présent(s) plusieurs fois : double saisie ou forfait ? "
                             f"Exemples : " + ", ".join(f"{m:g} ({n} fois)" for m, n in top), len(doublons)))
    pos = np.sort(v[v > 0])
    if pos.size >= 2 and pos[-1] > 10 * pos[-2]:
        out.append(_anomalie("info", "maximum_isole", f"colonne {col}",
                             f"Le plus grand montant ({pos[-1]:g}) dépasse dix fois le suivant ({pos[-2]:g}) : vérifier "
                             "la saisie et l'unité ; il pèse fortement sur l'ajustement GPD.", float(pos[-1])))
    resume = {"colonne": str(col), "n_lignes": len(brut), "n_montants": int(v.size),
              "minimum": float(v.min()) if v.size else None, "maximum": float(v.max()) if v.size else None,
              "mediane": float(np.median(v)) if v.size else None}
    return out, resume


# --- primes --------------------------------------------------------------------------------

def controler_primes(df, origines_triangle: list[str] | None) -> tuple[list[dict], dict]:
    out: list[dict] = []
    if df.empty:
        return [_anomalie("bloquant", "fichier_vide", "fichier", "Aucune ligne.")], {}
    cols = {str(c).strip().lower(): c for c in df.columns}
    c_orig = cols.get("origine", df.columns[0])
    if "prime" not in cols:
        return [_anomalie("bloquant", "colonne_prime_absente", "fichier",
                          f"Colonne Prime absente (colonnes lues : {list(df.columns)}).")], {}
    origines = [libelle(v) for v in df[c_orig].tolist()]
    for k, o in enumerate(origines):
        if o in ("", "nan", "None"):
            out.append(_anomalie("bloquant", "origine_sans_libelle", f"ligne {k + 2} du fichier", "Origine sans libellé."))
    for o, n in Counter(origines).items():
        if n > 1 and o not in ("", "nan", "None"):
            out.append(_anomalie("bloquant", "origine_en_double", f"origine {o}", f"Origine présente {n} fois."))
    for nom in ("prime", "ratio", "ultime_a_priori"):
        if nom not in cols:
            continue
        for k, v in enumerate(df[cols[nom]].tolist()):
            x = nombre_ou_nan(v)
            ou = f"origine {origines[k]}, colonne {cols[nom]}"
            if _vide(v):
                if nom == "prime":
                    out.append(_anomalie("bloquant", "prime_manquante", ou, "Prime vide."))
            elif math.isnan(x):
                out.append(_anomalie("bloquant", "texte_non_numerique", ou, "Valeur non numérique.", str(v)))
            elif x < 0:
                out.append(_anomalie("bloquant", "valeur_negative", ou, "Valeur négative.", x))
            elif x == 0 and nom == "prime":
                out.append(_anomalie("alerte", "prime_nulle", ou, "Prime nulle : ultime a priori nul pour BF et Cape Cod.", x))
            elif nom == "ratio" and x > 3:
                out.append(_anomalie("alerte", "ratio_eleve", ou,
                                     "Ratio a priori supérieur à 300 % : pourcentage saisi au lieu d'une fraction ?", x))
    if origines_triangle is not None:
        manquantes = [o for o in origines_triangle if o not in origines]
        if manquantes:
            out.append(_anomalie("bloquant", "origines_manquantes", "fichier",
                                 f"Origines du triangle absentes du fichier de primes : {manquantes}.", manquantes))
        en_trop = [o for o in origines if o not in origines_triangle and o not in ("", "nan", "None")]
        if en_trop:
            out.append(_anomalie("alerte", "origines_en_trop", "fichier",
                                 f"Origines absentes du triangle (ignorées par les méthodes) : {en_trop}.", en_trop))
    resume = {"n_origines": len(origines), "colonnes": [str(c) for c in df.columns]}
    return out, resume


# --- commande ------------------------------------------------------------------------------

def args_controler(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True, help="Fichier à contrôler (CSV ou Excel).")
    sp.add_argument("--nature", required=True, choices=["triangle", "sinistres", "primes"],
                    help="Nature des données : triangle de développement, sinistres individuels ou primes par origine.")
    sp.add_argument("--type", choices=["cumule", "incremental", "auto"], default="auto",
                    help="Pour un triangle : cumulé ou incrémental (défaut auto, deviné).")
    sp.add_argument("--colonne", help="Pour des sinistres : colonne des montants (défaut : première colonne numérique).")
    sp.add_argument("--triangle", help="Pour des primes : triangle à confronter (origines manquantes ou en trop).")
    sp.add_argument("--feuille", default=None, help="Feuille Excel (nom ou numéro).")


def cmd_controler(args) -> Resultat:
    res = Resultat("controler", {}, options={"nature": args.nature, "type": args.type, "colonne": args.colonne})
    df = lire_tableau(args.entree, args.feuille, doublons_autorises=True)
    res.ajouter_entree(args.entree)
    doubles = sorted({str(c) for c in df.columns if list(df.columns).count(c) > 1})
    if args.nature == "triangle":
        anomalies, resume = controler_triangle(df, args.type)
    elif doubles:
        anomalies, resume = [_anomalie("bloquant", "colonne_en_double", "fichier", f"Colonne(s) en double : {doubles}.",
                                       doubles)], {}
    elif args.nature == "sinistres":
        anomalies, resume = controler_sinistres(df, args.colonne)
    else:
        origines = None
        if args.triangle:
            tri = lire_tableau(args.triangle)
            res.ajouter_entree(args.triangle, "triangle")
            origines = [libelle(v) for v in tri.iloc[:, 0].tolist()]
        anomalies, resume = controler_primes(df, origines)
    ordre = {"bloquant": 0, "alerte": 1, "info": 2}
    anomalies.sort(key=lambda a: ordre[a["gravite"]])
    decompte = {g: sum(1 for a in anomalies if a["gravite"] == g) for g in ordre}
    par_code = dict(Counter(a["code"] for a in anomalies))
    conclusion = "bloquant" if decompte["bloquant"] else ("a_examiner" if decompte["alerte"] else "pret")
    res.resultats = {"nature": args.nature, "conclusion": conclusion, "decompte": decompte, "par_code": par_code,
                     "resume": resume, "anomalies": anomalies}
    if decompte["bloquant"]:
        res.avertissements.append(f"{decompte['bloquant']} anomalie(s) bloquante(s) : les méthodes refuseront ce fichier "
                                  "tel quel. Le moteur ne corrige rien : la correction est une décision à documenter.")
    if decompte["alerte"]:
        res.avertissements.append(f"{decompte['alerte']} alerte(s) à examiner avant de calculer.")
    return res


COMMANDES = {
    "controler": (cmd_controler, "Audit de qualité d'un fichier (triangle, sinistres, primes) sans calcul : "
                  "anomalies bloquantes, alertes, informations ; rien n'est corrigé.", args_controler),
}
