"""Commande credibilite de la ligne de commande."""

from __future__ import annotations

import argparse

import numpy as np

from .credibilite import buhlmann_straub, hachemeister, hierarchique
from .sortie import Hypothese, Resultat
from .triangle import _nombre, libelle, lire_tableau


def args_credibilite(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True,
                    help="CSV ou Excel au format long : colonnes Entite, Periode, Ratio, et Poids (sauf Bühlmann), "
                         "Cohorte (modèle hiérarchique).")
    sp.add_argument("--feuille", default=None, help="Feuille Excel (nom ou numéro).")
    sp.add_argument("--modele", choices=["buhlmann", "buhlmann-straub", "hierarchique", "regression"],
                    default="buhlmann-straub")
    sp.add_argument("--estimateur", choices=["sans-biais", "iteratif"],
                    help="Estimateur des variances entre entités (défaut : sans-biais, itératif pour hiérarchique).")
    sp.add_argument("--periode-future", type=float,
                    help="Régression : valeur du temps à prévoir (défaut : dernière période + 1).")
    sp.add_argument("--barycentre", action="store_true",
                    help="Régression : intercept au barycentre du temps (Bühlmann et Gisler 2005, section 8.4).")


def _colonne(df, nom: str, obligatoire: bool = True):
    cols = {str(c).strip().lower(): c for c in df.columns}
    if nom.lower() in cols:
        return cols[nom.lower()]
    if obligatoire:
        raise ValueError(f"colonne {nom} introuvable (colonnes : {list(df.columns)})")
    return None


def _lire(args, res: Resultat, avec_poids: bool):
    df = lire_tableau(args.entree, args.feuille)
    ce, cp, cr = _colonne(df, "Entite"), _colonne(df, "Periode"), _colonne(df, "Ratio")
    cw = _colonne(df, "Poids", obligatoire=avec_poids)
    cc = _colonne(df, "Cohorte", obligatoire=args.modele == "hierarchique")
    if df.shape[0] == 0:
        raise ValueError("fichier d'expérience vide")
    entites = list(dict.fromkeys(libelle(v) for v in df[ce]))
    if any(e in ("", "nan", "None") for e in entites):
        raise ValueError("une ligne n'a pas d'entité")
    valeurs_periodes = [_nombre(v) for v in df[cp]]
    if any(not np.isfinite(v) for v in valeurs_periodes):
        raise ValueError("une ligne a une période vide ou non numérique")
    periodes = sorted(set(valeurs_periodes))
    ie, ip = {e: k for k, e in enumerate(entites)}, {p: k for k, p in enumerate(periodes)}
    X = np.full((len(entites), len(periodes)), np.nan)
    W = np.full_like(X, np.nan) if cw is not None else None
    cohorte = {}
    for _, ligne in df.iterrows():
        i, t = ie[libelle(ligne[ce])], ip[_nombre(ligne[cp])]
        if not np.isnan(X[i, t]):
            raise ValueError(f"doublon : entité {entites[i]}, période {periodes[t]:g}")
        X[i, t] = _nombre(ligne[cr])
        if W is not None:
            W[i, t] = _nombre(ligne[cw])
        if cc is not None:
            c = libelle(ligne[cc])
            if c in ("", "nan", "None"):
                raise ValueError(f"entité {entites[i]} : cohorte vide")
            if cohorte.setdefault(i, c) != c:
                raise ValueError(f"entité {entites[i]} rattachée à deux cohortes ({cohorte[i]} et {c})")
    res.ajouter_entree(args.entree)
    manquants = int(np.isnan(X).sum())
    if manquants:
        res.avertissements.append(f"{manquants} couple(s) entité-période sans observation : ignorés.")
    coh = [cohorte.get(i) for i in range(len(entites))] if cc is not None else None
    return entites, np.array(periodes), X, W, coh


def cmd_credibilite(args) -> Resultat:
    est = args.estimateur or ("iteratif" if args.modele == "hierarchique" else "sans-biais")
    res = Resultat("credibilite", {}, options={"modele": args.modele, "estimateur": est,
                                               "barycentre": args.barycentre,
                                               "periode_future": args.periode_future})
    entites, periodes, X, W, coh = _lire(args, res, avec_poids=args.modele != "buhlmann")
    if args.modele == "buhlmann":
        W = None
    if args.modele in ("buhlmann", "buhlmann-straub"):
        r = buhlmann_straub(X, W, est)
        for e, d in zip(entites, r["entites"], strict=True):
            d["entite"] = e
        res.hypotheses.append(Hypothese(
            "modele", "Bühlmann" if W is None else "Bühlmann-Straub",
            "Prime = z_i × moyenne de l'entité + (1 - z_i) × prime collective, z_i = w_i / (w_i + s²/a).", "méthode"))
    elif args.modele == "hierarchique":
        r = hierarchique(X, W, coh, est)
        for e, d in zip(entites, r["entites"], strict=True):
            d["entite"] = e
        res.hypotheses.append(Hypothese(
            "modele", "hiérarchique à deux niveaux (Jewell)",
            "Crédibilité au niveau cohorte, puis au niveau entité autour de la prime de sa cohorte.", "méthode"))
    else:
        futur = args.periode_future if args.periode_future is not None else float(periodes.max() + 1)
        r = hachemeister(X, W, periodes, futur, args.barycentre, est)
        for e, d in zip(entites, r["entites"], strict=True):
            d["entite"] = e
        r["periode_future"] = futur
        res.hypotheses.append(Hypothese(
            "modele", "régression de Hachemeister, tendance linéaire",
            ("Intercept au barycentre du temps et coefficients traités séparément (Bühlmann et Gisler 2005, 8.4) : "
             "la prime reste entre la droite individuelle et la droite collective."
             if args.barycentre else
             "Modèle d'origine (1975) : la droite de crédibilité peut sortir de l'intervalle entre droites "
             "individuelle et collective ; envisager --barycentre."), "méthode"))
        if args.periode_future is None:
            res.hypotheses.append(Hypothese("periode_future", futur, "Dernière période + 1.", "valeur par défaut"))
    res.hypotheses.append(Hypothese(
        "estimateur", est,
        "Sans biais : Bühlmann et Gisler (2005), tronqué à 0. Itératif : point fixe de Bichsel-Straub "
        "(pseudo-estimateur).", "option utilisateur" if args.estimateur else "valeur par défaut"))
    for d in r.get("entites", []):
        if isinstance(d.get("credibilite"), float) and d["credibilite"] == 0.0:
            res.avertissements.append("Variance entre entités estimée nulle : toutes les primes valent la prime collective.")
            break
    if X.shape[0] < 5:
        res.avertissements.append("Moins de 5 entités : les variances structurelles sont très imprécises.")
    res.resultats = r
    return res


COMMANDES = {
    "credibilite": (cmd_credibilite,
                    "Crédibilité : Bühlmann, Bühlmann-Straub, hiérarchique (Jewell), régression de Hachemeister.",
                    args_credibilite),
}
