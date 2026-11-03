"""Provisionnement stochastique : Mack, Poisson sur-dispersé (ODP) analytique, bootstrap ODP.

Références :
- Mack, T. (1993). ASTIN Bulletin 23(2) : formules de l'erreur de prédiction de Chain Ladder.
- England, P. D. et Verrall, R. J. (2002). Stochastic Claims Reserving in General Insurance.
  British Actuarial Journal 8(3) : section 7.2 (ODP analytique), 7.5 (Mack), 8.2 et
  annexe 3 (bootstrap).

Notations : triangle cumulé C (n origines × n développements, carré, NaN dans le futur).
"""

from __future__ import annotations

import numpy as np

from .provisionnement import estimer_developpement, facteurs_individuels
from .triangle import Triangle


def _verifier_carre(tri: Triangle) -> int:
    n_i, n_k = tri.valeurs.shape
    if n_i != n_k:
        raise ValueError(f"triangle non carré ({n_i} origines × {n_k} développements) : "
                         "ces méthodes supposent un triangle complet n × n")
    obs = tri.observe()
    attendu = np.add.outer(np.arange(n_i), np.arange(n_k)) < n_i
    if not np.array_equal(obs, attendu):
        raise ValueError("le triangle doit être exactement triangulaire (pas de trou, pas de diagonale en trop)")
    return n_i


# --------------------------------------------------------------------------------------------
# Mack (1993)
# --------------------------------------------------------------------------------------------

def mack(tri: Triangle, sigma_dernier: str = "mack") -> dict:
    """Erreur de prédiction de Chain Ladder selon Mack (1993).

    sigma_dernier :
      - "mack" : sigma²_{n-1} = min(sigma⁴_{n-2} / sigma²_{n-3}, sigma²_{n-3}, sigma²_{n-2})
        (Mack 1993, p. 218) ;
      - "precedent" : sigma²_{n-1} = sigma²_{n-2} (variante d'England et Verrall 2002, tableau 14).
    """
    n = _verifier_carre(tri)
    C = tri.valeurs
    dev = estimer_developpement(tri)
    f = dev.facteurs
    indiv = facteurs_individuels(C)

    sigma2 = np.full(n - 1, np.nan)
    for k in range(n - 2):
        m = ~np.isnan(indiv[:, k])
        nb = m.sum()
        if nb >= 2:
            sigma2[k] = (C[m, k] * (indiv[m, k] - f[k]) ** 2).sum() / (nb - 1)
    if n >= 4:
        if sigma_dernier == "mack":
            a, b = sigma2[n - 3], sigma2[n - 4]
            sigma2[n - 2] = min(a * a / b if b > 0 else a, b, a)
        elif sigma_dernier == "precedent":
            sigma2[n - 2] = sigma2[n - 3]
        else:
            raise ValueError(f"sigma_dernier inconnu : {sigma_dernier}")

    # Projection complète du triangle
    proj = C.copy()
    for i in range(n):
        for k in range(n - i, n):
            proj[i, k] = proj[i, k - 1] * f[k - 1]
    ult = proj[:, -1]
    diag = tri.derniere_diagonale()
    reserve = ult - diag

    # Sommes de colonnes S_k = somme_{j=1}^{n-k} C_jk (origines observées au passage k -> k+1)
    S = np.array([C[: n - 1 - k, k].sum() for k in range(n - 1)])

    mse = np.zeros(n)
    for i in range(1, n):
        ks = range(n - 1 - i, n - 1)  # facteurs k (base 0) utilisés pour projeter l'origine i
        mse[i] = ult[i] ** 2 * sum(sigma2[k] / f[k] ** 2 * (1 / proj[i, k] + 1 / S[k]) for k in ks)

    mse_total = mse.sum()
    for i in range(1, n):
        ks = range(n - 1 - i, n - 1)
        somme_ult_suivants = ult[i + 1:].sum()
        mse_total += ult[i] * somme_ult_suivants * sum(2 * sigma2[k] / f[k] ** 2 / S[k] for k in ks)

    se = np.sqrt(mse)
    se_total = float(np.sqrt(mse_total))
    return {
        "facteurs": f.tolist(),
        "sigma2": sigma2.tolist(),
        "par_origine": {
            o: {
                "derniere_diagonale": float(d), "ultime": float(u), "provision": float(r),
                "erreur_prediction": float(s),
                "erreur_prediction_pct": float(s / r) if r > 0 else None,
            }
            for o, d, u, r, s in zip(tri.origines, diag, ult, reserve, se)
        },
        "total": {
            "derniere_diagonale": float(diag.sum()), "ultime": float(ult.sum()),
            "provision": float(reserve.sum()), "erreur_prediction": se_total,
            "erreur_prediction_pct": se_total / float(reserve.sum()),
        },
    }


