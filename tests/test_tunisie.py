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


# --- provisions-tn (arrêté du 27/02/2001) ---

from actuaire.tunisie import calculer_provisions  # noqa: E402

CADENCES = {"provision": 500.0, "ultime": 1500.0, "derniere_diagonale": 1000.0}


def test_ppna_bornes():
    d = {"ppna": {"date_inventaire": "2025-12-31", "contrats": [
        {"date_effet": "2025-12-31", "date_echeance": "2026-12-31", "prime_commerciale": 365},
        {"date_effet": "2025-01-01", "date_echeance": "2025-12-31", "prime_commerciale": 100}]}}
    r, _ = calculer_provisions(d)
    assert r["ppna"]["total"] == pytest.approx(365.0)


def test_frais_base_hors_frais_et_frais_suffisants():
    r, avert = calculer_provisions({"frais_gestion_sinistres": {
        "psap_hors_frais": 1000, "frais_estimes": 60, "base_minimum": "psap_hors_frais"}})
    f = r["frais_gestion_sinistres"]
    assert f["minimum"] == pytest.approx(50) and f["frais_retenus"] == 60 and avert == []


def test_auto_materiels_sans_cadences_refuse():
    d = {"auto_materiels": {"dossier_par_dossier": 100, "cout_moyen": {"nombre_dossiers": 2, "cout_moyen": 10}}}
    with pytest.raises(ValueError, match="--cadences"):
        calculer_provisions(d)
    r, _ = calculer_provisions(d, CADENCES)
    assert r["auto_materiels"]["methode_retenue"] == "cadences" and r["auto_materiels"]["provision"] == 500


def test_dotation_plafonnee_a_zero_si_plafond_atteint():
    r, _ = calculer_provisions({"egalisation_grele": {"provision_debut": 900, "excedent_technique": 100,
                                                       "primes_exercice": 400}})
    assert r["egalisation_grele"]["dotation"] == 0 and r["egalisation_grele"]["provision_fin"] == 900


@pytest.mark.parametrize("d, message", [
    ({}, "au moins un bloc"),
    ({"ppna": {"date_inventaire": "31/12/2025", "contrats": []}}, "AAAA-MM-JJ"),
    ({"ppna": {"date_inventaire": "2025-12-31", "contrats": [
        {"date_effet": "2025-06-01", "date_echeance": "2025-06-01", "prime_commerciale": 1}]}}, "échéance"),
    ({"prc": {"auto": {"charge_sinistres": 1, "frais": 0, "primes_acquises": 0, "ppna": 1}}}, "strictement positif"),
    ({"frais_gestion_sinistres": {"psap_hors_frais": 1, "frais_estimes": 0, "base_minimum": "x"}}, "base_minimum"),
    ({"equilibrage": {"provision_debut": 0, "excedent_technique": 1, "primes_nettes_5_exercices": [1, 2]}}, "5 exercices"),
    ({"rentes": {"provision_mathematique": -1}}, "positif ou nul"),
    ({"divers": {}}, "clés inconnues"),
])
def test_rejets_provisions(d, message):
    with pytest.raises(ValueError, match=message):
        calculer_provisions(d)


def test_cli_cadences_refuse_autre_methode(tmp_path):
    autre = tmp_path / "m.json"
    from actuaire.sortie import empreinte_resultats
    autre.write_text(json.dumps({"methode": "mack", "resultats": {}, "moteur": {"version": "0.5.2"},
                                 "empreinte_resultats": empreinte_resultats({})}), encoding="utf-8")
    entree = tmp_path / "p.json"
    entree.write_text(json.dumps({"rentes": {"provision_mathematique": 1}}), encoding="utf-8")
    with pytest.raises(ValueError, match="chain-ladder"):
        calculer(["provisions-tn", "--entree", str(entree), "--cadences", str(autre)])


def _sortie_cl(tmp_path, statut="ok", avert=(), provision=500.0):
    from actuaire.sortie import empreinte_resultats
    r = {"total": {"provision": provision, "ultime": 1500.0, "derniere_diagonale": 1000.0}}
    p = tmp_path / "cl.json"
    p.write_text(json.dumps({"methode": "chain-ladder", "statut": statut, "avertissements": list(avert),
                             "moteur": {"version": "0.5.2"}, "resultats": r,
                             "empreinte_resultats": empreinte_resultats(r)}), encoding="utf-8")
    return p


def _entree_auto(tmp_path, dossier=450.0):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"auto_materiels": {"dossier_par_dossier": dossier,
                                                "cout_moyen": {"nombre_dossiers": 10, "cout_moyen": 40}}}),
                 encoding="utf-8")
    return p


def test_cadences_incompletes_refusees_et_avertissements_propages(tmp_path):
    with pytest.raises(ValueError, match="incomplet"):
        calculer(["provisions-tn", "--entree", str(_entree_auto(tmp_path)),
                  "--cadences", str(_sortie_cl(tmp_path, statut="incomplet"))])
    s = calculer(["provisions-tn", "--entree", str(_entree_auto(tmp_path)),
                  "--cadences", str(_sortie_cl(tmp_path, statut="avertissements", avert=["queue imposée"]))])
    assert any("chain-ladder des cadences : queue imposée" in a for a in s["avertissements"])


def test_perimetre_auto_materiels_signale(tmp_path):
    s = calculer(["provisions-tn", "--entree", str(_entree_auto(tmp_path, dossier=100.0)),
                  "--cadences", str(_sortie_cl(tmp_path))])
    assert any("même périmètre" in a for a in s["avertissements"])
    s = calculer(["provisions-tn", "--entree", str(_entree_auto(tmp_path, dossier=450.0)),
                  "--cadences", str(_sortie_cl(tmp_path))])
    assert not any("même périmètre" in a for a in s["avertissements"])
