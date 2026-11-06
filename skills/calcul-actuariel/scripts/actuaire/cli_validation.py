"""Commande comparer : rapport d'écarts entre un modèle externe et un calcul archivé du moteur.

C'est la validation par réplication indépendante : le moteur, testé sur des publications, sert
de deuxième implémentation ; chaque écart désigne une erreur, une hypothèse divergente ou un
arrondi. Le moteur ne recalcule rien ici : il lit sa propre sortie JSON (dont l'empreinte est
vérifiée) et les valeurs du modèle externe, puis classe chaque ligne.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from typing import Any

import numpy as np

from .sortie import Resultat, verifier_empreinte
from .triangle import lire_tableau, nombre_ou_nan

FACTEURS_CONNUS = {1000.0: "milliers", 1e6: "millions", 0.001: "milliers (inverse)", 1e-6: "millions (inverse)",
                   100.0: "pourcentages", 0.01: "pourcentages (inverse)"}


def lire_chemin(d: Any, chemin: str) -> Any:
    """Suit un chemin pointé ; une clé contenant un point (ex. quantile '0.995') est reconnue."""
    obj = d
    morceaux = chemin.split(".")
    i = 0
    while i < len(morceaux):
        if isinstance(obj, list):
            try:
                obj = obj[int(morceaux[i])]
            except (ValueError, IndexError):
                raise KeyError(chemin) from None
            i += 1
            continue
        if not isinstance(obj, dict):
            raise KeyError(chemin)
        for j in range(len(morceaux), i, -1):
            cle = ".".join(morceaux[i:j])
            if cle in obj:
                obj = obj[cle]
                i = j
                break
        else:
            raise KeyError(chemin)
    return obj


def chemins_numeriques(obj: Any, prefixe: str = "") -> list[str]:
    """Tous les chemins des valeurs numériques d'un bloc de résultats."""
    if isinstance(obj, dict):
        return [c for k, v in obj.items() for c in chemins_numeriques(v, f"{prefixe}.{k}" if prefixe else str(k))]
    if isinstance(obj, list):
        return [c for i, v in enumerate(obj) for c in chemins_numeriques(v, f"{prefixe}.{i}")]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return [prefixe]
    return []


def demi_unite_publiee(texte: str) -> float | None:
    """Demi-unité de la dernière décimale écrite (« 1 234,5 » -> 0,05) : un écart inférieur est un arrondi."""
    s = str(texte).strip().replace(" ", "").replace(" ", "").replace(" ", "")
    if re.search(r"[eE]", s):
        return None
    m = re.fullmatch(r"[-+]?[\d.,]*?[.,](\d+)", s)
    if m:
        return 0.5 * 10.0 ** (-len(m.group(1)))
    if re.fullmatch(r"[-+]?\d+", s):
        return 0.5
    return None


def _charger_sortie(chemin: str) -> dict:
    with open(chemin, encoding="utf-8") as f:
        sortie = json.load(f)
    if not isinstance(sortie, dict) or "resultats" not in sortie or "methode" not in sortie:
        raise ValueError("ce fichier n'est pas une sortie JSON du moteur (blocs 'methode' et 'resultats' attendus)")
    verifier_empreinte(sortie, "la sortie du moteur")
    return sortie


