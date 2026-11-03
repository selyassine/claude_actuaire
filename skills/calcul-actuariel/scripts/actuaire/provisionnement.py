"""Méthodes déterministes de provisionnement : Chain Ladder, Bornhuetter-Ferguson, Cape Cod.

Conventions (nommées pour pouvoir les comparer à chaque publication) :
- Les facteurs de développement sont estimés sur le triangle cumulé.
- "ponderee" : f_k = somme des C(i,k+1) / somme des C(i,k) (Mack 1993, formule de Chain Ladder).
- "simple" : moyenne arithmétique des facteurs individuels C(i,k+1)/C(i,k).
- "periode" : n'utilise que les n dernières diagonales (années calendaires) pour chaque facteur.
- Le facteur de queue multiplie le dernier facteur cumulé (CDF).
- Provision = ultime - dernière diagonale du triangle fourni (payés => provision totale,
  déclarés => IBNR).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .triangle import Triangle

MOYENNES = ("ponderee", "simple")


@dataclass
class Developpement:
    facteurs: np.ndarray          # f_k, k = 1..n-1 (longueur n-1)
    facteurs_individuels: np.ndarray  # C(i,k+1)/C(i,k), NaN si non observé ou exclu
    cdf: np.ndarray               # facteur cumulé jusqu'à l'ultime pour chaque âge (longueur n)
    queue: float


def facteurs_individuels(cum: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = cum[:, 1:] / cum[:, :-1]
    ratio[~np.isfinite(ratio)] = np.nan
    return ratio


def estimer_developpement(
    tri: Triangle,
    moyenne: str = "ponderee",
    periode: int | None = None,
    exclusions: list[tuple[int, int]] | None = None,
    queue: float = 1.0,
    facteurs_imposes: dict[int, float] | None = None,
    arrondi: int | None = None,
) -> Developpement:
    """Estime les facteurs de développement d'un triangle CUMULÉ.

    exclusions : liste de (index_origine, index_facteur), base 0, à retirer du calcul.
    facteurs_imposes : {index_facteur base 0: valeur} pour les choix de jugement.
    arrondi : nombre de décimales des facteurs retenus et des CDF (convention des exhibits
        de Friedland 2010 : facteurs arrondis à 3 décimales, CDF = produit des facteurs
        arrondis, lui-même arrondi à 3 décimales). None = pleine précision.
    """
    if moyenne not in MOYENNES:
        raise ValueError(f"moyenne inconnue : {moyenne} (choix : {MOYENNES})")
    cum = tri.valeurs
    n_i, n_k = cum.shape
    indiv = facteurs_individuels(cum)
    utilise = ~np.isnan(indiv)
    if periode is not None:
        # Diagonale calendaire de la cellule (i, k+1) : i + k + 1. Dernière diagonale = n_i - 1.
        derniere = max(i + np.where(~np.isnan(cum[i]))[0][-1] for i in range(n_i))
        for i in range(n_i):
            for k in range(n_k - 1):
                if i + k + 1 <= derniere - periode:
                    utilise[i, k] = False
    for i, k in exclusions or []:
        utilise[i, k] = False

    f = np.full(n_k - 1, np.nan)
    for k in range(n_k - 1):
        m = utilise[:, k]
        if not m.any():
            f[k] = 1.0
            continue
        if moyenne == "ponderee":
            f[k] = cum[m, k + 1].sum() / cum[m, k].sum()
        else:
            f[k] = indiv[m, k].mean()
    for k, v in (facteurs_imposes or {}).items():
        f[k] = v
    if arrondi is not None:
        f = np.round(f, arrondi)
    cdf = np.empty(n_k)
    cdf[-1] = queue
    for k in range(n_k - 2, -1, -1):
        cdf[k] = cdf[k + 1] * f[k]
    if arrondi is not None:
        cdf = np.round(cdf, arrondi)
    return Developpement(f, np.where(utilise, indiv, np.nan), cdf, queue)


def _age_courant(tri: Triangle) -> np.ndarray:
    obs = tri.observe()
    return np.array([np.where(obs[i])[0][-1] for i in range(tri.n_origines)])


def chain_ladder(tri: Triangle, dev: Developpement) -> dict:
    age = _age_courant(tri)
    diag = tri.derniere_diagonale()
    cdf = dev.cdf[age]
    ult = diag * cdf
    return _par_origine(tri, diag, cdf, ult)


def bornhuetter_ferguson(tri: Triangle, dev: Developpement, ultimes_a_priori: np.ndarray) -> dict:
    age = _age_courant(tri)
    diag = tri.derniere_diagonale()
    cdf = dev.cdf[age]
    non_dev = 1.0 - 1.0 / cdf
    ult = diag + ultimes_a_priori * non_dev
    res = _par_origine(tri, diag, cdf, ult)
    for o, a, p in zip(tri.origines, ultimes_a_priori, non_dev):
        res["par_origine"][o]["ultime_a_priori"] = float(a)
        res["par_origine"][o]["part_non_developpee"] = float(p)
    return res


def cape_cod(tri: Triangle, dev: Developpement, primes: np.ndarray) -> dict:
    """Cape Cod (Stanard-Bühlmann) : ratio a priori estimé sur l'ensemble des années.

    ELR = somme des dernières diagonales / somme des primes « utilisées » (prime / CDF).
    Les primes doivent déjà être ajustées (niveau tarifaire, tendance) si la méthode l'exige.
    """
    age = _age_courant(tri)
    diag = tri.derniere_diagonale()
    cdf = dev.cdf[age]
    primes_utilisees = primes / cdf
    elr = diag.sum() / primes_utilisees.sum()
    res = bornhuetter_ferguson(tri, dev, elr * primes)
    res["ratio_cape_cod"] = float(elr)
    for o, p, pu in zip(tri.origines, primes, primes_utilisees):
        res["par_origine"][o]["prime"] = float(p)
        res["par_origine"][o]["prime_utilisee"] = float(pu)
    return res


def _par_origine(tri: Triangle, diag, cdf, ult) -> dict:
    prov = ult - diag
    return {
        "par_origine": {
            o: {
                "derniere_diagonale": float(d),
                "cdf": float(c),
                "ultime": float(u),
                "provision": float(p),
            }
            for o, d, c, u, p in zip(tri.origines, diag, cdf, ult, prov)
        },
        "total": {
            "derniere_diagonale": float(diag.sum()),
            "ultime": float(ult.sum()),
            "provision": float(prov.sum()),
        },
    }


def description_developpement(tri: Triangle, dev: Developpement) -> dict:
    noms = [f"{tri.developpements[k]}-{tri.developpements[k + 1]}" for k in range(tri.n_dev - 1)]
    return {
        "facteurs": dict(zip(noms, dev.facteurs.tolist())),
        "cdf_par_age": dict(zip(tri.developpements, dev.cdf.tolist())),
        "queue": dev.queue,
    }
