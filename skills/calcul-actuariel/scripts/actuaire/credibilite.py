"""Crédibilité : Bühlmann, Bühlmann-Straub, modèle hiérarchique de Jewell, régression de Hachemeister.

Notations de Bühlmann et Gisler (2005) : X_it ratio de l'entité i en période t, w_it son poids
(volume), s² variance intra-entité, a variance entre entités, z_i facteur de crédibilité.
Les valeurs manquantes (NaN) sont ignorées (poids nul).
"""

from __future__ import annotations

import numpy as np

MAX_ITER = 10000
TOL = 1e-12


def _preparer(X: np.ndarray, W: np.ndarray | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=float)
    W = np.ones_like(X) if W is None else np.asarray(W, dtype=float)
    if X.shape != W.shape:
        raise ValueError("ratios et poids n'ont pas la même forme")
    present = ~np.isnan(X) & ~np.isnan(W) & (W > 0)
    if np.any(W[present] < 0):
        raise ValueError("poids négatifs")
    return np.where(present, X, 0.0), np.where(present, W, 0.0), present


def _intra(X, W, present):
    """Moyennes pondérées par entité, poids totaux et s² (variance intra-entité)."""
    wi = W.sum(1)
    if np.any(wi <= 0):
        raise ValueError("une entité n'a aucune observation")
    Xi = (W * X).sum(1) / wi
    ni = present.sum(1)
    ddl = (ni - 1).sum()
    if ddl <= 0:
        raise ValueError("il faut au moins deux périodes pour une entité")
    s2 = float((W * (X - Xi[:, None]) ** 2 * present).sum() / ddl)
    return Xi, wi, s2


def _a_sans_biais(Xi, wi, s2) -> float:
    I = len(Xi)
    wt = wi.sum()
    Xww = (wi * Xi).sum() / wt
    a = wt / (wt ** 2 - (wi ** 2).sum()) * ((wi * (Xi - Xww) ** 2).sum() - (I - 1) * s2)
    return max(float(a), 0.0)


def _a_iteratif(Xi, wi, s2, depart: float) -> tuple[float, int]:
    """Estimateur de Bichsel-Straub (point fixe)."""
    I = len(Xi)
    a = depart if depart > 0 else float(np.var(Xi, ddof=1))
    for k in range(MAX_ITER):
        if a <= 0:
            return 0.0, k
        z = wi / (wi + s2 / a)
        m = (z * Xi).sum() / z.sum()
        nouveau = float((z * (Xi - m) ** 2).sum() / (I - 1))
        if abs(nouveau - a) <= TOL * max(a, 1.0):
            return nouveau, k + 1
        a = nouveau
    raise ValueError("l'estimateur itératif n'a pas convergé")


def _credibilite(Xi, wi, s2, a):
    if a > 0:
        z = wi / (wi + s2 / a)
        m = float((z * Xi).sum() / z.sum())
    else:  # aucune hétérogénéité détectée : prime collective pour tous
        z = np.zeros_like(wi)
        m = float((wi * Xi).sum() / wi.sum())
    return z, m


def buhlmann_straub(X, W=None, estimateur: str = "sans-biais") -> dict:
    X, W, present = _preparer(X, W)
    if X.shape[0] < 2:
        raise ValueError("il faut au moins deux entités")
    Xi, wi, s2 = _intra(X, W, present)
    a = _a_sans_biais(Xi, wi, s2)
    iterations = None
    if estimateur == "iteratif":
        a, iterations = _a_iteratif(Xi, wi, s2, a)
    elif estimateur != "sans-biais":
        raise ValueError(f"estimateur inconnu : {estimateur}")
    z, m = _credibilite(Xi, wi, s2, a)
    return {
        "prime_collective": m,
        "variance_entre": a,
        "variance_intra": s2,
        "iterations": iterations,
        "entites": [{"moyenne": float(Xi[i]), "poids": float(wi[i]), "credibilite": float(z[i]),
                     "prime": float(z[i] * Xi[i] + (1 - z[i]) * m)} for i in range(len(Xi))],
    }


