"""Tarification annuelle d'une tranche de réassurance en excédent de sinistre (XL par risque).

Modèle collectif fréquence × sévérité :
- nombre annuel de sinistres au-delà du seuil u : loi de Poisson de paramètre lambda = N_u / années ;
- montant d'un sinistre au-delà de u : u + GPD(xi, sigma), ajustée par maximum de vraisemblance
  (McNeil 1997) ou imposée ;
- charge d'un sinistre pour la tranche (r, R) : L = min(max(X - r, 0), R - r) ;
- charge annuelle de la tranche : S = L_1 + ... + L_N (loi de Poisson composée).

L'espérance et la variance de S sont exactes (intégrales de la survie GPD). La loi de S est
obtenue par l'algorithme de Panjer (1981) après discrétisation de L par la méthode des arrondis
(« rounding » de Klugman, Panjer et Willmot), ce qui donne la VaR, l'espérance conditionnelle de
queue et l'effet d'une franchise et d'une limite annuelles. Le burning cost est la charge
historique moyenne de la tranche, sans indexation.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import integrate

from .extremes import XI_NUL, ajuster_gpd

POINTS_MAX = 400_000
RESTE_TOLERE = 1e-12


def _survie_conditionnelle(x: float, u: float, xi: float, sigma: float) -> float:
    """P(X > x | X > u) sous la GPD, pour x >= u."""
    if x <= u:
        return 1.0
    if abs(xi) < XI_NUL:
        return math.exp(-(x - u) / sigma)
    z = 1.0 + xi * (x - u) / sigma
    return 0.0 if z <= 0 else z ** (-1.0 / xi)


def _moments_charge(u: float, xi: float, sigma: float, r: float, R: float) -> tuple[float, float]:
    """E[L] et E[L^2] pour un sinistre au-delà de u (intégrales de la survie)."""
    def s(x: float) -> float:
        return _survie_conditionnelle(x, u, xi, sigma)

    m1, _ = integrate.quad(s, r, R, epsabs=1e-14, epsrel=1e-12, limit=500)
    m2, _ = integrate.quad(lambda x: 2.0 * (x - r) * s(x), r, R, epsabs=1e-14, epsrel=1e-12, limit=500)
    return m1, m2


def discretiser_charge(u: float, xi: float, sigma: float, r: float, R: float, pas: float) -> np.ndarray:
    """Loi discrète de L sur 0, h, ..., K h = R - r par la méthode des arrondis.

    f_0 = F(h/2), f_k = F(k h + h/2) - F(k h - h/2) pour 0 < k < K, f_K = 1 - F(K h - h/2) :
    la masse au-delà de la portée (sinistres qui épuisent la tranche) est portée par le dernier point."""
    portee = R - r
    k = round(portee / pas)
    if k < 1 or abs(k * pas - portee) > 1e-9 * max(1.0, portee):
        raise ValueError(f"le pas de discrétisation {pas} doit diviser la portée {portee}")
    bornes = r + pas * (np.arange(k) + 0.5)  # points milieu h/2, 3h/2, ..., (K - 1/2) h
    cdf = np.array([1.0 - _survie_conditionnelle(b, u, xi, sigma) for b in bornes])
    f = np.empty(k + 1)
    f[0] = cdf[0]
    f[1:k] = np.diff(cdf)
    f[k] = 1.0 - cdf[-1]
    return np.clip(f, 0.0, None)


def panjer_poisson(lam: float, f: np.ndarray) -> np.ndarray:
    """Loi de S = somme de N ~ Poisson(lam) copies de L (loi f sur 0, 1, 2, ... pas) : Panjer (1981).

    g_0 = exp(-lam (1 - f_0)) ; g_s = lam / s * somme_{j=1..min(s, K)} j f_j g_{s-j}.
    La récurrence s'arrête quand la masse restante est inférieure à 1e-12."""
    if lam < 0 or not math.isfinite(lam):
        raise ValueError(f"fréquence de Poisson invalide : {lam}")
    k = len(f) - 1
    jf = np.arange(k + 1) * f
    g = [math.exp(-lam * (1.0 - f[0]))]
    if g[0] <= 0:
        raise ValueError("fréquence trop élevée pour la récurrence de Panjer (probabilité de S = 0 nulle en "
                         "précision machine) : augmenter le seuil ou la priorité")
    cumul = g[0]
    s = 0
    while 1.0 - cumul > RESTE_TOLERE:
        s += 1
        if s > POINTS_MAX:
            raise ValueError("loi de la charge annuelle non convergée : augmenter le pas de discrétisation")
        j = min(s, k)
        precedents = np.array(g[s - j:s][::-1])  # g_{s-1}, ..., g_{s-j}
        gs = lam / s * float(np.dot(jf[1:j + 1], precedents))
        g.append(gs)
        cumul += gs
    return np.array(g)


def _var(valeurs: np.ndarray, cdf: np.ndarray, p: float) -> float:
    """Plus petite valeur s telle que P(S <= s) >= p."""
    i = int(np.searchsorted(cdf, p - 1e-15, side="left"))
    return float(valeurs[min(i, len(valeurs) - 1)])


def _cte(valeurs: np.ndarray, probas: np.ndarray, seuil: float) -> float | None:
    """E[S | S > seuil] (définition de l'espérance conditionnelle de queue de actuar)."""
    au_dela = valeurs > seuil
    masse = float(probas[au_dela].sum())
    if masse <= 0:
        return None
    return float(np.dot(valeurs[au_dela], probas[au_dela]) / masse)


