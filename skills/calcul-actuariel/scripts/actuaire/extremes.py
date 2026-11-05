"""Théorie des valeurs extrêmes : loi de Pareto généralisée (GPD) au-delà d'un seuil.

Méthode de McNeil (1997), « Estimating the tails of loss severity distributions using
extreme value theory », ASTIN Bulletin 27(1) :
- ajustement par maximum de vraisemblance de G_{xi,sigma} aux excès Y = X - u des pertes X > u ;
- erreurs types asymptotiques : sqrt(N) (xi^ - xi, sigma^/sigma - 1) -> N(0, (1 + xi) [[1 + xi, 1], [1, 2]]) ;
- estimateur de queue : 1 - F(x) = (N_u / n) (1 + xi (x - u) / sigma)^(-1/xi) pour x > u ;
- quantile : x_p = u + sigma / xi ((n / N_u (1 - p))^(-xi) - 1) ;
- prime pure d'une tranche (r, R) avec r >= u : intégrale de r à R de 1 - F(x).
"""

from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats

XI_NUL = 1e-9


def _log_vraisemblance_negative(params: np.ndarray, y: np.ndarray) -> float:
    xi, log_sigma = params
    sigma = math.exp(log_sigma)
    if abs(xi) < XI_NUL:
        return len(y) * log_sigma + y.sum() / sigma
    z = 1.0 + xi * y / sigma
    if np.any(z <= 0):
        return np.inf
    return len(y) * log_sigma + (1.0 / xi + 1.0) * np.log(z).sum()


def ajuster_gpd(excedents: np.ndarray, diagnostic: dict | None = None) -> tuple[float, float, bool]:
    """Maximum de vraisemblance (xi, sigma) sur les excès ; rend aussi un indicateur de convergence.

    Plusieurs points de départ (moments, xi = -0,2 / 0,1 / 0,5) ; chacun est relancé une fois depuis
    son optimum, et la meilleure vraisemblance est retenue. `diagnostic`, s'il est fourni, reçoit la
    log-vraisemblance, les départs essayés et l'écart entre optima (alerte si plusieurs optima distincts).
    """
    y = np.asarray(excedents, dtype=float)
    if y.size < 2 or np.any(y < 0) or not np.all(np.isfinite(y)):
        raise ValueError("il faut au moins deux excès finis, positifs ou nuls")
    m, v = y.mean(), y.var(ddof=1)
    if not m > 0:
        raise ValueError("tous les excès sont nuls : la GPD n'est pas identifiable")
    xi0 = float(np.clip(0.5 * (1.0 - m * m / v), -0.4, 0.9)) if v > 0 else 0.1
    departs = [(xi0, max(m * (1.0 - xi0), 1e-8))] + [(x, m * (1.0 - x)) for x in (-0.2, 0.1, 0.5)]
    opts = {"xatol": 1e-12, "fatol": 1e-12, "maxiter": 20000}
    essais = []
    for xi_d, s_d in departs:
        d = np.array([xi_d, math.log(s_d)])
        if not np.isfinite(_log_vraisemblance_negative(d, y)):
            continue  # départ hors du support de la GPD
        r = optimize.minimize(_log_vraisemblance_negative, d, args=(y,), method="Nelder-Mead", options=opts)
        r2 = optimize.minimize(_log_vraisemblance_negative, r.x, args=(y,), method="Nelder-Mead", options=opts)
        if np.isfinite(r2.fun):
            essais.append((float(r2.fun), r2, (xi_d, s_d)))
    if not essais:
        raise ValueError("GPD : aucune optimisation n'a trouvé de vraisemblance finie")
    essais.sort(key=lambda e: e[0])
    best = essais[0][1]
    xi, sigma = float(best.x[0]), float(math.exp(best.x[1]))
    meilleurs = [e for e in essais if e[0] - essais[0][0] < 1e-6]
    ecart_xi = max(abs(float(e[1].x[0]) - xi) for e in meilleurs)
    converge = any(e[1].success for e in meilleurs) and ecart_xi < 1e-4
    distincts = [e for e in essais if e[0] - essais[0][0] > 1e-6]
    if diagnostic is not None:
        diagnostic.update({
            "log_vraisemblance": -essais[0][0],
            "departs_essayes": len(departs),
            "departs_convergents": len(essais),
            "iterations": int(best.nit),
            "statut_optimiseur": str(best.message),
            "departs_au_meilleur_optimum": len(meilleurs),
            "ecart_xi_entre_departs": ecart_xi,
            "optima_locaux_moins_bons": len(distincts),
        })
    return xi, sigma, converge


def _cdf_gpd(y: np.ndarray, xi: float, sigma: float) -> np.ndarray:
    if abs(xi) < XI_NUL:
        return 1.0 - np.exp(-y / sigma)
    z = np.maximum(1.0 + xi * y / sigma, 0.0)
    return 1.0 - z ** (-1.0 / xi)


