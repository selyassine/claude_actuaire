"""Propriétés de Chain Ladder, BF et Cape Cod, et contrôle croisé avec un logiciel indépendant.

Les valeurs publiées sont testées dans test_publications.py ; ici on vérifie des propriétés
qui doivent tenir quelles que soient les données.
"""

import numpy as np
import pytest

from actuaire.provisionnement import (
    bornhuetter_ferguson,
    cape_cod,
    chain_ladder,
    estimer_developpement,
)
from actuaire.triangle import lire_triangle
from cli import calculer
from conftest import RACINE

DONNEES = RACINE / "tests" / "donnees"
TA = lire_triangle(DONNEES / "taylor_ashe_cumule.csv")


def test_ponderee_egale_somme_sur_somme():
    dev = estimer_developpement(TA)
    c = TA.valeurs
    m = ~np.isnan(c[:, 1])
    assert dev.facteurs[0] == pytest.approx(c[m, 1].sum() / c[m, 0].sum(), rel=1e-12)


def test_simple_egale_moyenne_des_facteurs_individuels():
    dev = estimer_developpement(TA, moyenne="simple")
    c = TA.valeurs
    m = ~np.isnan(c[:, 1])
    assert dev.facteurs[0] == pytest.approx(np.mean(c[m, 1] / c[m, 0]), rel=1e-12)


def test_periode_un_an_utilise_la_derniere_diagonale():
    dev = estimer_developpement(TA, periode=1)
    c = TA.valeurs
    # facteur 1-2 sur une seule année : la dernière origine qui a 2 périodes (ligne 9)
    assert dev.facteurs[0] == pytest.approx(c[8, 1] / c[8, 0], rel=1e-12)


def test_exclusion_et_facteur_impose():
    base = estimer_developpement(TA)
    excl = estimer_developpement(TA, exclusions=[(0, 0)])
    assert excl.facteurs[0] != base.facteurs[0]
    assert np.allclose(excl.facteurs[1:], base.facteurs[1:])
    imp = estimer_developpement(TA, facteurs_imposes={8: 1.05})
    assert imp.facteurs[8] == 1.05
    assert imp.cdf[0] == pytest.approx(base.cdf[0] / base.facteurs[8] * 1.05)


def test_queue_multiplie_tous_les_cdf():
    sans = estimer_developpement(TA)
    avec = estimer_developpement(TA, queue=1.05)
    assert np.allclose(avec.cdf, sans.cdf * 1.05)


def test_premiere_origine_complete_sans_provision():
    r = chain_ladder(TA, estimer_developpement(TA))
    assert r["par_origine"]["1"]["provision"] == 0


def test_bf_avec_a_priori_egal_au_chain_ladder_donne_le_chain_ladder():
    dev = estimer_developpement(TA)
    cl = chain_ladder(TA, dev)
    ult_cl = np.array([v["ultime"] for v in cl["par_origine"].values()])
    bf = bornhuetter_ferguson(TA, dev, ult_cl)
    assert bf["total"]["ultime"] == pytest.approx(cl["total"]["ultime"], rel=1e-12)


def test_cape_cod_ratio_et_ultimes():
    dev = estimer_developpement(TA)
    primes = np.full(TA.n_origines, 10_000_000.0)
    r = cape_cod(TA, dev, primes)
    diag = TA.derniere_diagonale()
    age = [np.where(~np.isnan(TA.valeurs[i]))[0][-1] for i in range(TA.n_origines)]
    elr = diag.sum() / (primes / dev.cdf[age]).sum()
    assert r["ratio_cape_cod"] == pytest.approx(elr, rel=1e-12)
    # ultime = diag + ELR x prime x (1 - 1/CDF)
    o = r["par_origine"]["10"]
    assert o["ultime"] == pytest.approx(diag[9] + elr * 1e7 * (1 - 1 / dev.cdf[0]), rel=1e-12)


def test_incremental_et_cumule_donnent_le_meme_resultat(tmp_path):
    inc = TA.en_incremental()
    chemin = tmp_path / "inc.csv"
    with open(chemin, "w") as f:
        f.write("Origine," + ",".join(TA.developpements) + "\n")
        for o, ligne in zip(TA.origines, inc.valeurs):
            f.write(o + "," + ",".join("" if np.isnan(v) else repr(float(v)) for v in ligne) + "\n")
    a = calculer(["chain-ladder", "--entree", str(chemin), "--type", "incremental"])
    b = calculer(["chain-ladder", "--entree", str(DONNEES / "taylor_ashe_cumule.csv"), "--type", "cumule"])
    assert a["resultats"]["total"]["provision"] == pytest.approx(b["resultats"]["total"]["provision"])


def test_raa_detecte_cumule_malgre_une_baisse():
    """RAA contient une baisse ponctuelle (1982 : 15 599 puis 15 496) mais est cumulé."""
    d = calculer(["chain-ladder", "--entree", str(DONNEES / "raa_cumule.csv")])
    assert d["hypotheses"][0]["valeur"] == "cumule"
    assert any("incertaine" in a for a in d["avertissements"])


@pytest.mark.parametrize("fichier, attendu", [
    # Contrôle croisé : package Python chainladder 0.10.1 (CAS), Chainladder().fit(...).ibnr_.sum()
    ("taylor_ashe_cumule.csv", 18680855.611924313),
    ("raa_cumule.csv", 52135.228261210155),
])
def test_controle_croise_logiciel_independant(fichier, attendu):
    d = calculer(["chain-ladder", "--entree", str(DONNEES / fichier), "--type", "cumule"])
    assert d["resultats"]["total"]["provision"] == pytest.approx(attendu, abs=1e-6)


def test_options_inconnues_message_clair():
    with pytest.raises(ValueError, match="facteur inconnu"):
        calculer(["chain-ladder", "--entree", str(DONNEES / "taylor_ashe_cumule.csv"),
                  "--facteurs-imposes", "12-24=1.5"])
