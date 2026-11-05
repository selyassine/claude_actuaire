"""Commande gpd de la ligne de commande."""

from __future__ import annotations

import argparse

import numpy as np

from .extremes import excedent_moyen, gpd_seuil
from .sortie import Hypothese, Resultat
from .triangle import lire_tableau, nombre_ou_nan


def _liste(texte: str | None) -> list[float]:
    return [float(t) for t in str(texte).replace(";", ",").split(",") if t.strip()] if texte else []


def args_gpd(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True, help="CSV ou Excel des montants de sinistres (une ligne par sinistre).")
    sp.add_argument("--colonne", help="Nom de la colonne des montants (défaut : première colonne numérique).")
    sp.add_argument("--feuille", default=None, help="Feuille Excel (nom ou numéro).")
    sp.add_argument("--seuil", type=float, required=True, help="Seuil u : la GPD est ajustée aux excès au-delà de u.")
    sp.add_argument("--quantiles", default="0.99,0.995,0.999",
                    help="Niveaux de quantile, séparés par des virgules (défaut 0.99,0.995,0.999).")
    sp.add_argument("--tranche", action="append", default=[],
                    help="Tranche de réassurance 'priorité,limite' (répétable), ex. --tranche 50,200.")
    sp.add_argument("--test-ajustement", type=int, default=0,
                    help="Nombre de simulations du bootstrap paramétrique donnant la p-valeur d'Anderson-Darling "
                         "(ex. 999). Défaut 0 : statistiques seules, sans p-valeur.")
    sp.add_argument("--graine", type=int, default=2026, help="Graine du test d'ajustement (défaut 2026).")
    sp.add_argument("--diagnostic-seuils",
                    help="Seuils où calculer l'excès moyen empirique (aide au choix du seuil), ex. 3,5,10,20.")


def _lire_pertes(args, res: Resultat) -> np.ndarray:
    df = lire_tableau(args.entree, args.feuille)
    if args.colonne:
        if args.colonne not in df.columns:
            raise ValueError(f"colonne introuvable : {args.colonne}")
        col = args.colonne
    else:
        col = next((c for c in df.columns
                    if np.isfinite([nombre_ou_nan(v) for v in df[c]]).mean() > 0.9), None)
        if col is None:
            raise ValueError("aucune colonne numérique trouvée dans le fichier")
    x = np.array([nombre_ou_nan(v) for v in df[col]], dtype=float)
    res.ajouter_entree(args.entree)
    manquants = int(np.isnan(x).sum())
    if manquants:
        res.avertissements.append(f"{manquants} valeur(s) non numérique(s) ignorée(s) dans la colonne {col}.")
    x = x[~np.isnan(x)]
    if np.any(x < 0):
        raise ValueError("des montants sont négatifs : la GPD s'applique à des pertes positives")
    res.hypotheses.append(Hypothese("colonne", str(col), "Colonne des montants utilisée.",
                                    "option utilisateur" if args.colonne else "valeur par défaut"))
    return x


def cmd_gpd(args) -> Resultat:
    quantiles = _liste(args.quantiles)
    tranches = []
    for t in args.tranche:
        v = _liste(t)
        if len(v) != 2:
            raise ValueError(f"tranche mal formée : {t} (attendu 'priorité,limite')")
        tranches.append((v[0], v[1]))
    res = Resultat("gpd", {}, options={"seuil": args.seuil, "quantiles": quantiles,
                                       "tranches": [list(t) for t in tranches],
                                       "test_ajustement": args.test_ajustement, "graine": args.graine})
    x = _lire_pertes(args, res)
    r = gpd_seuil(x, args.seuil, quantiles, tranches, args.test_ajustement, args.graine)
    res.hypotheses += [
        Hypothese("seuil", args.seuil,
                  "Choix de jugement : seuil assez haut pour que la GPD s'applique, assez bas pour garder "
                  "des données. À justifier (excès moyen linéaire, stabilité de xi selon le seuil)."),
        Hypothese("estimation", "maximum de vraisemblance sur les excès",
                  "McNeil (1997) ; erreurs types asymptotiques (1 + xi)/racine(N_u) pour xi.", "méthode"),
        Hypothese("queue", "1 - F(x) = (N_u / n) (1 + xi (x - u) / sigma)^(-1/xi)",
                  "Part empirique des dépassements multipliée par la survie GPD (McNeil 1997, section 3.5) ; "
                  "les quantiles et les primes de tranche sont conditionnels au seuil de collecte des données.",
                  "méthode"),
    ]
    if r["n_depassements"] < 50:
        res.avertissements.append(f"Seulement {r['n_depassements']} dépassements : estimations très incertaines.")
    if r["xi"] <= -0.5:
        res.avertissements.append("xi <= -0,5 : les erreurs types asymptotiques ne sont pas valables.")
    if r["xi"] >= 1:
        res.avertissements.append("xi >= 1 : espérance infinie au-delà du seuil ; seules les tranches bornées ont un prix fini.")
    if not r["convergence"]:
        res.avertissements.append("Optimisation non concluante (non convergée ou optima différents selon le point de départ, "
                                  "voir diagnostic_optimisation) : vérifier les résultats.")
    for p, q in r["quantiles"].items():
        if q > 2 * r["maximum_observe"]:
            res.avertissements.append(f"Le quantile {p} ({q:.4g}) dépasse le double du maximum observé : extrapolation forte.")
    lo, hi = r["intervalle_95_xi_profil"]
    if lo is None or hi is None:
        res.avertissements.append("Intervalle profilé de xi ouvert d'un côté : la donnée ne contraint pas xi.")
    elif r["intervalle_95_xi_wald"] and abs((hi - lo) - (r["intervalle_95_xi_wald"][1] - r["intervalle_95_xi_wald"][0])) \
            > 0.25 * (hi - lo):
        res.avertissements.append("Intervalles de Wald et profilé de xi très différents : préférer l'intervalle profilé.")
    p_ad = r["ajustement"].get("p_valeur_anderson_darling")
    if p_ad is not None and p_ad < 0.05:
        res.avertissements.append(f"Test d'Anderson-Darling : p = {p_ad:.3f} < 5 %, la GPD s'ajuste mal au-delà de ce "
                                  "seuil ; essayer un seuil plus haut.")
    if args.diagnostic_seuils:
        r["excedent_moyen"] = excedent_moyen(x, _liste(args.diagnostic_seuils))
    res.resultats = r
    return res


COMMANDES = {
    "gpd": (cmd_gpd, "GPD au-delà d'un seuil (McNeil 1997) : xi, sigma, quantiles, primes de tranche.", args_gpd),
}
