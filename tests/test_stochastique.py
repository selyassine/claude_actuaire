"""Propriétés de Mack, de l'ODP analytique et du bootstrap (les valeurs publiées sont dans les fiches)."""

import numpy as np
import pytest

from actuaire.provisionnement import chain_ladder, estimer_developpement
from actuaire.stochastique import bootstrap_odp, mack, odp_analytique
from actuaire.triangle import lire_triangle
from cli import calculer
from conftest import RACINE

DONNEES = RACINE / "tests" / "donnees"
RAA = lire_triangle(DONNEES / "raa_cumule.csv")
TA = lire_triangle(DONNEES / "taylor_ashe_cumule.csv")


@pytest.mark.parametrize("tri", [RAA, TA])
def test_mack_et_odp_donnent_la_provision_chain_ladder(tri):
    cl = chain_ladder(tri, estimer_developpement(tri))["total"]["provision"]
    assert mack(tri)["total"]["provision"] == pytest.approx(cl, rel=1e-12)
    assert odp_analytique(tri)["total"]["provision"] == pytest.approx(cl, rel=1e-9)


def test_mack_premiere_origine_sans_erreur_et_total_superieur_a_chaque_annee():
    r = mack(TA)
    po = list(r["par_origine"].values())
    assert po[0]["erreur_prediction"] == 0
    assert r["total"]["erreur_prediction"] > max(v["erreur_prediction"] for v in po)


def test_odp_variance_totale_superieure_a_la_somme_des_variances():
    """Les années partagent les paramètres : les covariances sont positives."""
    r = odp_analytique(RAA)
    somme = sum(v["erreur_prediction"] ** 2 for v in r["par_origine"].values())
    assert r["total"]["erreur_prediction"] ** 2 > somme


def test_odp_dispersion_proportionnelle():
    p = odp_analytique(RAA, "pearson")
    d = odp_analytique(RAA, "deviance")
    rapport = d["total"]["erreur_prediction"] / p["total"]["erreur_prediction"]
    assert rapport == pytest.approx(np.sqrt(d["phi"] / p["phi"]), rel=1e-9)


def test_bootstrap_reproductible_avec_la_graine():
    a = bootstrap_odp(RAA, 500, graine=7)
    b = bootstrap_odp(RAA, 500, graine=7)
    c = bootstrap_odp(RAA, 500, graine=8)
    assert a["total"] == b["total"]
    assert a["total"]["moyenne"] != c["total"]["moyenne"]


def test_bootstrap_proche_de_l_analytique():
    """England et Verrall (2002, 8.2.11) : la moyenne et l'écart-type bootstrap sont proches
    de la provision Chain Ladder et de l'erreur de prédiction analytique (Pearson)."""
    b = bootstrap_odp(TA, 5000, graine=1)
    a = odp_analytique(TA)
    assert b["total"]["moyenne"] == pytest.approx(a["total"]["provision"], rel=0.03)
    assert b["total"]["erreur_prediction"] == pytest.approx(a["total"]["erreur_prediction"], rel=0.05)


def test_triangle_non_carre_refuse(tmp_path):
    chemin = tmp_path / "rect.csv"
    chemin.write_text("Origine,1,2,3\nA,10,20,30\nB,10,20,\n")
    with pytest.raises(ValueError, match="non carré"):
        calculer(["mack", "--entree", str(chemin), "--type", "cumule"])


def test_avertissement_peu_de_simulations():
    d = calculer(["bootstrap", "--entree", str(DONNEES / "raa_cumule.csv"), "--type", "cumule",
                  "--simulations", "200"])
    assert any("5 000" in a for a in d["avertissements"])
