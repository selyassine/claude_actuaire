"""Entrées invalides et cas dégénérés : le moteur doit refuser plutôt que rendre un chiffre faux.

Chaque test correspond à un défaut relevé par l'audit du 2026-11-05.
"""

import json
import math
import subprocess
import sys

import numpy as np
import pytest
import yaml

from actuaire import vie
from actuaire.credibilite import buhlmann_straub
from actuaire.extremes import ajuster_gpd, gpd_seuil
from actuaire.provisionnement import (
    bornhuetter_ferguson,
    cape_cod,
    estimer_developpement,
)
from actuaire.scr import calculer_scr
from actuaire.sortie import Resultat
from actuaire.stochastique import bootstrap_odp, mack, odp_analytique
from actuaire.triangle import Triangle
from conftest import RACINE

CLI = RACINE / "skills" / "calcul-actuariel" / "scripts" / "cli.py"
N = np.nan


def tri(valeurs):
    v = np.array(valeurs, dtype=float)
    return Triangle([str(2000 + i) for i in range(v.shape[0])], [str(k + 1) for k in range(v.shape[1])], v)


CARRE = tri([[100, 150, 170, 180], [110, 168, 190, N], [120, 175, N, N], [130, N, N, N]])


# --- Triangles -------------------------------------------------------------------------------

def test_trou_interieur_refuse_a_la_conversion():
    inc = tri([[100, N, 50], [90, 40, N], [80, N, N]])
    with pytest.raises(ValueError, match="valeur manquante"):
        inc.en_cumule()


def test_valeur_infinie_refusee():
    with pytest.raises(ValueError, match="infinies"):
        tri([[100, np.inf], [90, N]]).verifier_forme()


