"""Propriétés du module crédibilité, indépendantes des valeurs publiées."""

import numpy as np
import pytest

from actuaire.credibilite import buhlmann_straub, hachemeister, hierarchique
from cli import calculer

RNG = np.random.default_rng(11)
X = 100 + RNG.normal(0, 10, (6, 1))[:, [0] * 8] + RNG.normal(0, 5, (6, 8))
W = RNG.uniform(1, 10, (6, 8))


def test_buhlmann_est_buhlmann_straub_a_poids_egaux():
    a = buhlmann_straub(X)
    b = buhlmann_straub(X, np.full_like(X, 3.0))
    assert a["prime_collective"] == pytest.approx(b["prime_collective"])
    assert [e["prime"] for e in a["entites"]] == pytest.approx([e["prime"] for e in b["entites"]])


def test_prime_entre_moyenne_et_collective():
    r = buhlmann_straub(X, W)
    m = r["prime_collective"]
    for e in r["entites"]:
        assert 0 <= e["credibilite"] <= 1
        assert min(e["moyenne"], m) - 1e-9 <= e["prime"] <= max(e["moyenne"], m) + 1e-9


def test_sans_heterogeneite_prime_collective():
    Xh = np.tile(np.array([100.0, 101, 99, 100, 102, 98]), (5, 1))
    r = buhlmann_straub(Xh, np.ones_like(Xh))
    assert r["variance_entre"] == 0
    assert all(e["prime"] == pytest.approx(r["prime_collective"]) for e in r["entites"])


def test_valeurs_manquantes_ignorees():
    Xm = X.copy()
    Xm[0, 3] = np.nan
    r = buhlmann_straub(Xm, W)
    w0 = np.nansum(np.where(np.isnan(Xm[0]), 0, W[0]))
    assert r["entites"][0]["poids"] == pytest.approx(w0)


def test_iteratif_point_fixe():
    r = buhlmann_straub(X, W, "iteratif")
    z = np.array([e["credibilite"] for e in r["entites"]])
    mi = np.array([e["moyenne"] for e in r["entites"]])
    m = (z * mi).sum() / z.sum()
    assert r["variance_entre"] == pytest.approx((z * (mi - m) ** 2).sum() / (len(z) - 1), rel=1e-8)


def test_hierarchique_deux_estimateurs():
    coh = ["a", "a", "a", "b", "b", "b"]
    for est in ("iteratif", "sans-biais"):
        r = hierarchique(X, W, coh, est)
        assert set(r["cohortes"]) == {"a", "b"}
        assert len(r["entites"]) == 6


def test_regression_barycentre_entre_droites():
    t = np.arange(1, 9.0)
    Xt = X + 3 * t
    r = hachemeister(Xt, W, t, 9, barycentre=True)
    assert len(r["primes"]) == 6
    assert all(0 <= z <= 1 for e in r["entites"] for z in e["credibilite"])


def test_cli_doublon_refuse(tmp_path):
    f = tmp_path / "c.csv"
    f.write_text("Entite,Periode,Ratio,Poids\n1,1,10,1\n1,1,11,1\n2,1,12,1\n2,2,9,1\n")
    with pytest.raises(ValueError):
        calculer(["credibilite", "--entree", str(f)])