# --------------------------------------------------------------------------------------------
# Poisson sur-dispersé (ODP) : ajustement Chain Ladder et erreur de prédiction analytique
# --------------------------------------------------------------------------------------------

def _ajuste_odp(C: np.ndarray, n: int):
    """Valeurs ajustées incrémentales du modèle ODP (égales à Chain Ladder), passé et futur."""
    cum = C
    f = np.array([cum[: n - 1 - k, k + 1].sum() / cum[: n - 1 - k, k].sum() for k in range(n - 1)])
    # Cumulés ajustés par récurrence arrière depuis la dernière diagonale (annexe 3)
    D = np.full((n, n), np.nan)
    for i in range(n):
        last = n - 1 - i
        D[i, last] = cum[i, last]
        for k in range(last - 1, -1, -1):
            D[i, k] = D[i, k + 1] / f[k]
        for k in range(last + 1, n):
            D[i, k] = D[i, k - 1] * f[k - 1]
    m = D.copy()
    m[:, 1:] = D[:, 1:] - D[:, :-1]
    return f, m


def _dispersion(y: np.ndarray, mu: np.ndarray, ddl: int, methode: str) -> float:
    """Paramètre de dispersion phi du modèle ODP.

    - "pearson" : somme des résidus de Pearson au carré / ddl (England et Verrall 2002, annexe 3) ;
    - "deviance" : déviance de quasi-Poisson / ddl, le terme y log(y/mu) valant 0 si y <= 0
      (valeur 1049,8 du tableau 2 d'England et Verrall 2002, données RAA).
    """
    if methode == "pearson":
        return float(((y - mu) ** 2 / mu).sum() / ddl)
    if methode == "deviance":
        ylog = np.where(y > 0, y * np.log(np.where(y > 0, y, 1.0) / mu), 0.0)
        return float(2 * (ylog - (y - mu)).sum() / ddl)
    raise ValueError(f"dispersion inconnue : {methode} (choix : pearson, deviance)")


def odp_analytique(tri: Triangle, dispersion: str = "pearson") -> dict:
    """Erreur de prédiction analytique du modèle ODP de Chain Ladder (England et Verrall 2002, 7.2).

    MSEP(R) = phi × somme des m futurs + m' Var(eta) m, avec Var(beta) = phi (X'WX)^-1, W = diag(m),
    paramétrage log(m_ij) = c + a_i + b_j avec a_1 = b_1 = 0. phi selon `dispersion` (voir _dispersion).
    """
    n = _verifier_carre(tri)
    C = tri.valeurs
    inc = C.copy()
    inc[:, 1:] = C[:, 1:] - C[:, :-1]
    _, m = _ajuste_odp(C, n)
    passe = np.add.outer(np.arange(n), np.arange(n)) < n
    futur = ~passe

    nb_obs = passe.sum()
    nb_param = 2 * n - 1
    ddl = nb_obs - nb_param
    phi = _dispersion(inc[passe], m[passe], ddl, dispersion)

    def ligne(i, j):
        x = np.zeros(nb_param)
        x[0] = 1.0
        if i > 0:
            x[i] = 1.0
        if j > 0:
            x[n - 1 + j] = 1.0
        return x

    cellules_p = [(i, j) for i in range(n) for j in range(n) if passe[i, j]]
    cellules_f = [(i, j) for i in range(n) for j in range(n) if futur[i, j]]
    X = np.array([ligne(i, j) for i, j in cellules_p])
    W = np.array([m[i, j] for i, j in cellules_p])
    cov_beta = phi * np.linalg.inv(X.T @ (W[:, None] * X))
    Xf = np.array([ligne(i, j) for i, j in cellules_f])
    mf = np.array([m[i, j] for i, j in cellules_f])
    V = Xf @ cov_beta @ Xf.T
    origine_f = np.array([i for i, _ in cellules_f])

    par_origine = {}
    diag = tri.derniere_diagonale()
    for i in range(n):
        sel = origine_f == i
        r = mf[sel].sum()
        msep = phi * r + mf[sel] @ V[np.ix_(sel, sel)] @ mf[sel] if sel.any() else 0.0
        se = float(np.sqrt(msep))
        par_origine[tri.origines[i]] = {
            "derniere_diagonale": float(diag[i]), "provision": float(r), "ultime": float(diag[i] + r),
            "erreur_prediction": se, "erreur_prediction_pct": se / r if r > 0 else None,
        }
    r_tot = mf.sum()
    se_tot = float(np.sqrt(phi * r_tot + mf @ V @ mf))
    return {
        "phi": phi,
        "dispersion": dispersion,
        "degres_de_liberte": int(ddl),
        "par_origine": par_origine,
        "total": {"provision": float(r_tot), "ultime": float(diag.sum() + r_tot),
                  "erreur_prediction": se_tot, "erreur_prediction_pct": se_tot / r_tot},
    }