def hierarchique(X, W, cohortes, estimateur: str = "iteratif") -> dict:
    """Modèle hiérarchique à deux niveaux (Jewell 1975 ; Bühlmann et Gisler 2005, ch. 6)."""
    X, W, present = _preparer(X, W)
    coh = np.asarray(cohortes)
    groupes = list(dict.fromkeys(coh.tolist()))
    if len(groupes) < 2:
        raise ValueError("il faut au moins deux cohortes")
    Xij, wij, s2 = _intra(X, W, present)
    idx = [np.flatnonzero(coh == g) for g in groupes]
    if any(len(ix) < 2 for ix in idx):
        raise ValueError("chaque cohorte doit contenir au moins deux entités")
    I = len(groupes)

    def niveau(a, b):
        z = wij / (wij + s2 / a) if a > 0 else np.zeros_like(wij)
        zS = np.array([z[ix].sum() for ix in idx])
        Xz = np.array([(z[ix] * Xij[ix]).sum() / z[ix].sum() if z[ix].sum() > 0
                       else (wij[ix] * Xij[ix]).sum() / wij[ix].sum() for ix in idx])
        zi = zS / (zS + a / b) if b > 0 else np.zeros(I)
        return z, zS, Xz, zi

    if estimateur == "sans-biais":
        # Bühlmann et Gisler (2005) : A_i / c_i et B / d, tronqués à 0
        Xiw = np.array([(wij[ix] * Xij[ix]).sum() / wij[ix].sum() for ix in idx])
        A = np.array([(wij[ix] * (Xij[ix] - Xiw[k]) ** 2).sum() - (len(ix) - 1) * s2 for k, ix in enumerate(idx)])
        c = np.array([wij[ix].sum() - (wij[ix] ** 2).sum() / wij[ix].sum() for ix in idx])
        a = float(np.mean(np.maximum(A / c, 0.0)))
        z, zS, Xz, _ = niveau(a, 1.0)
        Xzz_bar = (zS * Xz).sum() / zS.sum()
        B = (zS * (Xz - Xzz_bar) ** 2).sum() - (I - 1) * a
        d = zS.sum() - (zS ** 2).sum() / zS.sum()
        b = max(float(B / d), 0.0)
        iterations = None
    elif estimateur == "iteratif":
        a = b = float(np.var(Xij, ddof=1))
        for iterations in range(1, MAX_ITER + 1):
            z, zS, Xz, zi = niveau(a, b)
            a_n = float(sum((z[ix] * (Xij[ix] - Xz[k]) ** 2).sum() for k, ix in enumerate(idx))
                        / sum(len(ix) - 1 for ix in idx))
            m = (zi * Xz).sum() / zi.sum() if zi.sum() > 0 else Xz.mean()
            b_n = float((zi * (Xz - m) ** 2).sum() / (I - 1))
            fini = abs(a_n - a) <= TOL * max(a, 1.0) and abs(b_n - b) <= TOL * max(b, 1.0)
            a, b = a_n, b_n
            if fini:
                break
        else:
            raise ValueError("l'estimateur itératif n'a pas convergé")
    else:
        raise ValueError(f"estimateur inconnu : {estimateur}")

    z, zS, Xz, zi = niveau(a, b)
    if estimateur == "iteratif":
        m = float((zi * Xz).sum() / zi.sum()) if zi.sum() > 0 else float(Xz.mean())
    else:
        m = float((zS * Xz).sum() / zS.sum())
    prime_coh = zi * Xz + (1 - zi) * m
    pos = {g: k for k, g in enumerate(groupes)}
    prime_ent = np.array([z[j] * Xij[j] + (1 - z[j]) * prime_coh[pos[coh[j]]] for j in range(len(Xij))])
    return {
        "prime_collective": m,
        "variance_entre_cohortes": b,
        "variance_entre_entites": a,
        "variance_intra": s2,
        "iterations": iterations,
        "cohortes": {str(g): {"moyenne": float(Xz[k]), "poids": float(zS[k]), "credibilite": float(zi[k]),
                              "prime": float(prime_coh[k])} for k, g in enumerate(groupes)},
        "entites": [{"cohorte": str(coh[j]), "moyenne": float(Xij[j]), "poids": float(wij[j]),
                     "credibilite": float(z[j]), "prime": float(prime_ent[j])} for j in range(len(Xij))],
    }


def _ajuster_individuels(X, W, present, Y):
    I, n = X.shape
    p = Y.shape[1]
    coefs, mats, ddl, rss = [], [], 0, 0.0
    for i in range(I):
        w = W[i] * present[i]
        M = Y.T @ (w[:, None] * Y)
        if np.linalg.matrix_rank(M) < p:
            raise ValueError(f"entité {i + 1} : pas assez d'observations pour la régression")
        b = np.linalg.solve(M, Y.T @ (w * X[i]))
        coefs.append(b)
        mats.append(M)
        rss += float((w * (X[i] - Y @ b) ** 2).sum())
        ddl += int(present[i].sum()) - p
    if ddl <= 0:
        raise ValueError("pas assez d'observations pour estimer la variance intra")
    return np.array(coefs), mats, rss / ddl