def statistiques_ajustement(excedents: np.ndarray, xi: float, sigma: float) -> dict:
    """Kolmogorov-Smirnov et Anderson-Darling des excès contre la GPD ajustée.

    Les paramètres étant estimés sur les mêmes données, les tables usuelles de ces tests ne
    s'appliquent pas : la p-valeur se calcule par bootstrap paramétrique (voir p_valeur_ajustement)."""
    y = np.sort(np.asarray(excedents, dtype=float))
    n = y.size
    z = np.clip(_cdf_gpd(y, xi, sigma), 1e-300, 1 - 1e-16)
    i = np.arange(1, n + 1)
    ks = float(max(np.max(i / n - z), np.max(z - (i - 1) / n)))
    ad = float(-n - np.mean((2 * i - 1) * (np.log(z) + np.log(1.0 - z[::-1]))))
    return {"kolmogorov_smirnov": ks, "anderson_darling": ad}


def p_valeur_ajustement(excedents: np.ndarray, xi: float, sigma: float, simulations: int,
                        graine: int) -> dict:
    """p-valeur d'Anderson-Darling par bootstrap paramétrique : on simule des échantillons GPD de
    même taille, on réajuste, et on compare les statistiques (méthode de Choulakian et Stephens 2001,
    p-valeur obtenue par simulation au lieu de leurs tables)."""
    if simulations < 19:
        raise ValueError("au moins 19 simulations sont nécessaires pour une p-valeur au seuil de 5 %")
    rng = np.random.default_rng(graine)
    n = len(excedents)
    observe = statistiques_ajustement(excedents, xi, sigma)["anderson_darling"]
    sup, valides = 0, 0
    for _ in range(simulations):
        u = rng.random(n)
        y = -sigma * np.log(u) if abs(xi) < XI_NUL else sigma / xi * (u ** (-xi) - 1.0)
        try:
            xs, ss, ok = ajuster_gpd(y)
        except ValueError:
            continue
        valides += 1
        sup += statistiques_ajustement(y, xs, ss)["anderson_darling"] >= observe
    if valides < 19:
        raise ValueError("bootstrap d'ajustement : trop peu de réajustements réussis")
    return {"p_valeur_anderson_darling": (1 + sup) / (1 + valides), "simulations_valides": valides,
            "graine": graine}


def _ll_profil(xi: float, y: np.ndarray) -> float:
    """Log-vraisemblance maximisée en sigma pour xi fixé."""
    ymax, m = float(y.max()), float(y.mean())
    bas = math.log(max(-xi * ymax * (1 + 1e-9), m * 1e-8)) if xi < 0 else math.log(m * 1e-8)
    haut = math.log(100.0 * (ymax + m))
    r = optimize.minimize_scalar(lambda ls: _log_vraisemblance_negative(np.array([xi, ls]), y),
                                 bounds=(bas, haut), method="bounded", options={"xatol": 1e-10})
    return -float(r.fun)


def intervalle_profil_xi(excedents: np.ndarray, xi: float, sigma: float, niveau: float = 0.95) -> list:
    """Intervalle de confiance de xi par vraisemblance profilée (Coles 2001, section 4.3.4).

    Plus fiable que l'intervalle de Wald pour les petits échantillons et les queues lourdes, car
    il ne suppose pas la normalité de l'estimateur. Une borne non atteinte dans [-1, xi + 5] vaut None."""
    y = np.asarray(excedents, dtype=float)
    ll_max = -_log_vraisemblance_negative(np.array([xi, math.log(sigma)]), y)
    seuil = stats.chi2.ppf(niveau, 1) / 2.0

    def g(t: float) -> float:
        return ll_max - _ll_profil(t, y) - seuil

    bornes = []
    for sens, limite in ((-1, -1.0), (1, xi + 5.0)):
        a, pas, borne = xi, 0.02, None
        while (sens < 0 and a > limite) or (sens > 0 and a < limite):
            b = max(a - pas, limite) if sens < 0 else min(a + pas, limite)
            if g(b) > 0:
                borne = optimize.brentq(g, min(a, b), max(a, b), xtol=1e-8)
                break
            a, pas = b, pas * 1.5
        bornes.append(borne)
    return bornes


def _survie_queue(x: float, u: float, xi: float, sigma: float, part: float) -> float:
    if abs(xi) < XI_NUL:
        return part * math.exp(-(x - u) / sigma)
    z = 1.0 + xi * (x - u) / sigma
    return 0.0 if z <= 0 else part * z ** (-1.0 / xi)


