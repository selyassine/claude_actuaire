"""Commande gpd de la ligne de commande."""

from __future__ import annotations

import argparse

import numpy as np

from .extremes import excedent_moyen, gpd_seuil
from .reassurance import tarif_tranche_xl
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


def args_tranche_xl(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True, help="CSV ou Excel des montants de sinistres (une ligne par sinistre).")
    sp.add_argument("--colonne", help="Nom de la colonne des montants (défaut : première colonne numérique).")
    sp.add_argument("--feuille", default=None, help="Feuille Excel (nom ou numéro).")
    sp.add_argument("--seuil", type=float, required=True, help="Seuil u de la GPD (au plus égal à la priorité).")
    sp.add_argument("--annees", type=float, required=True,
                    help="Nombre d'années d'observation couvertes par le fichier (donne la fréquence annuelle).")
    sp.add_argument("--tranche", required=True, help="'priorité,limite haute', ex. 50,200 (portée 150).")
    sp.add_argument("--niveaux", default="0.99,0.995", help="Niveaux de VaR et de CTE (défaut 0.99,0.995).")
    sp.add_argument("--pas", type=float, help="Pas de discrétisation (défaut : portée / 1000 ; doit diviser la portée).")
    sp.add_argument("--franchise-annuelle", type=float, default=0.0, help="Franchise annuelle globale (AAD), défaut 0.")
    sp.add_argument("--limite-annuelle", type=float, help="Limite annuelle globale (AAL), défaut : aucune.")
    sp.add_argument("--parametres", help="'xi,sigma' imposés au lieu de l'ajustement (ex. étude de sensibilité) ; "
                         "si xi est négatif, écrire --parametres=-0.2,5.")


def cmd_tranche_xl(args) -> Resultat:
    tranche = _liste(args.tranche)
    if len(tranche) != 2:
        raise ValueError(f"tranche mal formée : {args.tranche} (attendu 'priorité,limite')")
    niveaux = _liste(args.niveaux)
    parametres = None
    if args.parametres:
        v = _liste(args.parametres)
        if len(v) != 2:
            raise ValueError(f"paramètres mal formés : {args.parametres} (attendu 'xi,sigma')")
        parametres = (v[0], v[1])
    res = Resultat("tranche-xl", {}, options={
        "seuil": args.seuil, "annees": args.annees, "tranche": tranche, "niveaux": niveaux, "pas": args.pas,
        "franchise_annuelle": args.franchise_annuelle, "limite_annuelle": args.limite_annuelle,
        "parametres": list(parametres) if parametres else None})
    x = _lire_pertes(args, res)
    r = tarif_tranche_xl(x, args.seuil, args.annees, tranche[0], tranche[1], niveaux, args.pas,
                         args.franchise_annuelle, args.limite_annuelle, parametres)
    res.hypotheses += [
        Hypothese("frequence", "Poisson, lambda = dépassements du seuil / années d'observation",
                  "Fréquence supposée stable sur la période ; pas de tendance ni de surdispersion.", "méthode"),
        Hypothese("severite", "u + GPD(xi, sigma) au-delà du seuil",
                  "Paramètres imposés par l'utilisateur." if parametres else
                  "Maximum de vraisemblance sur les excès (McNeil 1997), comme la commande gpd.",
                  "option utilisateur" if parametres else "méthode"),
        Hypothese("as_if", "aucune indexation ni mise à l'échelle",
                  "Les montants sont pris tels quels : indexer les sinistres historiques avant l'appel si "
                  "l'inflation ou l'exposition ont changé sur la période.", "valeur par défaut"),
        Hypothese("discretisation", f"pas {r['discretisation']['pas']:g}, méthode des arrondis",
                  "La VaR et la CTE sont lues sur une grille de ce pas ; la prime pure et l'écart type sont exacts.",
                  "option utilisateur" if args.pas else "valeur par défaut"),
    ]
    if parametres is None and r["n_depassements"] < 50:
        res.avertissements.append(f"Seulement {r['n_depassements']} dépassements du seuil : paramètres GPD très incertains.")
    if not r["convergence"]:
        res.avertissements.append("Ajustement GPD non concluant : vérifier avec la commande gpd (diagnostic_optimisation).")
    bc = r["burning_cost"]
    if bc["sinistres_dans_tranche"] < 5:
        res.avertissements.append(f"{bc['sinistres_dans_tranche']} sinistre(s) historique(s) dans la tranche : le burning "
                                  "cost n'est pas fiable, la prime repose surtout sur l'extrapolation GPD.")
    rapport = bc["rapport_modele_sur_burning_cost"]
    if rapport is not None and not 0.5 <= rapport <= 2:
        res.avertissements.append(f"Prime du modèle {rapport:.2f} fois le burning cost : vérifier le seuil, l'indexation "
                                  "et la période d'observation.")
    ecart = r["discretisation"]["ecart_relatif_prime"]
    if ecart is not None and abs(ecart) > 1e-3:
        res.avertissements.append(f"La discrétisation écarte la prime de {ecart:.2%} : réduire le pas.")
    if r["probabilite_sinistre_epuise_tranche"] > 0.5:
        res.avertissements.append("Plus d'un sinistre sur deux au-delà du seuil épuise la tranche : vérifier la limite.")
    sens = r["sensibilite_xi"]
    if sens is not None:
        res.hypotheses.append(Hypothese(
            "sensibilite_xi", "bornes de l'intervalle profilé à 95 %",
            "La prime est recalculée aux deux bornes de l'intervalle de xi (sigma réestimé, fréquence inchangée) : "
            "ordre de grandeur de l'incertitude d'estimation, pas un intervalle de confiance de la prime.", "méthode"))
        primes = [p for p in sens["prime_pure_annuelle_aux_bornes"] if p is not None]
        if r["prime_pure_annuelle"] > 0 and primes:
            ecart = max(abs(p / r["prime_pure_annuelle"] - 1) for p in primes)
            if ecart > 0.5:
                res.avertissements.append(
                    f"Prime très sensible à xi : aux bornes de l'intervalle à 95 % elle va de {min(primes):.6g} à "
                    f"{max(primes):.6g} (estimation centrale {r['prime_pure_annuelle']:.6g}). Le citer avec la prime.")
        if sens["intervalle_95_xi_profil"] == [None, None]:
            res.avertissements.append("Pas d'intervalle profilé pour xi (xi <= -0,5 ou trop peu de dépassements) : "
                                      "l'incertitude d'estimation sur la prime n'est pas quantifiée.")
        elif None in sens["prime_pure_annuelle_aux_bornes"]:
            res.avertissements.append("Une borne de l'intervalle profilé de xi n'est pas atteinte : l'incertitude "
                                      "sur la prime n'est pas bornée de ce côté.")
    res.resultats = r
    return res


COMMANDES = {
    "gpd": (cmd_gpd, "GPD au-delà d'un seuil (McNeil 1997) : xi, sigma, quantiles, primes de tranche.", args_gpd),
    "tranche-xl": (cmd_tranche_xl, "Tranche XL annuelle (Poisson × GPD, Panjer) : prime pure, écart type, VaR, CTE, "
                   "burning cost, franchise et limite annuelles.", args_tranche_xl),
}