def hachemeister(X, W, temps, futur: float, barycentre: bool = False, estimateur: str = "sans-biais") -> dict:
    """Régression de crédibilité de Hachemeister (1975), tendance linéaire X_it = b0 + b1 t.

    barycentre=True : approximation de Bühlmann et Gisler (2005, section 8.4) ; plan
    orthogonalisé selon les poids collectifs, puis Bühlmann-Straub séparé sur chaque coefficient
    (estimateur sans biais ou itératif).
    Sinon : modèle d'origine, matrice de covariance A estimée par point fixe (pseudo-estimateur).
    """
    X, W, present = _preparer(X, W)
    t = np.asarray(temps, dtype=float)
    I, n = X.shape
    if len(t) != n:
        raise ValueError("autant de valeurs de temps que de périodes")
    Y = np.column_stack([np.ones(n), t])
    yf = np.array([1.0, float(futur)])

    if barycentre:
        wcol = W.sum(0) / W.sum()
        Q, R = np.linalg.qr(Y * np.sqrt(wcol)[:, None])
        Yo = Q / np.sqrt(wcol)[:, None]
        yf_o = yf @ np.linalg.inv(R)
        coefs, _, s2 = _ajuster_individuels(X, W, present, Yo)
        # poids de chaque coefficient : somme des w_it x_tk²
        poids = np.array([[(W[i] * Yo[:, k] ** 2).sum() for k in range(2)] for i in range(I)])
        coll, zs, avars = np.zeros(2), np.zeros((I, 2)), np.zeros(2)
        for k in range(2):
            a = _a_sans_biais(coefs[:, k], poids[:, k], s2)
            if a > 0 and estimateur == "iteratif":
                a, _ = _a_iteratif(coefs[:, k], poids[:, k], s2, a)
            zs[:, k], coll[k] = _credibilite(coefs[:, k], poids[:, k], s2, a)
            avars[k] = a
        ajustes = coll + zs * (coefs - coll)
        primes = ajustes @ yf_o
        return {
            "variante": "barycentre",
            "variance_intra": s2,
            "variances_entre": avars.tolist(),
            "primes": [float(v) for v in primes],
            "entites": [{"credibilite": zs[i].tolist(), "prime": float(primes[i])} for i in range(I)],
        }

    coefs, mats, s2 = _ajuster_individuels(X, W, present, Y)
    A = np.cov(coefs.T)
    for it in range(1, MAX_ITER + 1):
        Z = [A @ np.linalg.inv(A + s2 * np.linalg.inv(M)) for M in mats]
        bc = np.linalg.solve(sum(Z), sum(Z[i] @ coefs[i] for i in range(I)))
        An = sum(Z[i] @ np.outer(coefs[i] - bc, coefs[i] - bc) for i in range(I)) / (I - 1)
        An = (An + An.T) / 2
        # le système est mal conditionné (colonnes 1 et t) : bruit numérique de l'ordre de 1e-6 en relatif
        if np.max(np.abs(An - A) / np.maximum(np.abs(A), 1e-300)) <= 1e-5:
            A = An
            break
        A = An
    else:
        raise ValueError("l'estimation de A n'a pas convergé")
    Z = [A @ np.linalg.inv(A + s2 * np.linalg.inv(M)) for M in mats]
    bc = np.linalg.solve(sum(Z), sum(Z[i] @ coefs[i] for i in range(I)))
    ajustes = [Z[i] @ coefs[i] + (np.eye(2) - Z[i]) @ bc for i in range(I)]
    primes = [float(yf @ c) for c in ajustes]
    return {
        "variante": "origine",
        "coefficients_collectifs": bc.tolist(),
        "variance_intra": s2,
        "covariance_entre": A.tolist(),
        "iterations": it,
        "primes": primes,
        "entites": [{"coefficients_individuels": coefs[i].tolist(), "coefficients_credibilite": ajustes[i].tolist(),
                     "matrice_credibilite": Z[i].tolist(), "prime": primes[i]} for i in range(I)],
    }
