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
from scipy import optimize

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


def ajuster_gpd(excedents: np.ndarray) -> tuple[float, float, bool]:
    """Maximum de vraisemblance (xi, sigma) sur les excès ; rend aussi un indicateur de convergence."""
    y = np.asarray(excedents, dtype=float)
    if y.size < 2 or np.any(y < 0):
        raise ValueError("il faut au moins deux excès positifs ou nuls")
    # départ : méthode des moments (valable si xi < 1/2), bornée
    m, v = y.mean(), y.var(ddof=1)
    xi0 = float(np.clip(0.5 * (1.0 - m * m / v), -0.4, 0.9)) if v > 0 else 0.1
    sigma0 = max(m * (1.0 - xi0), 1e-8)
    depart = np.array([xi0, math.log(sigma0)])
    r = optimize.minimize(_log_vraisemblance_negative, depart, args=(y,), method="Nelder-Mead",
                          options={"xatol": 1e-12, "fatol": 1e-12, "maxiter": 20000})
    r2 = optimize.minimize(_log_vraisemblance_negative, r.x, args=(y,), method="Nelder-Mead",
                           options={"xatol": 1e-12, "fatol": 1e-12, "maxiter": 20000})
    return float(r2.x[0]), float(math.exp(r2.x[1])), bool(r2.success)


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
              tranches: list[tuple[float, float]]) -> dict:
    x = np.asarray(pertes, dtype=float)
    x = x[~np.isnan(x)]
    n = int(x.size)
    excedents = x[x > seuil] - seuil
    nu = int(excedents.size)
    if nu < 2:
        raise ValueError(f"seulement {nu} perte(s) au-dessus du seuil {seuil}")
    xi, sigma, converge = ajuster_gpd(excedents)
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

    return {
        "n": n,
        "seuil": seuil,
        "n_depassements": nu,
        "part_depassements": part,
        "xi": xi,
        "sigma": sigma,
        "erreur_type_xi": se_xi,
        "erreur_type_sigma": se_sigma,
        "convergence": converge,
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
        out[f"{u:g}"] = {"n_depassements": int(y.size), "excedent_moyen": float(y.mean()) if y.size else None}
    return out
