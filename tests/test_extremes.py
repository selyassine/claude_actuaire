"""Propriétés du module GPD, indépendantes des valeurs publiées."""

import numpy as np
import pytest
from scipy import integrate, stats

from actuaire.extremes import _survie_queue, ajuster_gpd, gpd_seuil
from cli import calculer


def test_retrouve_les_parametres_simules():
    y = stats.genpareto.rvs(0.4, scale=3.0, size=20000, random_state=np.random.default_rng(1))
    xi, sigma, ok = ajuster_gpd(y)
    assert ok
    assert xi == pytest.approx(0.4, abs=0.03)
    assert sigma == pytest.approx(3.0, rel=0.03)


def test_concorde_avec_scipy():
    y = stats.genpareto.rvs(0.3, scale=2.0, size=500, random_state=np.random.default_rng(7))
    xi, sigma, _ = ajuster_gpd(y)
    c, _, s = stats.genpareto.fit(y, floc=0)
    assert xi == pytest.approx(c, abs=2e-3)
    assert sigma == pytest.approx(s, rel=2e-3)


def test_quantile_et_survie_coherents():
    x = 1 + stats.genpareto.rvs(0.5, scale=1.0, size=3000, random_state=np.random.default_rng(3))
    r = gpd_seuil(x, 3.0, [0.99, 0.999], [(5.0, 20.0)])
    part = r["n_depassements"] / r["n"]
    for p, q in r["quantiles"].items():
        assert _survie_queue(q, 3.0, r["xi"], r["sigma"], part) == pytest.approx(1 - float(p))
    num = integrate.quad(lambda t: _survie_queue(t, 3.0, r["xi"], r["sigma"], part), 5, 20)[0]
    assert r["tranches"]["5-20"]["prime_pure"] == pytest.approx(num, rel=1e-8)


def test_cas_exponentiel():
    y = stats.expon.rvs(scale=2.0, size=20000, random_state=np.random.default_rng(5))
    xi, sigma, _ = ajuster_gpd(y)
    assert abs(xi) < 0.03
    assert sigma == pytest.approx(2.0, rel=0.03)


def test_tranche_sous_le_seuil_refusee():
    x = np.arange(1.0, 200.0)
    with pytest.raises(ValueError):
        gpd_seuil(x, 50.0, [], [(20.0, 100.0)])


def test_cli_avertit_si_peu_de_depassements(tmp_path):
    f = tmp_path / "pertes.csv"
    v = 1 + stats.genpareto.rvs(0.5, size=300, random_state=np.random.default_rng(9))
    f.write_text("Montant\n" + "\n".join(f"{a:.6f}" for a in v))
    d = calculer(["gpd", "--entree", str(f), "--seuil", str(np.quantile(v, 0.9)),
                  "--diagnostic-seuils", "2,5"])
    assert d["resultats"]["n_depassements"] == 30
    assert any("dépassements" in a for a in d["avertissements"])
    assert set(d["resultats"]["excedent_moyen"]) == {"2", "5"}
