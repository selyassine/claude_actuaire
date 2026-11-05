"""Commandes mack, odp et bootstrap de la ligne de commande."""

from __future__ import annotations

import argparse

from .cli_provisionnement import _triangle_cumule, args_triangle
from .sortie import Hypothese, Resultat
from .stochastique import bootstrap_odp, mack, odp_analytique


def args_mack(sp: argparse.ArgumentParser) -> None:
    args_triangle(sp)
    sp.add_argument("--sigma-dernier", choices=["mack", "precedent"], default="mack",
                    help="Extrapolation du dernier sigma² : formule de Mack (1993, défaut) "
                         "ou égal au précédent.")


def args_odp(sp: argparse.ArgumentParser) -> None:
    args_triangle(sp)
    sp.add_argument("--dispersion", choices=["pearson", "deviance"], default=None,
                    help="Estimation du paramètre de dispersion phi (défaut : Pearson, avec un avertissement : "
                         "les deux conventions existent dans la littérature, à préciser).")


def args_bootstrap(sp: argparse.ArgumentParser) -> None:
    args_triangle(sp)
    sp.add_argument("--simulations", type=int, default=10000, help="Nombre de simulations (défaut 10 000).")
    sp.add_argument("--graine", type=int, default=2026, help="Graine aléatoire, pour un résultat reproductible.")


def _hyp_commune(res: Resultat) -> None:
    res.hypotheses.append(Hypothese(
        "facteurs", "moyenne pondérée sur toutes les années, sans queue",
        "Les formules publiées supposent les facteurs Chain Ladder standards ; aucune option de jugement "
        "(exclusion, période, queue) n'est appliquée.", "méthode"))


def cmd_mack(args) -> Resultat:
    res = Resultat("mack", {}, options={"sigma_dernier": args.sigma_dernier})
    tri = _triangle_cumule(args, res)
    _hyp_commune(res)
    res.hypotheses.append(Hypothese(
        "sigma2_dernier", args.sigma_dernier,
        "Dernier sigma² non estimable (une seule observation) : "
        + ("min(s⁴(n-2)/s²(n-3), s²(n-3), s²(n-2)) selon Mack (1993)." if args.sigma_dernier == "mack"
           else "égal à l'avant-dernier.")))
    res.resultats = mack(tri, args.sigma_dernier)
    return res


def cmd_odp(args) -> Resultat:
    explicite = args.dispersion is not None
    args.dispersion = args.dispersion or "pearson"
    res = Resultat("odp", {}, options={"dispersion": args.dispersion})
    if not explicite:
        res.avertissements.append(
            "Dispersion non précisée : Pearson retenu par défaut. La déviance donne un autre phi "
            "(England et Verrall 2002, tableau 3) ; préciser --dispersion pearson ou deviance selon la consigne.")
    tri = _triangle_cumule(args, res)
    _hyp_commune(res)
    res.hypotheses.append(Hypothese(
        "dispersion", args.dispersion,
        "Paramètre phi estimé par " + ("le khi² de Pearson" if args.dispersion == "pearson" else "la déviance")
        + " / degrés de liberté (observations - 2n + 1).",
        "option utilisateur" if explicite else "valeur par défaut"))
    res.resultats = odp_analytique(tri, args.dispersion)
    return res


def cmd_bootstrap(args) -> Resultat:
    res = Resultat("bootstrap", {}, options={"simulations": args.simulations, "graine": args.graine})
    tri = _triangle_cumule(args, res)
    _hyp_commune(res)
    res.hypotheses.append(Hypothese(
        "procedure", "England et Verrall (2002), annexe 3",
        "Résidus de Pearson ajustés (facteur racine(n/ddl)), rééchantillonnage, Chain Ladder sur les "
        "pseudo-données, puis loi de processus Gamma de moyenne m et de variance phi × m.", "méthode"))
    r = bootstrap_odp(tri, args.simulations, args.graine)
    if r["cellules_moyenne_negative"]:
        res.avertissements.append(
            f"{r['cellules_moyenne_negative']} cellules futures simulées avaient une moyenne négative ou nulle : "
            "aucun aléa de processus n'y a été ajouté.")
    if args.simulations < 5000:
        res.avertissements.append("Moins de 5 000 simulations : les quantiles élevés sont instables.")
    res.resultats = r
    return res


COMMANDES = {
    "mack": (cmd_mack, "Mack (1993) : erreur de prédiction de Chain Ladder.", args_mack),
    "odp": (cmd_odp, "Poisson sur-dispersé : erreur de prédiction analytique.", args_odp),
    "bootstrap": (cmd_bootstrap, "Bootstrap ODP (England et Verrall 2002) : distribution de la provision.",
                  args_bootstrap),
}