def tarif_tranche_xl(pertes: np.ndarray, seuil: float, annees: float, priorite: float, limite: float,
                     niveaux: list[float], pas: float | None = None, franchise_annuelle: float = 0.0,
                     limite_annuelle: float | None = None, parametres: tuple[float, float] | None = None) -> dict:
    x = np.asarray(pertes, dtype=float)
    x = x[~np.isnan(x)]
    if np.any(np.isinf(x)):
        raise ValueError("des pertes sont infinies")
    if np.any(x < 0):
        raise ValueError("des montants sont négatifs")
    if not (math.isfinite(annees) and annees > 0):
        raise ValueError(f"nombre d'années d'observation invalide : {annees}")
    if not math.isfinite(seuil):
        raise ValueError(f"seuil invalide : {seuil}")
    if not (math.isfinite(priorite) and math.isfinite(limite)) or limite <= priorite:
        raise ValueError(f"tranche ({priorite}, {limite}) : la limite haute doit dépasser la priorité")
    if priorite < seuil:
        raise ValueError(f"la priorité {priorite} doit être au moins égale au seuil {seuil} : sous le seuil, "
                         "la GPD ne décrit pas les sinistres")
    if franchise_annuelle < 0 or (limite_annuelle is not None and limite_annuelle <= 0):
        raise ValueError("franchise annuelle négative ou limite annuelle non positive")
    for p in niveaux:
        if not 0 < p < 1:
            raise ValueError(f"niveau hors de ]0, 1[ : {p}")
    portee = limite - priorite
    pas = portee / 1000.0 if pas is None else pas
    if not (math.isfinite(pas) and pas > 0):
        raise ValueError(f"pas de discrétisation invalide : {pas}")

    excedents = x[x > seuil] - seuil
    nu = int(excedents.size)
    if parametres is None:
        if nu < 2:
            raise ValueError(f"seulement {nu} perte(s) au-dessus du seuil {seuil}")
        xi, sigma, converge = ajuster_gpd(excedents)
    else:
        xi, sigma = parametres
        if not (math.isfinite(xi) and math.isfinite(sigma) and sigma > 0):
            raise ValueError(f"paramètres GPD imposés invalides : xi={xi}, sigma={sigma}")
        if nu < 1:
            raise ValueError(f"aucune perte au-dessus du seuil {seuil} : la fréquence est nulle")
        converge = True
    lam = nu / annees

    m1, m2 = _moments_charge(seuil, xi, sigma, priorite, limite)
    esperance = lam * m1
    ecart_type = math.sqrt(lam * m2)

    f = discretiser_charge(seuil, xi, sigma, priorite, limite, pas)
    g = panjer_poisson(lam, f)
    valeurs = pas * np.arange(len(g))
    cdf = np.cumsum(g)
    esperance_discrete = float(np.dot(valeurs, g))

    var = {f"{p:g}": _var(valeurs, cdf, p) for p in niveaux}
    cte = {f"{p:g}": _cte(valeurs, g, var[f"{p:g}"]) for p in niveaux}

    observees = np.minimum(np.maximum(x - priorite, 0.0), portee)
    out = {
        "seuil": seuil,
        "annees_observation": annees,
        "n_depassements": nu,
        "frequence_annuelle_depassements": lam,
        "xi": xi,
        "sigma": sigma,
        "parametres": "imposés" if parametres is not None else "estimés",
        "convergence": converge,
        "tranche": {"priorite": priorite, "limite": limite, "portee": portee},
        "probabilite_sinistre_atteint_tranche": _survie_conditionnelle(priorite, seuil, xi, sigma),
        "probabilite_sinistre_epuise_tranche": _survie_conditionnelle(limite, seuil, xi, sigma),
        "frequence_annuelle_sinistres_dans_tranche": lam * _survie_conditionnelle(priorite, seuil, xi, sigma),
        "charge_moyenne_par_sinistre_au_dela_du_seuil": m1,
        "prime_pure_annuelle": esperance,
        "ecart_type_annuel": ecart_type,
        "probabilite_annee_sans_charge": float(g[0]),
        "var": var,
        "esperance_conditionnelle_queue": cte,
        "burning_cost": {
            "charge_annuelle_moyenne": float(observees.sum() / annees),
            "sinistres_dans_tranche": int((x > priorite).sum()),
            "sinistres_epuisant_tranche": int((x >= limite).sum()),
            "rapport_modele_sur_burning_cost": (esperance / float(observees.sum() / annees)
                                                if observees.sum() > 0 else None),
        },
        "discretisation": {
            "methode": "arrondis (rounding), récurrence de Panjer",
            "pas": pas,
            "points_loi_annuelle": len(g),
            "prime_pure_discretisee": esperance_discrete,
            "ecart_relatif_prime": (esperance_discrete - esperance) / esperance if esperance > 0 else None,
        },
    }
    if franchise_annuelle > 0 or limite_annuelle is not None:
        cedee = np.maximum(valeurs - franchise_annuelle, 0.0)
        if limite_annuelle is not None:
            cedee = np.minimum(cedee, limite_annuelle)
        e = float(np.dot(cedee, g))
        out["conditions_annuelles"] = {
            "franchise_annuelle": franchise_annuelle,
            "limite_annuelle": limite_annuelle,
            "prime_pure_annuelle": e,
            "ecart_type_annuel": math.sqrt(max(float(np.dot(cedee ** 2, g)) - e * e, 0.0)),
            "probabilite_franchise_depassee": float(g[valeurs > franchise_annuelle].sum()),
            "probabilite_limite_epuisee": (float(g[valeurs >= franchise_annuelle + limite_annuelle - 1e-9 * pas].sum())
                                           if limite_annuelle is not None else None),
        }
    return out
