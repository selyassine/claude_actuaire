"""Commandes chain-ladder, bf et cape-cod de la ligne de commande."""

from __future__ import annotations

import argparse

import numpy as np

from .provisionnement import (
    bornhuetter_ferguson,
    cape_cod,
    chain_ladder,
    description_developpement,
    estimer_developpement,
)
from .sortie import Hypothese, Resultat
from .triangle import Triangle, _nombre, libelle, lire_tableau, lire_triangle


def args_triangle(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True, help="Fichier CSV ou Excel du triangle.")
    sp.add_argument("--feuille", default=None, help="Onglet Excel (nom ou numéro).")
    sp.add_argument("--type", choices=["auto", "cumule", "incremental"], default="auto",
                    help="Nature du triangle. auto = cumulé si toutes les lignes sont croissantes.")


def args_developpement(sp: argparse.ArgumentParser) -> None:
    args_triangle(sp)
    sp.add_argument("--moyenne", choices=["ponderee", "simple"], default="ponderee",
                    help="Moyenne des facteurs individuels (défaut : pondérée par les montants).")
    sp.add_argument("--periode", type=int, default=None,
                    help="N'utiliser que les N dernières années calendaires pour chaque facteur.")
    sp.add_argument("--queue", type=float, default=1.0, help="Facteur de queue (défaut 1).")
    sp.add_argument("--exclure", default="",
                    help="Facteurs individuels exclus, ex. '2003@1-2,2005@2-3' (origine@facteur).")
    sp.add_argument("--facteurs-imposes", default="",
                    help="Facteurs retenus par jugement, ex. '1-2=1.85,9-10=1.01'.")
    sp.add_argument("--arrondi", type=int, default=None,
                    help="Décimales des facteurs retenus et des CDF (ex. 3, convention Friedland). "
                         "Défaut : pleine précision.")


def args_bf(sp: argparse.ArgumentParser) -> None:
    args_developpement(sp)
    sp.add_argument("--primes", required=True,
                    help="CSV/Excel : colonnes Origine, Prime et, au choix, Ratio ou Ultime_a_priori.")
    sp.add_argument("--ratio", type=float, default=None,
                    help="Ratio sinistres/primes a priori unique (remplace la colonne Ratio).")


def args_cape_cod(sp: argparse.ArgumentParser) -> None:
    args_developpement(sp)
    sp.add_argument("--primes", required=True,
                    help="CSV/Excel : colonnes Origine, Prime (primes déjà ajustées si nécessaire).")


# --- préparation commune -------------------------------------------------------------------

def _triangle_cumule(args, res: Resultat) -> Triangle:
    tri = lire_triangle(args.entree, args.feuille)
    res.ajouter_entree(args.entree, "triangle")
    tri.verifier_forme()
    if args.type == "auto":
        cumule = tri.semble_cumule()
        res.hypotheses.append(Hypothese(
            "type_de_triangle", "cumule" if cumule else "incremental",
            "Détecté automatiquement : lignes croissantes = cumulé. Préciser --type en cas de doute.",
            "valeur par défaut"))
        part = tri.part_croissante()
        res.avertissements.append(
            f"Type de triangle deviné, détection incertaine ({part:.0%} des passages croissants) : "
            f"retenu {'cumulé' if cumule else 'incrémental'}. Préciser --type cumule ou --type incremental.")
    else:
        cumule = args.type == "cumule"
    res.avertissements.extend(tri.controles())
    return tri if cumule else tri.en_cumule()


def _indice_facteur(tri: Triangle, nom: str) -> int:
    noms = [f"{tri.developpements[k]}-{tri.developpements[k + 1]}" for k in range(tri.n_dev - 1)]
    if nom not in noms:
        raise ValueError(f"facteur inconnu : '{nom}'. Facteurs du triangle : {noms}")
    return noms.index(nom)