def _integrale_queue(a: float, b: float, u: float, xi: float, sigma: float, part: float) -> float:
    """Intégrale de a à b (u <= a <= b) de la survie de queue."""
    if abs(xi) < XI_NUL:
        return part * sigma * (math.exp(-(a - u) / sigma) - math.exp(-(b - u) / sigma))
    za, zb = 1.0 + xi * (a - u) / sigma, 1.0 + xi * (b - u) / sigma
    if xi < 0:  # support borné : x < u - sigma / xi
        za, zb = max(za, 0.0), max(zb, 0.0)
    if abs(xi - 1.0) < XI_NUL:
        return part * sigma * math.log(zb / za)
    e = 1.0 - 1.0 / xi
    return part * sigma / (xi - 1.0) * (zb ** e - za ** e)


def gpd_seuil(pertes: np.ndarray, seuil: float, quantiles: list[float],
              tranches: list[tuple[float, float]], simulations_ajustement: int = 0,
              graine: int = 2026) -> dict:
    x = np.asarray(pertes, dtype=float)
    if np.any(np.isinf(x)):
        raise ValueError("des pertes sont infinies")
    if not np.isfinite(seuil):
        raise ValueError(f"seuil invalide : {seuil}")
    x = x[~np.isnan(x)]
    if np.any(x < 0):
        raise ValueError("des montants sont négatifs : la GPD s'applique à des pertes positives")
    n = int(x.size)
    excedents = x[x > seuil] - seuil
    nu = int(excedents.size)
    if nu < 2:
        raise ValueError(f"seulement {nu} perte(s) au-dessus du seuil {seuil}")
    diag: dict = {}
    xi, sigma, converge = ajuster_gpd(excedents, diag)
    part = nu / n
    se_xi = (1.0 + xi) / math.sqrt(nu) if xi > -0.5 else None
    se_sigma = sigma * math.sqrt(2.0 * (1.0 + xi) / nu) if xi > -0.5 else None

    def quantile(p: float) -> float:
        if not 0 < p < 1:
            raise ValueError(f"niveau de quantile hors de ]0, 1[ : {p}")
        if 1 - p > part:
            return float(np.quantile(x, p))  # sous le seuil : quantile empirique
        t = (1.0 - p) / part
        if abs(xi) < XI_NUL:
            return seuil - sigma * math.log(t)
        return seuil + sigma / xi * (t ** (-xi) - 1.0)

    res_tranches = {}
    for r, R in tranches:
        if R <= r:
            raise ValueError(f"tranche ({r}, {R}) : la limite haute doit dépasser la priorité")
        if r < seuil:
            raise ValueError(f"tranche ({r}, {R}) : la priorité doit être au moins égale au seuil {seuil}")
        res_tranches[f"{r:g}-{R:g}"] = {
            "priorite": r, "limite": R, "portee": R - r,
            "prime_pure": _integrale_queue(r, R, seuil, xi, sigma, part),
            "probabilite_atteinte": _survie_queue(r, seuil, xi, sigma, part),
        }

    z = stats.norm.ppf(0.975)
    ajustement = statistiques_ajustement(excedents, xi, sigma)
    if simulations_ajustement:
        ajustement.update(p_valeur_ajustement(excedents, xi, sigma, simulations_ajustement, graine))
    return {
        "n": n,
        "seuil": seuil,
        "n_depassements": nu,
        "part_depassements": part,
        "xi": xi,
        "sigma": sigma,
        "erreur_type_xi": se_xi,
        "erreur_type_sigma": se_sigma,
        "intervalle_95_xi_wald": [xi - z * se_xi, xi + z * se_xi] if se_xi else None,
        "intervalle_95_sigma_wald": [sigma - z * se_sigma, sigma + z * se_sigma] if se_sigma else None,
        "intervalle_95_xi_profil": intervalle_profil_xi(excedents, xi, sigma),
        "ajustement": ajustement,
        "convergence": converge,
        "diagnostic_optimisation": diag,
        "excedent_moyen_empirique": float(excedents.mean()),
        "quantiles": {f"{p:g}": quantile(p) for p in quantiles},
        "tranches": res_tranches,
        "maximum_observe": float(x.max()),
    }


def excedent_moyen(pertes: np.ndarray, seuils: list[float]) -> dict:
    """Fonction d'excès moyen empirique e_n(u), outil de choix du seuil (linéaire si GPD)."""
    x = np.asarray(pertes, dtype=float)
    out = {}
    for u in seuils:
        y = x[x > u] - u
        ligne = {"n_depassements": int(y.size), "excedent_moyen": float(y.mean()) if y.size else None,
                 "xi": None, "sigma": None}
        if y.size >= 10:  # stabilité des paramètres selon le seuil (McNeil 1997, figure 6)
            xi, sigma, _ = ajuster_gpd(y)
            ligne.update({"xi": xi, "sigma": sigma})
        out[f"{u:g}"] = ligne
    return out