# --------------------------------------------------------------------------------------------
# Bootstrap ODP (England et Verrall 2002, annexe 3)
# --------------------------------------------------------------------------------------------

def bootstrap_odp(tri: Triangle, simulations: int = 10000, graine: int | None = 2026,
                  quantiles=(0.5, 0.75, 0.9, 0.95, 0.99, 0.995)) -> dict:
    n = _verifier_carre(tri)
    rng = np.random.default_rng(graine)
    C = tri.valeurs
    inc = C.copy()
    inc[:, 1:] = C[:, 1:] - C[:, :-1]
    _, m = _ajuste_odp(C, n)
    passe = np.add.outer(np.arange(n), np.arange(n)) < n
    futur = ~passe

    nb_obs = int(passe.sum())
    ddl = nb_obs - (2 * n - 1)
    r = (inc[passe] - m[passe]) / np.sqrt(m[passe])
    phi = float((r ** 2).sum() / ddl)
    r_adj = r * np.sqrt(nb_obs / ddl)

    m_passe = m[passe]
    res_origine = np.zeros((simulations, n))
    negatifs = 0
    for s in range(simulations):
        pseudo_inc = np.full((n, n), np.nan)
        tirage = rng.choice(r_adj, size=nb_obs, replace=True)
        pseudo_inc[passe] = tirage * np.sqrt(m_passe) + m_passe
        pseudo_cum = np.where(passe, np.nancumsum(pseudo_inc, axis=1), np.nan)
        f = np.array([pseudo_cum[: n - 1 - k, k + 1].sum() / pseudo_cum[: n - 1 - k, k].sum()
                      for k in range(n - 1)])
        proj = pseudo_cum.copy()
        for i in range(1, n):
            for k in range(n - i, n):
                proj[i, k] = proj[i, k - 1] * f[k - 1]
        mf = proj.copy()
        mf[:, 1:] = proj[:, 1:] - proj[:, :-1]
        mu = mf[futur]
        # Loi de processus : Gamma de moyenne mu et de variance phi × mu (ODP)
        sim = np.empty_like(mu)
        pos = mu > 0
        sim[pos] = rng.gamma(shape=mu[pos] / phi, scale=phi)
        sim[~pos] = mu[~pos]
        negatifs += int((~pos).sum())
        lignes = np.where(futur)[0]
        res_origine[s] = np.bincount(lignes, weights=sim, minlength=n)

    total = res_origine.sum(axis=1)
    diag = tri.derniere_diagonale()
    out = {
        "phi": phi,
        "simulations": simulations,
        "graine": graine,
        "par_origine": {
            o: {"moyenne": float(res_origine[:, i].mean()),
                "erreur_prediction": float(res_origine[:, i].std(ddof=1)),
                "ultime_moyen": float(diag[i] + res_origine[:, i].mean())}
            for i, o in enumerate(tri.origines)
        },
        "total": {
            "moyenne": float(total.mean()),
            "erreur_prediction": float(total.std(ddof=1)),
            "erreur_prediction_pct": float(total.std(ddof=1) / total.mean()),
            "quantiles": {f"{q:g}": float(np.quantile(total, q)) for q in quantiles},
        },
        "cellules_moyenne_negative": negatifs,
    }
    return out