def test_trou_refuse_par_la_cli(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("Origine,1,2,3\n2001,100,,180\n2002,110,160,\n2003,120,,\n")
    r = subprocess.run([sys.executable, str(CLI), "chain-ladder", "--entree", str(f), "--type", "cumule"],
                       capture_output=True, text=True)
    assert r.returncode == 2
    err = json.loads(r.stderr)
    assert err["statut"] == "erreur" and "valeur manquante" in err["erreur"]


def test_type_devine_toujours_signale(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("Origine,1,2\n2001,100,150\n2002,110,\n")
    from cli import calculer
    d = calculer(["chain-ladder", "--entree", str(f)])
    assert any("deviné" in a for a in d["avertissements"])


# --- Facteurs de développement ----------------------------------------------------------------

def test_facteur_non_estimable_refuse_au_lieu_de_1():
    with pytest.raises(ValueError, match="non estimable"):
        estimer_developpement(CARRE, exclusions=[(0, 2)])


def test_facteur_non_estimable_accepte_s_il_est_impose():
    dev = estimer_developpement(CARRE, exclusions=[(0, 2)], facteurs_imposes={2: 1.04})
    assert dev.facteurs[2] == 1.04


@pytest.mark.parametrize("queue", [0.0, -1.0, math.inf, math.nan])
def test_queue_invalide(queue):
    with pytest.raises(ValueError, match="queue"):
        estimer_developpement(CARRE, queue=queue)


@pytest.mark.parametrize("valeur", [0.0, -1.2, math.inf, math.nan])
def test_facteur_impose_invalide(valeur):
    with pytest.raises(ValueError, match="imposé"):
        estimer_developpement(CARRE, facteurs_imposes={0: valeur})


def test_facteur_impose_hors_triangle():
    with pytest.raises(ValueError, match="hors du triangle"):
        estimer_developpement(CARRE, facteurs_imposes={7: 1.1})


def test_denominateur_nul_ou_negatif():
    with pytest.raises(ValueError, match="nulle ou négative"):
        estimer_developpement(tri([[-10, 10, 12], [-5, 15, N], [5, N, N]]))
    with pytest.raises(ValueError, match="non estimable"):  # 0 au départ : aucun facteur individuel défini
        estimer_developpement(tri([[0, 10, 12], [0, 15, N], [5, N, N]]))


def test_bf_et_cape_cod_entrees_invalides():
    dev = estimer_developpement(CARRE)
    with pytest.raises(ValueError, match="a priori"):
        bornhuetter_ferguson(CARRE, dev, np.array([200, -1, 210, 220.0]))
    with pytest.raises(ValueError, match="a priori"):
        bornhuetter_ferguson(CARRE, dev, np.array([200, 210, 220.0]))
    with pytest.raises(ValueError, match="primes"):
        cape_cod(CARRE, dev, np.array([300, 0, 310, 320.0]))
    with pytest.raises(ValueError, match="primes"):
        cape_cod(CARRE, dev, np.array([300, math.nan, 310, 320.0]))


# --- Crédibilité -------------------------------------------------------------------------------

def test_poids_negatif_refuse():
    X = np.array([[100.0, 110, 105], [90, 95, 99]])
    W = np.array([[10.0, -5, 8], [7, 9, 6]])
    with pytest.raises(ValueError, match="négatifs"):
        buhlmann_straub(X, W)


def test_ratio_ou_poids_infini_refuse():
    X = np.array([[100.0, 110, 105], [90, 95, 99]])
    W = np.array([[10.0, 5, 8], [7, 9, 6]])
    with pytest.raises(ValueError, match="infinis"):
        buhlmann_straub(np.where(X == 110, np.inf, X), W)
    with pytest.raises(ValueError, match="infinis"):
        buhlmann_straub(X, np.where(W == 5, np.inf, W))


# --- SCR -------------------------------------------------------------------------------------

@pytest.mark.parametrize("donnees, motif", [
    ({"marche": {"scenario_taux": "hausse", "taux": float("nan")}}, "non finie"),
    ({"marche": {"scenario_taux": "hausse", "actions": float("inf")}}, "non finie"),
    ({"vie": {"mortalite": "12"}}, "nombre attendu"),
    ({"contrepartie": {"type1": -5, "type2": 3}}, "négatif"),
    ({"contrepartie": {"type1": float("nan")}}, "non finie"),
    ({"non_vie": {"catastrophe": {"naturelle": -1}}}, "négatif"),
    ({"sante": {"slt": float("nan")}}, "non finie"),
    ({"incorporels": -3}, "négatif"),
    ({"operationnel": {"op": float("nan")}}, "non finie"),
    ({"operationnel": -2}, "négatif"),
    ({"ajustements": {"impots_differes": 5}}, "négatif"),
    ({"ajustements": {"capital_supplementaire": float("inf")}}, "non finie"),
    ({"vie": float("nan")}, "non finie"),
])
def test_scr_entrees_invalides(donnees, motif):
    with pytest.raises(ValueError, match=motif):
        calculer_scr(donnees)


def test_scr_nan_depuis_json(tmp_path):
    f = tmp_path / "s.json"
    f.write_text('{"vie": {"mortalite": NaN}}')
    r = subprocess.run([sys.executable, str(CLI), "scr", "--entree", str(f)], capture_output=True, text=True)
    assert r.returncode == 2 and "non finie" in r.stderr


def test_scr_tout_nul_donne_zero():
    res, _ = calculer_scr({"marche": {"scenario_taux": "hausse"}, "vie": {}, "operationnel": 0})
    assert res["scr"] == 0


# --- Mack, ODP, bootstrap ----------------------------------------------------------------------

def test_mack_triangle_trop_petit():
    petit = tri([[100, 150, 170], [110, 160, N], [120, N, N]])
    with pytest.raises(ValueError, match="trop petit"):
        mack(petit)
    assert math.isfinite(mack(petit, "precedent")["total"]["erreur_prediction"])


def test_odp_triangle_trop_petit():
    with pytest.raises(ValueError, match="trop petit"):
        odp_analytique(tri([[100, 150], [110, N]]))


def test_odp_valeur_ajustee_nulle():
    # Aucun paiement en développement 2 : incréments ajustés nuls, modèle ODP non défini
    zero = tri([[100, 100, 130, 140], [110, 110, 140, N], [120, 120, N, N], [130, N, N, N]])
    with pytest.raises(ValueError, match="ajustée nulle"):
        odp_analytique(zero)
    with pytest.raises(ValueError, match="ajustée nulle"):
        bootstrap_odp(zero, simulations=10)


def test_bootstrap_dispersion_nulle():
    # Triangle exactement Chain Ladder (lignes proportionnelles) : résidus nuls
    exact = tri([[100, 150, 180], [200, 300, N], [300, N, N]])
    with pytest.raises(ValueError, match="dispersion nulle"):
        bootstrap_odp(exact, simulations=10)


@pytest.mark.parametrize("kw", [{"simulations": 1}, {"quantiles": (0.5, 1.0)}])
def test_bootstrap_parametres_invalides(kw):
    with pytest.raises(ValueError):
        bootstrap_odp(CARRE, **kw)


# --- Vie ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("A, B, c", [(0.0002, 0.00004, 1.0), (0.0002, 0.00004, 0.9), (0.0002, 0.0, 1.1),
                                     (-0.01, 0.00004, 1.1), (math.nan, 0.00004, 1.1)])
def test_makeham_parametres_invalides(A, B, c):
    with pytest.raises(ValueError, match="Makeham"):
        vie.ModeleSurvie.makeham(A, B, c)


