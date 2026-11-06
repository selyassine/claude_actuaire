"""Version 0.5.5 : points P2 de l'analyse du 2026-11-05 (soir).

Bootstrap (cellules à moyenne négative), conditionnement de l'ODP, tolérance par défaut de comparer,
sensibilité de la prime XL à xi, récurrence de Panjer sans conversion liste → tableau."""

import json

import numpy as np
import pytest

from actuaire.stochastique import CONDITIONNEMENT_MAX, bootstrap_odp, odp_analytique
from actuaire.triangle import lire_triangle
from cli import calculer, main
from conftest import RACINE

DONNEES = RACINE / "tests" / "donnees"
RAA = lire_triangle(DONNEES / "raa_cumule.csv")
DANISH = str(DONNEES / "danish_mcneil.csv")


def test_odp_rend_le_conditionnement():
    r = odp_analytique(RAA, "pearson")
    assert 1 < r["conditionnement_information"] < 1e8


def test_odp_refuse_une_matrice_mal_conditionnee(tmp_path):
    f = tmp_path / "t.csv"
    lignes = ["Origine,1,2,3,4", "1,1e9,2e9,2.5e9,2.6e9", "2,1.1e9,2.1e9,2.7e9,", "3,1e-6,3e-6,,", "4,1.2e9,,,"]
    f.write_text("\n".join(lignes) + "\n")
    with pytest.raises(ValueError, match="mal conditionnée"):
        odp_analytique(lire_triangle(f), "pearson")
    assert CONDITIONNEMENT_MAX == 1e12


def test_bootstrap_part_des_cellules_negatives():
    r = bootstrap_odp(RAA, 2000, 7)
    n_futur = 45
    assert r["part_cellules_moyenne_negative"] == pytest.approx(r["cellules_moyenne_negative"] / (2000 * n_futur))
    assert 0 <= r["part_cellules_moyenne_negative"] <= 1


def test_bootstrap_avertissement_cite_la_part():
    # RAA : environ 13 % des cellules futures simulées ont une moyenne négative (incréments négatifs du triangle).
    d = calculer(["bootstrap", "--entree", str(DONNEES / "raa_cumule.csv"), "--type", "cumule",
                  "--simulations", "5000", "--graine", "1"])
    assert d["resultats"]["part_cellules_moyenne_negative"] > 0.05
    msg = [a for a in d["avertissements"] if "moyenne" in a and "négative" in a]
    assert msg and "%" in msg[0] and "sous-estimés" in msg[0]


def test_comparer_defaut_un_millionieme(tmp_path):
    sortie = tmp_path / "cl.json"
    d = calculer(["chain-ladder", "--entree", str(DONNEES / "raa_cumule.csv"), "--type", "cumule"])
    sortie.write_text(json.dumps(d), encoding="utf-8")
    u = d["resultats"]["par_origine"]["1990"]["ultime"]
    ext = tmp_path / "ext.csv"
    ext.write_text(f"chemin;valeur\npar_origine.1990.ultime;{u * (1 + 1e-4)!r}\n", encoding="utf-8")
    r = calculer(["comparer", "--resultats", str(sortie), "--externe", str(ext)])
    assert r["options"]["tolerance_relative"] == 1e-6
    assert r["resultats"]["lignes"][0]["statut"] != "conforme"


def test_tranche_xl_sensibilite_xi_encadre_la_prime():
    d = calculer(["tranche-xl", "--entree", DANISH, "--seuil", "10", "--annees", "11", "--tranche", "50,200"])
    r = d["resultats"]
    s = r["sensibilite_xi"]
    bas, haut = s["intervalle_95_xi_profil"]
    assert bas < r["xi"] < haut
    p_bas, p_haut = s["prime_pure_annuelle_aux_bornes"]
    assert p_bas < r["prime_pure_annuelle"] < p_haut
    assert any(h["nom"] == "sensibilite_xi" for h in d["hypotheses"])


def test_tranche_xl_parametres_imposes_sans_sensibilite():
    d = calculer(["tranche-xl", "--entree", DANISH, "--seuil", "10", "--annees", "11", "--tranche", "50,200",
                  "--parametres", "0.5,7"])
    assert d["resultats"]["sensibilite_xi"] is None


def test_tranche_xl_peu_de_depassements_sans_intervalle():
    d = calculer(["tranche-xl", "--entree", DANISH, "--seuil", "60", "--annees", "11", "--tranche", "60,200"])
    assert d["resultats"]["sensibilite_xi"]["intervalle_95_xi_profil"] == [None, None]
    assert any("incertitude d'estimation sur la prime n'est pas quantifiée" in a for a in d["avertissements"])


def test_gpd_xi_inferieur_a_moins_un_demi_sans_erreur(capsys):
    assert main(["gpd", "--entree", DANISH, "--seuil", "60"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["resultats"]["intervalle_95_xi_profil"] == [None, None]


def test_panjer_rend_un_tableau_de_la_bonne_taille():
    from actuaire.reassurance import panjer_poisson

    f = np.array([0.0, 0.5, 0.5])
    g = panjer_poisson(3000.0 / 1000.0, f)
    assert isinstance(g, np.ndarray) and g.ndim == 1
    assert g.sum() == pytest.approx(1.0, abs=1e-11)
    g2 = panjer_poisson(0.5, np.array([0.2] * 5))
    assert len(g2) > 1 and g2.sum() == pytest.approx(1.0, abs=1e-11)
