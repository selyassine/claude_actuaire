"""Commande registre (0.4.2) : registre des hypothèses d'un dossier de calculs."""

import json

import pytest

from actuaire.cli_registre import _md
from cli import calculer, main
from conftest import RACINE

RAA = str(RACINE / "tests" / "donnees" / "raa_cumule.csv")
FR_TRI = str(RACINE / "tests" / "donnees" / "friedland_us_auto_declares.csv")
FR_PRIMES = str(RACINE / "tests" / "donnees" / "friedland_us_auto_primes.csv")


def sortie(dossier, nom, argv):
    d = calculer(argv)
    f = dossier / nom
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return f, d


def registre(*argv):
    return calculer(["registre", "--sorties", *map(str, argv)])


def codes(r):
    return {i["code"]: i["gravite"] for i in r["resultats"]["incoherences"]}


def erreur(argv, capsys):
    code = main(argv)
    err = capsys.readouterr().err
    return code, (json.loads(err) if err.strip() else {})


def test_dossier_coherent_et_note(tmp_path):
    s = tmp_path / "sorties"
    s.mkdir()
    sortie(s, "cl.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    sortie(s, "bf.json", ["bf", "--entree", FR_TRI, "--primes", FR_PRIMES, "--ratio", "0.65", "--type", "cumule"])
    note = tmp_path / "note" / "hypotheses.md"
    d = calculer(["registre", "--sorties", str(s), "--note", str(note), "--titre", "Dossier test"])
    r = d["resultats"]
    assert r["conclusion"] == "coherent" and r["n_calculs"] == 2 and d["statut"] == "ok"
    assert [c["fichier"] for c in r["calculs"]] == ["bf.json", "cl.json"]
    assert all(c["empreinte_verifiee"] for c in r["calculs"])
    assert any(h["nom"] == "sinistralite_a_priori" and h["valeur"] == 0.65 for h in r["hypotheses"]["choix_de_jugement"])
    assert any(h["nom"] == "moyenne_des_facteurs" for h in r["hypotheses"]["valeurs_par_defaut"])
    texte = note.read_text(encoding="utf-8")
    assert texte.startswith("# Dossier test") and "## Choix de jugement" in texte and "sinistralite_a_priori" in texte
    assert "python cli.py bf" in texte and "inchangé" in texte
    assert r["note"]["fichier"] == str(note) and len(r["note"]["sha256"]) == 64


def test_hypotheses_divergentes_sur_les_memes_donnees(tmp_path):
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    b, _ = sortie(tmp_path, "b.json", ["chain-ladder", "--entree", RAA, "--type", "cumule", "--queue", "1.05"])
    d = registre(a, b)
    assert codes(d) == {"hypotheses_divergentes": "alerte"}
    i = d["resultats"]["incoherences"][0]
    assert "facteur_de_queue" in i["message"] and set(i["calculs"]) == {"a.json", "b.json"}
    assert d["resultats"]["conclusion"] == "a_examiner"


def test_pas_de_divergence_sur_des_donnees_differentes(tmp_path):
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    b, _ = sortie(tmp_path, "b.json", ["chain-ladder", "--entree", FR_TRI, "--type", "cumule", "--queue", "1.05"])
    assert "hypotheses_divergentes" not in codes(registre(a, b))


def test_resultats_retouches(tmp_path):
    a, d = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    d["resultats"]["total"]["provision"] = 1.0
    a.write_text(json.dumps(d), encoding="utf-8")
    r = registre(a)
    assert codes(r)["resultats_retouches"] == "bloquant" and r["resultats"]["conclusion"] == "bloquant"
    assert r["resultats"]["calculs"][0]["empreinte_verifiee"] is False


def test_donnees_differentes_et_modifiees(tmp_path):
    tri = tmp_path / "t.csv"
    tri.write_text("Origine,1,2\n2020,100,150\n2021,110,\n", encoding="utf-8")
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", str(tri), "--type", "cumule"])
    tri.write_text("Origine,1,2\n2020,100,160\n2021,110,\n", encoding="utf-8")
    b, _ = sortie(tmp_path, "b.json", ["chain-ladder", "--entree", str(tri), "--type", "cumule"])
    r = registre(a, b)
    c = codes(r)
    assert c["donnees_differentes"] == "bloquant" and c["donnees_modifiees_depuis"] == "alerte"
    modif = next(i for i in r["resultats"]["incoherences"] if i["code"] == "donnees_modifiees_depuis")
    assert modif["calculs"] == ["a.json"]


def test_donnees_introuvables_et_option_sans_verification(tmp_path):
    tri = tmp_path / "t.csv"
    tri.write_text("Origine,1,2\n2020,100,150\n2021,110,\n", encoding="utf-8")
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", str(tri), "--type", "cumule"])
    tri.unlink()
    assert codes(registre(a))["donnees_introuvables"] == "info"
    d = calculer(["registre", "--sorties", str(a), "--sans-verifier-entrees"])
    assert codes(d) == {} and d["resultats"]["donnees"][0]["sha256_actuel"] is None


def test_versions_environnements_statut_et_empreinte(tmp_path):
    a, d = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    d["moteur"]["version"] = "0.2.0"
    d["moteur"]["environnement"] = {"python": "3.9"}
    d["statut"] = "incomplet"
    d.pop("empreinte_resultats")
    b = tmp_path / "b.json"
    b.write_text(json.dumps(d), encoding="utf-8")
    c = codes(registre(a, b))
    assert c["versions_differentes"] == "alerte" and c["environnements_differents"] == "info"
    assert c["calcul_incomplet"] == "alerte" and c["sans_empreinte"] == "info"


def test_fichiers_ignores_et_doublons(tmp_path):
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    (tmp_path / "x.json").write_text("{pas du json", encoding="utf-8")
    (tmp_path / "y.json").write_text('{"a": 1}', encoding="utf-8")
    reg = calculer(["registre", "--sorties", str(a)])
    (tmp_path / "z.json").write_text(json.dumps(reg), encoding="utf-8")
    d = registre(tmp_path, a)
    r = d["resultats"]
    assert r["n_calculs"] == 1
    raisons = sorted(i["raison"] for i in r["fichiers_ignores"])
    assert raisons[0].startswith("JSON illisible") and "pas une sortie du moteur" in raisons
    assert "sortie d'un registre" in raisons
    assert any("ignoré" in a for a in d["avertissements"])


def test_refus(tmp_path, capsys):
    (tmp_path / "y.json").write_text('{"a": 1}', encoding="utf-8")
    code, e = erreur(["registre", "--sorties", str(tmp_path)], capsys)
    assert code == 2 and "aucune sortie du moteur" in e["erreur"]
    code, e = erreur(["registre", "--sorties", str(tmp_path / "absent.json")], capsys)
    assert code == 2 and "introuvable" in e["erreur"]
    a, _ = sortie(tmp_path, "a.json", ["chain-ladder", "--entree", RAA, "--type", "cumule"])
    code, e = erreur(["registre", "--sorties", str(a), "--note", str(a)], capsys)
    assert code == 2 and "ne peut pas remplacer" in e["erreur"]


def test_echappement_markdown():
    assert _md("a|b\nc") == "a\\|b c" and _md(1.5) == "1.5" and _md(None) == "null"


@pytest.mark.parametrize("cmd", [["gpd", "--entree", str(RACINE / "tests/donnees/danish_mcneil.csv"), "--seuil", "10"],
                                 ["survie", "--modele", "sssm", "--taux", "0.04", "--age", "50", "--n", "20"]])
def test_registre_accepte_toutes_les_methodes(tmp_path, cmd):
    a, _ = sortie(tmp_path, "a.json", cmd)
    r = registre(a)["resultats"]
    assert r["n_calculs"] == 1 and sum(len(v) for v in r["hypotheses"].values()) >= 1