def test_table_invalide():
    with pytest.raises(ValueError, match="consécutifs"):
        vie.ModeleSurvie.table({60: 0.01, 62: 0.02})
    with pytest.raises(ValueError, match=r"hors de \[0, 1\]"):
        vie.ModeleSurvie.table({60: 0.01, 61: 1.2})


def test_table_age_en_double(tmp_path):
    from actuaire.cli_vie import _lire_qx
    f = tmp_path / "q.csv"
    f.write_text("Age,qx\n60,0.01\n60,0.02\n")
    with pytest.raises(ValueError, match="double"):
        _lire_qx(str(f))


@pytest.mark.parametrize("kw, motif", [
    ({"capital": -1000}, "capital"),
    ({"age": -1}, "âge"),
    ({"duree": -5, "type": "temporaire"}, "durée"),
    ({"duree": 10, "duree_primes": 15, "type": "temporaire"}, "dépasse"),
    ({"frais_initiaux_pct": -0.1}, "frais"),
    ({"frais_renouvellement_pct": 1.0}, "100 %"),
])
def test_contrat_invalide(kw, motif):
    base = {"type": "vie-entiere", "age": 50, "capital": 100000}
    with pytest.raises(ValueError, match=motif):
        vie.Contrat(**(base | kw))


def test_taux_invalide():
    with pytest.raises(ValueError, match="taux"):
        vie.Base(vie.ModeleSurvie.makeham(0.00022, 2.7e-6, 1.124), -1.0)


def test_prime_commerciale_positive_avec_frais_extremes():
    b = vie.Base(vie.ModeleSurvie.makeham(0.00022, 2.7e-6, 1.124), 0.04)
    c = vie.Contrat("temporaire", 40, 1000, duree=1, frais_initiaux_pct=0.99)
    assert vie.tarifer(b, c, [])["prime_commerciale"] > 0


# --- GPD ---------------------------------------------------------------------------------------

def test_gpd_perte_infinie_refusee():
    with pytest.raises(ValueError, match="infinies"):
        gpd_seuil(np.array([1.0, 2, 3, np.inf]), 1.5, [0.99], [])


def test_gpd_excedents_tous_nuls():
    with pytest.raises(ValueError, match="identifiable"):
        ajuster_gpd(np.zeros(20))


def test_gpd_diagnostic_multi_departs():
    rng = np.random.default_rng(3)
    y = rng.pareto(2.0, 400) * 2
    diag = {}
    xi, sigma, ok = ajuster_gpd(y, diag)
    assert ok
    assert diag["departs_convergents"] >= 2
    assert diag["ecart_xi_entre_departs"] < 1e-4
    assert math.isfinite(diag["log_vraisemblance"])


# --- Sortie ------------------------------------------------------------------------------------

def test_resultat_non_fini_signale():
    d = Resultat("test", {"a": 1.0, "b": {"c": math.nan}, "x_pct": math.inf}).en_dict()
    assert d["statut"] == "incomplet"
    assert d["resultats"]["b"]["c"] is None
    # aucun champ n'est exempté, pas même un pourcentage
    assert any("b.c" in a and "x_pct" in a for a in d["avertissements"])
    assert Resultat("test", {"a": 1.0}).en_dict()["statut"] == "ok"
    # un ratio non défini attendu est rendu None explicitement, sans déclencher « incomplet »
    assert Resultat("test", {"x_pct": None}).en_dict()["statut"] == "ok"


def test_erreur_relative_provision_nulle_none():
    from actuaire.stochastique import _ratio
    assert _ratio(5.0, 0.0) is None and _ratio(5.0, -1.0) is None
    assert _ratio(5.0, 10.0) == 0.5


# --- Notation du banc d'essai ------------------------------------------------------------------

def test_essai_manquant_compte_faux(tmp_path):
    sys.path.insert(0, str(RACINE / "banc_essai"))
    from noter import noter
    taches, reps = tmp_path / "taches", tmp_path / "reponses"
    for t in ("t1", "t2"):
        (taches / t).mkdir(parents=True)
        (taches / t / "corrige.yaml").write_text(yaml.safe_dump(
            {"famille": "f", "valeurs": [{"nom": "v", "attendu": 10, "tolerance_absolue": 0.5}]}))
    (reps / "C" / "t1").mkdir(parents=True)
    (reps / "C" / "t1" / "1.md").write_text('```resultats\n{"v": 10}\n```')
    (reps / "C" / "inconnue").mkdir()
    s = noter(reps, taches, conditions=["B", "C"], repetitions=2)
    assert s["C"]["ensemble"] == {"justes": 1, "total": 4, "taux": 0.25}
    assert s["B"]["ensemble"]["total"] == 4 and s["B"]["ensemble"]["justes"] == 0
    assert "C/t1/2" in s["completude"]["essais_manquants"]
    assert s["completude"]["reponses_sans_corrige"] == ["C/inconnue"]
