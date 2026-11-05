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
    if not (np.isfinite(queue) and queue > 0):
        raise ValueError(f"facteur de queue invalide : {queue} (nombre fini strictement positif attendu)")
    imposes = dict(facteurs_imposes or {})
    for k, v in imposes.items():
        if not 0 <= k < n_k - 1:
            raise ValueError(f"facteur imposé hors du triangle : indice {k}")
        if not (np.isfinite(v) and v > 0):
            raise ValueError(f"facteur imposé invalide : {v} (nombre fini strictement positif attendu)")

    f = np.full(n_k - 1, np.nan)
    for k in range(n_k - 1):
        if k in imposes:
            f[k] = imposes[k]
            continue
        m = utilise[:, k]
        if not m.any():
            raise ValueError(f"facteur {k + 1} → {k + 2} non estimable : aucun facteur individuel utilisable "
                             "(données, période ou exclusions). L'imposer explicitement (--facteurs-imposes) "
                             "en justifiant la valeur.")
        if moyenne == "ponderee":
            den = cum[m, k].sum()
            if not den > 0:
                raise ValueError(f"facteur {k + 1} → {k + 2} : somme des montants de départ nulle ou négative")
            f[k] = cum[m, k + 1].sum() / den
        else:
            f[k] = indiv[m, k].mean()
        if not (np.isfinite(f[k]) and f[k] > 0):
            raise ValueError(f"facteur {k + 1} → {k + 2} estimé invalide : {f[k]}")
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
    ultimes_a_priori = np.asarray(ultimes_a_priori, dtype=float)
    if ultimes_a_priori.shape != (tri.n_origines,):
        raise ValueError("un ultime a priori par année d'origine est attendu")
    if not np.all(np.isfinite(ultimes_a_priori)) or np.any(ultimes_a_priori < 0):
        raise ValueError("ultimes a priori : valeurs finies et positives ou nulles attendues")
    age = _age_courant(tri)
    diag = tri.derniere_diagonale()
    cdf = dev.cdf[age]
    non_dev = 1.0 - 1.0 / cdf
    ult = diag + ultimes_a_priori * non_dev
    res = _par_origine(tri, diag, cdf, ult)
    for o, a, p in zip(tri.origines, ultimes_a_priori, non_dev, strict=True):
        res["par_origine"][o]["ultime_a_priori"] = float(a)
        res["par_origine"][o]["part_non_developpee"] = float(p)
    return res


def cape_cod(tri: Triangle, dev: Developpement, primes: np.ndarray) -> dict:
    """Cape Cod (Stanard-Bühlmann) : ratio a priori estimé sur l'ensemble des années.

    ELR = somme des dernières diagonales / somme des primes « utilisées » (prime / CDF).
    Les primes doivent déjà être ajustées (niveau tarifaire, tendance) si la méthode l'exige.
    """
    primes = np.asarray(primes, dtype=float)
    if primes.shape != (tri.n_origines,):
        raise ValueError("une prime par année d'origine est attendue")
    if not np.all(np.isfinite(primes)) or np.any(primes <= 0):
        raise ValueError("primes : valeurs finies et strictement positives attendues")
    age = _age_courant(tri)
    diag = tri.derniere_diagonale()
    cdf = dev.cdf[age]
    primes_utilisees = primes / cdf
    elr = diag.sum() / primes_utilisees.sum()
    res = bornhuetter_ferguson(tri, dev, elr * primes)
    res["ratio_cape_cod"] = float(elr)
    for o, p, pu in zip(tri.origines, primes, primes_utilisees, strict=True):
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
            for o, d, c, u, p in zip(tri.origines, diag, cdf, ult, prov, strict=True)
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
        "facteurs": dict(zip(noms, dev.facteurs.tolist(), strict=True)),
        "cdf_par_age": dict(zip(tri.developpements, dev.cdf.tolist(), strict=True)),
        "queue": dev.queue,
    }
