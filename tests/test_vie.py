"""Propriétés du module vie, indépendantes des valeurs publiées."""

import math

import pytest

from actuaire.vie import Base, Contrat, ModeleSurvie, tarifer
from cli import calculer

SSSM = ModeleSurvie.makeham(0.00022, 2.7e-6, 1.124, facteur_selection=0.9, periode_selection=2)
SUSM = ModeleSurvie.makeham(0.00022, 2.7e-6, 1.124)


def test_relation_annuite_assurance():
    """A = 1 - d ä, pour une vie sélectionnée comme pour une vie ultime."""
    b = Base(SSSM, 0.04)
    d = 0.04 / 1.04
    for s in (0, 1, 5):
        assert b.assurance_deces(50, s) == pytest.approx(1 - d * b.annuite_due(50, s), abs=1e-10)


def test_mixte_relation():
    b = Base(SUSM, 0.05)
    a = b.annuite_due(40, 0, 20)
    mixte = b.assurance_deces(40, 0, 20) + b.capital_differe(40, 0, 20)
    assert mixte == pytest.approx(1 - 0.05 / 1.05 * a, abs=1e-10)


def test_selection_reduit_la_mortalite_puis_disparait():
    assert SSSM.q(50, 0) < SSSM.q(50, 1) < SUSM.q(50, 1) * 1.0000001
    assert SSSM.q(50, 2) == SUSM.q(52, 0)
    # sans sélection, q ultime de Makeham exact
    A, B, c = 0.00022, 2.7e-6, 1.124
    assert SUSM.q(60, 0) == pytest.approx(1 - math.exp(-A - B * c ** 60 * (c - 1) / math.log(c)))


def test_sans_frais_brute_egale_nette():
    b = Base(SUSM, 0.05)
    r = tarifer(b, Contrat("mixte", 40, 1000, duree=20), [0, 5, 20, 25])
    assert r["prime_commerciale"] == pytest.approx(r["prime_nette"])
    for t in ("5", "20"):
        assert r["provisions"][t]["brute"] == pytest.approx(r["provisions"][t]["nette"])
    assert r["provisions"]["20"]["nette"] == pytest.approx(1000)  # échéance : capital dû
    assert r["provisions"]["25"]["nette"] == 0


def test_provision_nulle_a_l_origine_et_fpt_a_un_an():
    b = Base(SSSM, 0.04)
    r = tarifer(b, Contrat("temporaire", 45, 50000, duree=15, frais_initiaux_pct=0.3), [0, 1])
    assert r["provisions"]["1"]["fpt"] == pytest.approx(0, abs=1e-9)


def test_table_fournie(tmp_path):
    f = tmp_path / "table.csv"
    f.write_text("Age;qx\n" + "\n".join(f"{a};{0.01 * (a - 97):.2f}".replace(".", ",") for a in range(98, 101)))
    d = calculer(["survie", "--modele", "table", "--table", str(f), "--taux", "0", "--age", "98"])
    # q98 = 0,01, q99 = 0,02, q100 = 0,03, puis décès certain après le dernier âge de la table
    assert d["resultats"]["esperance_vie_entiere"] == pytest.approx(0.99 + 0.99 * 0.98 + 0.99 * 0.98 * 0.97)
    assert d["entrees"][0]["role"] == "table_mortalite"


def test_erreur_parametres_manquants():
    with pytest.raises(ValueError):
        calculer(["survie", "--modele", "makeham", "--A", "0.001", "--taux", "0.03", "--age", "40"])