def args_comparer(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--resultats", required=True, help="Sortie JSON d'une commande du moteur (fichier enregistré).")
    sp.add_argument("--externe", help="CSV ou Excel du modèle externe : colonnes 'chemin' et 'valeur' (et, en option, "
                                      "'libelle' et 'tolerance_relative').")
    sp.add_argument("--feuille", default=None, help="Feuille Excel du fichier externe (nom ou numéro).")
    sp.add_argument("--tolerance-relative", type=float, default=1e-6,
                    help="Écart relatif accepté (défaut 1e-6, soit la précision numérique : un modèle qui applique "
                         "la même méthode doit reproduire le moteur à ce niveau). Élargir seulement avec une "
                         "justification, de préférence ligne par ligne (colonne 'tolerance_relative').")
    sp.add_argument("--tolerance-absolue", type=float, default=0.0,
                    help="Écart absolu toujours accepté, pour les valeurs proches de zéro (défaut 0).")
    sp.add_argument("--lister", action="store_true",
                    help="Liste les chemins numériques disponibles dans la sortie du moteur, sans comparer.")


def _colonne(df, nom: str) -> str | None:
    for c in df.columns:
        if str(c).strip().lower() == nom:
            return c
    return None


def cmd_comparer(args) -> Resultat:
    if args.tolerance_relative < 0 or args.tolerance_absolue < 0:
        raise ValueError("les tolérances doivent être positives ou nulles")
    sortie = _charger_sortie(args.resultats)
    res = Resultat("comparer", {}, options={"tolerance_relative": args.tolerance_relative,
                                            "tolerance_absolue": args.tolerance_absolue})
    res.ajouter_entree(args.resultats, "sortie_moteur")
    disponibles = chemins_numeriques(sortie["resultats"], "resultats")
    if args.lister:
        res.resultats = {"methode_comparee": sortie["methode"], "chemins_disponibles": disponibles}
        return res
    if not args.externe:
        raise ValueError("--externe est obligatoire (ou --lister pour voir les chemins disponibles)")

    df = lire_tableau(args.externe, args.feuille)
    c_chemin, c_valeur = _colonne(df, "chemin"), _colonne(df, "valeur")
    if c_chemin is None or c_valeur is None:
        raise ValueError("le fichier externe doit avoir les colonnes 'chemin' et 'valeur'")
    c_libelle, c_tol = _colonne(df, "libelle"), _colonne(df, "tolerance_relative")
    res.ajouter_entree(args.externe, "modele_externe")
    if df.empty:
        raise ValueError("le fichier externe ne contient aucune ligne")

    lignes, vus, rapports = [], set(), []
    for _, row in df.iterrows():
        chemin = str(row[c_chemin]).strip()
        if chemin in ("", "nan", "None"):
            raise ValueError("une ligne du fichier externe n'a pas de chemin")
        complet = chemin if chemin.startswith("resultats.") else f"resultats.{chemin}"
        if complet in vus:
            raise ValueError(f"chemin en double dans le fichier externe : {chemin}")
        vus.add(complet)
        ligne: dict[str, Any] = {"chemin": complet, "libelle": None if c_libelle is None else str(row[c_libelle]),
                                 "valeur_moteur": None, "valeur_externe": None, "ecart_absolu": None,
                                 "ecart_relatif": None}
        tol_rel = args.tolerance_relative
        if c_tol is not None and str(row[c_tol]).strip() not in ("", "nan", "None"):
            tol_rel = nombre_ou_nan(row[c_tol])
            if not (math.isfinite(tol_rel) and tol_rel >= 0):
                raise ValueError(f"tolérance invalide pour {chemin} : {row[c_tol]}")
        ligne["tolerance_relative"] = tol_rel
        externe = nombre_ou_nan(row[c_valeur])
        try:
            moteur = lire_chemin(sortie, complet)
        except KeyError:
            ligne["statut"] = "chemin_absent"
            lignes.append(ligne)
            continue
        if not math.isfinite(externe):
            ligne.update(statut="valeur_externe_invalide", valeur_moteur=moteur)
            lignes.append(ligne)
            continue
        if moteur is None or isinstance(moteur, bool) or not isinstance(moteur, (int, float)):
            ligne.update(statut="non_numerique_moteur", valeur_externe=externe)
            lignes.append(ligne)
            continue
        ecart = externe - float(moteur)
        rel = ecart / abs(moteur) if moteur != 0 else (0.0 if ecart == 0 else None)
        ligne.update(valeur_moteur=moteur, valeur_externe=externe, ecart_absolu=ecart, ecart_relatif=rel)
        demi = demi_unite_publiee(row[c_valeur]) if isinstance(row[c_valeur], str) else None
        if abs(ecart) <= max(args.tolerance_absolue, tol_rel * abs(moteur)):
            ligne["statut"] = "conforme"
        elif demi is not None and abs(ecart) <= demi * (1 + 1e-9):
            ligne["statut"] = "arrondi"
        else:
            ligne["statut"] = "ecart"
            if moteur != 0 and externe != 0:
                rapports.append(externe / float(moteur))
        lignes.append(ligne)

    compte = {s: sum(1 for li in lignes if li["statut"] == s)
              for s in ("conforme", "arrondi", "ecart", "chemin_absent", "valeur_externe_invalide",
                        "non_numerique_moteur")}
    rels = [abs(li["ecart_relatif"]) for li in lignes if li["ecart_relatif"] is not None]
    probleme = len(lignes) - compte["conforme"] - compte["arrondi"]
    res.resultats = {
        "methode_comparee": sortie["methode"],
        "version_moteur_comparee": sortie.get("moteur", {}).get("version"),
        "empreinte_resultats_comparee": sortie.get("empreinte_resultats"),
        "conclusion": "conforme" if probleme == 0 else "ecarts_a_analyser",
        "n_lignes": len(lignes),
        "decompte": compte,
        "ecart_relatif_max": max(rels) if rels else None,
        "chemins_moteur_non_compares": len([c for c in disponibles if c not in vus]),
        "lignes": lignes,
    }
    if sortie.get("statut") not in ("ok", None):
        res.avertissements.append(f"La sortie du moteur comparée a le statut '{sortie.get('statut')}' : lire ses "
                                  "avertissements avant de conclure.")
    if compte["chemin_absent"]:
        res.avertissements.append(f"{compte['chemin_absent']} chemin(s) introuvable(s) dans la sortie du moteur : "
                                  "utiliser --lister pour voir les chemins disponibles.")
    if compte["valeur_externe_invalide"]:
        res.avertissements.append(f"{compte['valeur_externe_invalide']} valeur(s) externe(s) non numérique(s).")
    if len(rapports) >= 3:
        med = float(np.median(rapports))
        if all(abs(r / med - 1) < 0.01 for r in rapports):
            nom = next((v for k, v in FACTEURS_CONNUS.items() if abs(med / k - 1) < 0.01), None)
            if nom:
                res.avertissements.append(f"Tous les écarts suivent un même facteur {med:.6g} : unités différentes "
                                          f"({nom}) plutôt qu'une erreur de calcul.")
            elif abs(med + 1) < 0.01:
                res.avertissements.append("Tous les écarts sont des changements de signe : convention de signe différente.")
            else:
                res.avertissements.append(f"Tous les écarts suivent un même facteur {med:.6g} : hypothèse commune "
                                          "divergente (taux, exposition, mise à l'échelle) plutôt qu'erreurs isolées.")
    if compte["ecart"]:
        res.avertissements.append(f"{compte['ecart']} écart(s) au-delà de la tolérance : chacun est une erreur, une "
                                  "hypothèse différente ou une spécification ambiguë, à expliquer avant validation.")
    return res


COMMANDES = {
    "comparer": (cmd_comparer, "Rapport d'écarts entre un modèle externe et une sortie archivée du moteur "
                 "(validation par réplication indépendante).", args_comparer),
}