def _developpement(tri: Triangle, args, res: Resultat):
    if tri.n_dev < 2:
        raise ValueError("une seule période de développement : aucun facteur ne peut être estimé")
    exclusions = []
    for item in filter(None, (s.strip() for s in args.exclure.split(","))):
        if item.count("@") != 1:
            raise ValueError(f"--exclure : '{item}' n'est pas de la forme origine@facteur (ex. 2003@1-2)")
        origine, facteur = (x.strip() for x in item.split("@"))
        if origine not in tri.origines:
            raise ValueError(f"origine inconnue dans --exclure : '{origine}'")
        exclusions.append((tri.origines.index(origine), _indice_facteur(tri, facteur)))
    imposes = {}
    for item in filter(None, (s.strip() for s in args.facteurs_imposes.split(","))):
        if item.count("=") != 1:
            raise ValueError(f"--facteurs-imposes : '{item}' n'est pas de la forme facteur=valeur (ex. 1-2=1.85)")
        nom, val = item.split("=")
        k = _indice_facteur(tri, nom.strip())
        if k in imposes:
            raise ValueError(f"--facteurs-imposes : facteur '{nom.strip()}' imposé deux fois")
        imposes[k] = _nombre(val)

    dev = estimer_developpement(tri, args.moyenne, args.periode, exclusions, args.queue, imposes,
                                args.arrondi)
    res.options.update({
        "moyenne": args.moyenne, "periode": args.periode, "queue": args.queue,
        "exclure": args.exclure or None, "facteurs_imposes": args.facteurs_imposes or None,
        "arrondi": args.arrondi,
    })
    if args.arrondi is not None:
        res.hypotheses.append(Hypothese("arrondi", args.arrondi,
                                        "Facteurs et CDF arrondis avant projection (reproduit les exhibits publiés)."))
    res.hypotheses.append(Hypothese(
        "moyenne_des_facteurs", args.moyenne,
        "Pondérée = somme C(k+1) / somme C(k) ; simple = moyenne arithmétique des facteurs individuels.",
        "option utilisateur" if args.moyenne != "ponderee" else "valeur par défaut"))
    res.hypotheses.append(Hypothese(
        "facteur_de_queue", args.queue,
        "Aucun développement après la dernière période observée." if args.queue == 1.0
        else "Facteur de queue fourni par l'utilisateur.",
        "valeur par défaut" if args.queue == 1.0 else "option utilisateur"))
    if args.periode:
        res.hypotheses.append(Hypothese("periode", args.periode,
                                        f"Facteurs estimés sur les {args.periode} dernières années calendaires."))
    if exclusions:
        res.hypotheses.append(Hypothese("exclusions", args.exclure,
                                        "Facteurs individuels retirés par l'utilisateur ; justifier ce choix."))
    if imposes:
        res.hypotheses.append(Hypothese("facteurs_imposes", args.facteurs_imposes,
                                        "Facteurs retenus par jugement ; justifier l'écart avec les facteurs estimés."))
    if args.queue == 1.0 and not tri.observe()[0].all():
        res.avertissements.append("La première année d'origine n'est pas complète : un facteur de queue de 1 "
                                  "suppose qu'il n'y a plus de développement.")
    return dev


def _lire_primes(chemin: str, tri: Triangle, res: Resultat) -> dict[str, dict[str, float]]:
    """Lit le fichier de primes et le confronte au triangle avant tout calcul.

    Bloquant : colonne Prime absente, origine en double, origine du triangle absente.
    Signalé : origines du fichier absentes du triangle (ignorées)."""
    df = lire_tableau(chemin)
    if df.shape[0] == 0:
        raise ValueError("fichier de primes vide")
    cols = {str(c).strip().lower(): c for c in df.columns}
    if "origine" not in cols:
        cols["origine"] = df.columns[0]
    if "prime" not in cols:
        raise ValueError(f"colonne Prime absente du fichier de primes (colonnes lues : {list(df.columns)})")
    out: dict[str, dict[str, float]] = {}
    for _, ligne in df.iterrows():
        o = libelle(ligne[cols["origine"]])
        if o in out:
            raise ValueError(f"origine '{o}' en double dans le fichier de primes")
        out[o] = {k: _nombre(ligne[cols[k]]) for k in ("prime", "ratio", "ultime_a_priori") if k in cols}
    manquantes = [o for o in tri.origines if o not in out]
    if manquantes:
        raise ValueError(f"origines du triangle absentes du fichier de primes : {manquantes} "
                         f"(origines du fichier : {list(out)})")
    en_trop = [o for o in out if o not in tri.origines]
    if en_trop:
        res.avertissements.append(f"Origines du fichier de primes absentes du triangle, ignorées : {en_trop}.")
    return out


