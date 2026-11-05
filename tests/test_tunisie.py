"""Marge de solvabilité tunisienne (art. 58 bis) et tables TD99 / TV99."""

import json

import pytest

from actuaire.tunisie import calculer_marge, lire_tables, qx_table
from cli import calculer

BASE_NV = {
    "primes_emises_acceptees": 100.0, "primes_retenues": 60.0,
    "sinistres": {"reglements": [40.0, 45.0, 50.0], "psap_debut": 70.0, "psap_fin": 80.0,
                  "recours_encaisses": 5.0, "charge_nette": 56.0},
}


@pytest.mark.parametrize("nom", ["TD99", "TV99"])
def test_transcription_coherente_avec_qx_imprimes(nom):
    """Jusqu'à 91 ans, le q_x imprimé (arrondi à 0,01 %) égale 1 − l_{x+1}/l_x."""
    t = lire_tables()[nom]
    ages = sorted(t)
    assert ages == list(range(0, ages[-1] + 1))
    assert t[0][0] == 100000 and t[ages[-1]][0] == 0
    for x in ages[:-1]:
        assert t[x + 1][0] <= t[x][0], f"{nom} : l_x croissant à {x} ans"
        if x <= 91:
            q = 1 - t[x + 1][0] / t[x][0]
            assert abs(q - t[x][1]) <= 0.00005 + 1e-12, f"{nom} à {x} ans : {q:.6f} contre {t[x][1]}"


def test_alias_tm99_et_source_publiee():
    assert qx_table("tm99") == qx_table("td99")
    assert qx_table("td99")[100] == pytest.approx(1 - 51 / 101)
    assert qx_table("td99", "publie")[100] == pytest.approx(0.4968)
    assert max(qx_table("tv99")) == 104 and qx_table("tv99")[104] == 1.0
    with pytest.raises(ValueError, match="table inconnue"):
        qx_table("pf60")


def test_plancher_et_choix_de_la_base():
    r, avert = calculer_marge({"non_vie": BASE_NV})
    nv = r["non_vie"]
    assert nv["base_primes"]["montant"] == pytest.approx(12.0)
    assert nv["base_sinistres"]["rapport_retention"]["plancher_applique"]
    assert nv["base_sinistres"]["montant"] == pytest.approx(0.25 * 140 / 3 * 0.5)
    assert nv["methode_retenue"] == "primes" and r["activite"] == "non_vie" and avert == []


def test_mixte_est_la_somme():
    vie = {"provisions_mathematiques_brutes": 100.0, "provisions_mathematiques_nettes": 100.0,
           "capitaux_sous_risque_bruts": 1000.0, "capitaux_sous_risque_nets": 1000.0}
    r, _ = calculer_marge({"non_vie": BASE_NV, "vie": vie})
    assert r["activite"] == "mixte"
    assert r["minimum_reglementaire"] == pytest.approx(12.0 + 4.0 + 3.0)


@pytest.mark.parametrize("modif, message", [
    (lambda d: d["non_vie"]["sinistres"]["reglements"].pop(), "3 attendus"),
    (lambda d: d["non_vie"].update(assurance_credit=True), "7 attendus"),
    (lambda d: d.update(divers=1), "clés inconnues"),
    (lambda d: d["non_vie"]["sinistres"].pop("charge_nette"), "charge_nette manquant"),
    (lambda d: d["non_vie"].update(primes_emises_acceptees=0), "strictement positif"),
    (lambda d: d.update(marge_constituee={"capital": 5}), "éléments inconnus"),
    (lambda d: d.update(marge_constituee={"pertes": -5}), "montant positif attendu"),
    (lambda d: d["non_vie"]["sinistres"].update(psap_fin="80"), "nombre fini"),
])
def test_rejets(modif, message):
    d = {"non_vie": json.loads(json.dumps(BASE_NV))}
    modif(d)
    with pytest.raises(ValueError, match=message):
        calculer_marge(d)


def test_net_superieur_au_brut_signale():
    d = {"non_vie": json.loads(json.dumps(BASE_NV))}
    d["non_vie"]["primes_retenues"] = 120.0
    _, avert = calculer_marge(d)
    assert any("dépasse le brut" in a for a in avert)


def test_cli_tables_tunisiennes():
    sortie = calculer(["survie", "--modele", "tm99", "--taux", "0.045", "--age", "40"])
    hyp = {h["nom"]: h for h in sortie["hypotheses"]}
    assert "TM99" in hyp["loi_de_mortalite"]["valeur"]
    assert any("4 %" in a for a in sortie["avertissements"])
    publie = calculer(["survie", "--modele", "tv99", "--qx-source", "publie", "--taux", "0.03", "--age", "60"])
    lx = calculer(["survie", "--modele", "tv99", "--taux", "0.03", "--age", "60"])
    assert publie["resultats"]["annuite_due_vie_entiere"] != lx["resultats"]["annuite_due_vie_entiere"]
