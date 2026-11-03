"""Propriétés de l'agrégation SCR, indépendantes des valeurs publiées."""

import math

import numpy as np
import pytest

from actuaire import scr as m
from actuaire.scr import calculer_scr

MATRICES = [m.BSCR, m.marche(0.0), m.marche(0.5), m.VIE, m.SANTE, m.SANTE_SLT, m.SANTE_NSLT, m.SANTE_CAT, m.NON_VIE]


@pytest.mark.parametrize("struct", MATRICES)
def test_matrices_symetriques_diagonale_unite(struct):
    noms, c = struct
    c = np.array(c, dtype=float)
    assert c.shape == (len(noms), len(noms))
    assert np.allclose(c, c.T)
    assert np.allclose(np.diag(c), 1)
    assert np.all(np.linalg.eigvalsh(c) > -1e-12)


def test_un_seul_module_sans_diversification():
    r, _ = calculer_scr({"non_vie": 1000.0})
    assert r["bscr"] == pytest.approx(1000.0)
    assert r["diversification_bscr"] == pytest.approx(0.0)


def test_diversification_negative_ou_nulle():
    r, _ = calculer_scr({"marche": 100, "contrepartie": 20, "vie": 50, "sante": 10, "non_vie": 70})
    assert -sum(r["modules"].values()) <= r["diversification_bscr"] <= 0


def test_scenario_taux_obligatoire():
    with pytest.raises(ValueError, match="scenario_taux"):
        calculer_scr({"marche": {"taux": 10, "actions": 5}})


def test_operationnel_article_204():
    r, _ = calculer_scr({"non_vie": 100, "operationnel": {"op": 50, "exp_ul": 8}})
    assert r["operationnel"] == pytest.approx(min(0.3 * 100, 50) + 0.25 * 8)


def test_catastrophe_non_vie_article_119():
    r, _ = calculer_scr({"non_vie": {"catastrophe": {"naturelle": 30, "reassurance_non_proportionnelle_dommages": 10,
                                                    "humaine": 20, "autres": 5}}})
    assert r["modules"]["non_vie"] == pytest.approx(math.sqrt(40 ** 2 + 20 ** 2 + 5 ** 2))


def test_cles_inconnues_refusees():
    with pytest.raises(ValueError):
        calculer_scr({"vie": {"mortality": 10}})
    with pytest.raises(ValueError):
        calculer_scr({"ajustements": {"impots_differes": 100}})