def _controle_unites(tri: Triangle, dev, primes: np.ndarray, res: Resultat) -> None:
    """Alerte si les sinistres projetés et les primes ne semblent pas dans la même unité
    (ex. triangle en milliers d'euros, primes en euros)."""
    ult = chain_ladder(tri, dev)["par_origine"]
    ratios = np.array([ult[o]["ultime"] for o in tri.origines]) / primes
    ratios = ratios[np.isfinite(ratios) & (ratios > 0)]
    if ratios.size and not 0.02 <= float(np.median(ratios)) <= 50:
        res.avertissements.append(
            f"Ratio médian ultime Chain Ladder / prime de {float(np.median(ratios)):.4g} : vérifier que le "
            "triangle et les primes sont dans la même unité monétaire et sur les mêmes périodes.")


# --- commandes ----------------------------------------------------------------------------

def cmd_chain_ladder(args) -> Resultat:
    res = Resultat("chain-ladder", {})
    tri = _triangle_cumule(args, res)
    dev = _developpement(tri, args, res)
    res.resultats = {**description_developpement(tri, dev), **chain_ladder(tri, dev)}
    return res


def cmd_bf(args) -> Resultat:
    res = Resultat("bf", {})
    tri = _triangle_cumule(args, res)
    dev = _developpement(tri, args, res)
    primes = _lire_primes(args.primes, tri, res)
    res.ajouter_entree(args.primes, "primes")
    if all("prime" in primes[o] and np.isfinite(primes[o]["prime"]) and primes[o]["prime"] > 0
           for o in tri.origines):
        _controle_unites(tri, dev, np.array([primes[o]["prime"] for o in tri.origines]), res)
    a_priori = []
    for o in tri.origines:
        p = primes[o]
        if args.ratio is not None:
            a_priori.append(p["prime"] * args.ratio)
        elif not np.isnan(p.get("ultime_a_priori", np.nan)):
            a_priori.append(p["ultime_a_priori"])
        elif not np.isnan(p.get("ratio", np.nan)):
            a_priori.append(p["prime"] * p["ratio"])
        else:
            raise ValueError(f"pas de ratio ni d'ultime a priori pour l'origine {o} (utiliser --ratio)")
    res.options["ratio"] = args.ratio
    res.hypotheses.append(Hypothese(
        "sinistralite_a_priori",
        args.ratio if args.ratio is not None else "fichier de primes",
        "Ultime a priori = prime × ratio a priori ; c'est un choix de jugement à documenter.",
        "option utilisateur"))
    res.resultats = {**description_developpement(tri, dev),
                     **bornhuetter_ferguson(tri, dev, np.array(a_priori))}
    return res


def cmd_cape_cod(args) -> Resultat:
    res = Resultat("cape-cod", {})
    tri = _triangle_cumule(args, res)
    dev = _developpement(tri, args, res)
    primes = _lire_primes(args.primes, tri, res)
    res.ajouter_entree(args.primes, "primes")
    p = np.array([primes[o]["prime"] for o in tri.origines])
    if np.all(np.isfinite(p) & (p > 0)):
        _controle_unites(tri, dev, p, res)
    res.hypotheses.append(Hypothese(
        "primes", "fichier de primes",
        "Le ratio Cape Cod suppose des primes au même niveau tarifaire et de tendance ; "
        "les ajuster avant l'appel si nécessaire.", "donnée d'entrée"))
    res.resultats = {**description_developpement(tri, dev), **cape_cod(tri, dev, p)}
    return res


COMMANDES = {
    "chain-ladder": (cmd_chain_ladder, "Chain Ladder : facteurs, ultimes et provisions.", args_developpement),
    "bf": (cmd_bf, "Bornhuetter-Ferguson à partir d'une sinistralité a priori.", args_bf),
    "cape-cod": (cmd_cape_cod, "Cape Cod : sinistralité a priori estimée sur toutes les années.", args_cape_cod),
}
