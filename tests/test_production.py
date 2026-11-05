"""Contrôles de la version 0.3.0 : contrôles métier croisés, reproductibilité, cohérence
des versions et installation réelle de l'archive du skill."""

import json
import re
import subprocess
import sys
import zipfile

import pytest

from cli import calculer, main
from conftest import RACINE

DONNEES = RACINE / "tests" / "donnees"
RAA = DONNEES / "raa_cumule.csv"
FR_TRI = DONNEES / "friedland_us_auto_declares.csv"
FR_PRIMES = DONNEES / "friedland_us_auto_primes.csv"


def ecrire(chemin, texte):
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def erreur(argv, capsys):
    """Code de sortie et message d'erreur JSON d'une commande refusée."""
    code = main(argv)
    err = capsys.readouterr().err
    return code, (json.loads(err) if err.strip() else {})


# --- Commande triangle ---------------------------------------------------------------------------

def test_triangle_refuse_un_trou(tmp_path, capsys):
    f = ecrire(tmp_path / "t.csv", "Origine,1,2,3\n2020,100,,130\n2021,110,140,\n2022,120,,\n")
    code, e = erreur(["triangle", "--entree", str(f), "--type", "cumule"], capsys)
    assert code == 2 and e["statut"] == "erreur" and "manquante" in e["erreur"]


def test_triangle_refuse_une_ligne_vide(tmp_path, capsys):
    f = ecrire(tmp_path / "t.csv", "Origine,1,2\n2020,100,130\n2021,,\n")
    code, e = erreur(["triangle", "--entree", str(f), "--type", "cumule"], capsys)
    assert code == 2 and "aucune valeur" in e["erreur"]


def test_triangle_type_devine_signale():
    d = calculer(["triangle", "--entree", str(RAA)])
    assert d["resultats"]["type_retenu"] == "cumule"
    assert any("incertaine" in a for a in d["avertissements"])


def test_triangle_libelles_excel(tmp_path):
    """Excel lit souvent l'année 2020 comme 2020.0 : le libellé doit rester 2020."""
    f = ecrire(tmp_path / "t.csv", "Origine,1.0,2.0\n2020.0,100,130\n2021.0,110,\n")
    d = calculer(["triangle", "--entree", str(f), "--type", "cumule"])
    assert d["resultats"]["origines"] == ["2020", "2021"]
    assert d["resultats"]["developpements"] == ["1", "2"]


# --- Fichier de primes ---------------------------------------------------------------------------

def test_primes_origine_en_double(tmp_path, capsys):
    lignes = FR_PRIMES.read_text().splitlines()
    f = ecrire(tmp_path / "p.csv", "\n".join(lignes + [lignes[1]]) + "\n")
    code, e = erreur(["cape-cod", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(f)], capsys)
    assert code == 2 and "en double" in e["erreur"]


def test_primes_colonne_prime_absente(tmp_path, capsys):
    f = ecrire(tmp_path / "p.csv", "Origine,Montant\n1998,1\n")
    code, e = erreur(["cape-cod", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(f)], capsys)
    assert code == 2 and "Prime" in e["erreur"]


def test_primes_origine_manquante(tmp_path, capsys):
    lignes = FR_PRIMES.read_text().splitlines()
    f = ecrire(tmp_path / "p.csv", "\n".join(lignes[:-1]) + "\n")
    code, e = erreur(["bf", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(f)], capsys)
    assert code == 2 and "absentes du fichier de primes" in e["erreur"]


def test_primes_origine_en_trop_signalee(tmp_path):
    texte = FR_PRIMES.read_text().rstrip("\n") + "\n2050,1000000,750000\n"
    f = ecrire(tmp_path / "p.csv", texte)
    d = calculer(["bf", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(f)])
    assert any("2050" in a and "ignorées" in a for a in d["avertissements"])


def test_primes_unite_differente_signalee(tmp_path):
    """Primes en milliers alors que le triangle est en unités : ratio ultime / prime aberrant."""
    lignes = FR_PRIMES.read_text().splitlines()
    sortie = [lignes[0]]
    for ligne in lignes[1:]:
        o, p, u = ligne.split(",")
        sortie.append(f"{o},{float(p) / 1000},{float(u) / 1000}")
    f = ecrire(tmp_path / "p.csv", "\n".join(sortie) + "\n")
    d = calculer(["cape-cod", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(f)])
    assert any("même unité" in a for a in d["avertissements"])


def test_primes_coherentes_sans_alerte_unite():
    d = calculer(["cape-cod", "--entree", str(FR_TRI), "--type", "cumule", "--primes", str(FR_PRIMES)])
    assert not any("même unité" in a for a in d["avertissements"])


# --- Options de jugement mal formées -------------------------------------------------------------

@pytest.mark.parametrize("option, valeur, message", [
    ("--exclure", "1981", "origine@facteur"),
    ("--exclure", "1981@1-2@x", "origine@facteur"),
    ("--facteurs-imposes", "1-2", "facteur=valeur"),
    ("--facteurs-imposes", "1-2=1.5,1-2=1.6", "deux fois"),
    ("--facteurs-imposes", "1-2=abc", "non numérique"),
])
def test_options_mal_formees(option, valeur, message, capsys):
    code, e = erreur(["chain-ladder", "--entree", str(RAA), "--type", "cumule", option, valeur], capsys)
    assert code == 2 and message in e["erreur"]


# --- Crédibilité -----------------------------------------------------------------------------------

def test_credibilite_periode_vide(tmp_path, capsys):
    f = ecrire(tmp_path / "c.csv", "Entite,Periode,Ratio,Poids\nA,1,0.5,10\nA,,0.6,10\nB,1,0.7,10\n")
    code, e = erreur(["credibilite", "--entree", str(f)], capsys)
    assert code == 2 and "période vide" in e["erreur"]


def test_credibilite_deux_cohortes(tmp_path, capsys):
    f = ecrire(tmp_path / "c.csv", "Entite,Periode,Ratio,Poids,Cohorte\nA,1,0.5,10,X\nA,2,0.6,10,Y\n"
                                   "B,1,0.7,10,X\nB,2,0.7,10,X\n")
    code, e = erreur(["credibilite", "--entree", str(f), "--modele", "hierarchique"], capsys)
    assert code == 2 and "deux cohortes" in e["erreur"]


# --- Reproductibilité ------------------------------------------------------------------------------

def test_sortie_contient_environnement_et_empreinte():
    d = calculer(["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    env = d["moteur"]["environnement"]
    assert set(env) == {"python", "numpy", "scipy", "pandas"}
    assert re.fullmatch(r"[0-9a-f]{64}", d["empreinte_resultats"])
    assert d["reproduction"]["arguments"] == ["chain-ladder", "--entree", str(RAA), "--type", "cumule"]


def _archiver(tmp_path, argv):
    f = tmp_path / "sortie.json"
    f.write_text(json.dumps(calculer(argv), ensure_ascii=False), encoding="utf-8")
    return f


@pytest.mark.parametrize("argv", [
    ["chain-ladder", "--entree", str(RAA), "--type", "cumule"],
    ["mack", "--entree", str(RAA), "--type", "cumule"],
    ["bootstrap", "--entree", str(RAA), "--type", "cumule", "--simulations", "300", "--graine", "11"],
    ["tarif-vie", "--taux", "0.05", "--type", "mixte", "--age", "40", "--capital", "100000", "--duree", "20"],
])
def test_rejouer_identique(tmp_path, argv):
    d = calculer(["rejouer", "--sortie", str(_archiver(tmp_path, argv))])
    assert d["resultats"]["identique"] is True and d["resultats"]["ecarts"] == []
    assert d["statut"] == "ok"


def test_rejouer_detecte_donnees_modifiees(tmp_path, capsys):
    tri = tmp_path / "raa.csv"
    tri.write_bytes(RAA.read_bytes())
    sortie = _archiver(tmp_path, ["chain-ladder", "--entree", str(tri), "--type", "cumule"])
    tri.write_text(tri.read_text().replace("5012", "5013"), encoding="utf-8")
    code, e = erreur(["rejouer", "--sortie", str(sortie)], capsys)
    assert code == 2 and "a changé" in e["erreur"]


def test_rejouer_detecte_resultats_retouches(tmp_path, capsys):
    sortie = _archiver(tmp_path, ["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    d = json.loads(sortie.read_text(encoding="utf-8"))
    d["resultats"]["total"]["provision"] += 1
    sortie.write_text(json.dumps(d), encoding="utf-8")
    code, e = erreur(["rejouer", "--sortie", str(sortie)], capsys)
    assert code == 2 and "modifiés" in e["erreur"]


def test_rejouer_fichier_qui_nest_pas_une_sortie(tmp_path, capsys):
    f = ecrire(tmp_path / "x.json", '{"a": 1}')
    code, e = erreur(["rejouer", "--sortie", str(f)], capsys)
    assert code == 2 and "reproduction" in e["erreur"]


def test_format_texte_exclu_des_arguments_de_reproduction():
    from cli import _arguments_de_calcul
    assert _arguments_de_calcul(["mack", "--format", "texte", "--entree", "x"]) == ["mack", "--entree", "x"]
    assert _arguments_de_calcul(["mack", "--format=json", "--entree", "x"]) == ["mack", "--entree", "x"]


# --- Versions --------------------------------------------------------------------------------------

def test_versions_synchronisees():
    from actuaire import __version__
    plugin = json.loads((RACINE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    changelog = (RACINE / "CHANGELOG.md").read_text(encoding="utf-8")
    premiere = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M).group(1)
    assert plugin["version"] == __version__ == premiere


# --- Installation réelle de l'archive ------------------------------------------------------------

def test_archive_installee_fonctionne(tmp_path):
    """Construit le zip, l'extrait ailleurs et lance le moteur depuis l'extraction, comme claude.ai."""
    sys.path.insert(0, str(RACINE / "outils"))
    from construire_zip import construire

    archive = construire()
    with zipfile.ZipFile(archive) as z:
        noms = z.namelist()
        assert "calcul-actuariel/SKILL.md" in noms
        assert "calcul-actuariel/references/guide-des-methodes.md" in noms
        assert not [n for n in noms if "__pycache__" in n or n.endswith(".pyc")]
        assert not [n for n in noms if n.startswith(("tests/", "banc_essai/"))]
        z.extractall(tmp_path)
    cli = tmp_path / "calcul-actuariel" / "scripts" / "cli.py"
    env = subprocess.run([sys.executable, str(cli), "environnement"], capture_output=True, text=True, check=True,
                         cwd=tmp_path)
    assert json.loads(env.stdout)["resultats"]["statut"] == "pret"
    cl = subprocess.run([sys.executable, str(cli), "chain-ladder", "--entree", str(RAA), "--type", "cumule"],
                        capture_output=True, text=True, check=True, cwd=tmp_path)
    assert abs(json.loads(cl.stdout)["resultats"]["total"]["provision"] - 52135.23) < 0.01


# --- GPD : intervalles et ajustement -------------------------------------------------------------

def _excedents_danish(seuil=10.0):
    import numpy as np
    x = np.loadtxt(DONNEES / "danish_mcneil.csv", delimiter=",", skiprows=1, usecols=-1)
    return x[x > seuil] - seuil


def test_statistiques_ajustement_comme_scipy():
    """KS et AD recalculés indépendamment par scipy, paramètres fixés."""
    import numpy as np
    from scipy import stats

    from actuaire.extremes import ajuster_gpd, statistiques_ajustement
    y = _excedents_danish()
    xi, sigma, _ = ajuster_gpd(y)
    s = statistiques_ajustement(y, xi, sigma)
    ks = stats.kstest(y, stats.genpareto(c=xi, scale=sigma).cdf).statistic
    assert abs(s["kolmogorov_smirnov"] - ks) < 1e-10
    z = np.sort(stats.genpareto(c=xi, scale=sigma).cdf(y))
    n, i = len(z), np.arange(1, len(z) + 1)
    ad = -n - np.sum((2 * i - 1) * (np.log(z) + np.log(1 - z[::-1]))) / n
    assert abs(s["anderson_darling"] - ad) < 1e-10


def test_intervalle_profil_xi_par_grille():
    """Les bornes profilées annulent bien la déviance profilée au niveau du khi-deux à 1 ddl,
    vérifié par une maximisation indépendante en sigma (scipy, sur une grille fine)."""
    import math

    import numpy as np
    from scipy import optimize, stats

    from actuaire.extremes import ajuster_gpd, intervalle_profil_xi
    y = _excedents_danish()
    xi, sigma, _ = ajuster_gpd(y)
    lo, hi = intervalle_profil_xi(y, xi, sigma)

    def ll(t, s):
        return float(np.sum(stats.genpareto.logpdf(y, c=t, scale=s)))

    def prof(t):
        r = optimize.minimize_scalar(lambda ls: -ll(t, math.exp(ls)), bounds=(-5, 6), method="bounded",
                                     options={"xatol": 1e-10})
        return -r.fun

    l_max = ll(xi, sigma)
    for b in (lo, hi):
        assert abs(2 * (l_max - prof(b)) - stats.chi2.ppf(0.95, 1)) < 1e-4
    assert lo < xi < hi


def test_p_valeur_ajustement_reproductible_et_bornee():
    from actuaire.extremes import ajuster_gpd, p_valeur_ajustement
    y = _excedents_danish()
    xi, sigma, _ = ajuster_gpd(y)
    a = p_valeur_ajustement(y, xi, sigma, 49, 5)
    b = p_valeur_ajustement(y, xi, sigma, 49, 5)
    assert a == b and 0 < a["p_valeur_anderson_darling"] <= 1


def test_p_valeur_detecte_mauvais_modele():
    """Des excès uniformes ne suivent pas une GPD à queue lourde : le test doit les rejeter."""
    import numpy as np

    from actuaire.extremes import p_valeur_ajustement
    y = np.random.default_rng(1).uniform(0, 1, 400) ** 0.2 * 5
    xi, sigma = 0.5, 1.0  # mauvais modèle imposé
    assert p_valeur_ajustement(y, xi, sigma, 49, 3)["p_valeur_anderson_darling"] < 0.05


def test_p_valeur_trop_peu_de_simulations():
    from actuaire.extremes import p_valeur_ajustement
    with pytest.raises(ValueError, match="19"):
        p_valeur_ajustement(_excedents_danish(), 0.5, 7.0, 10, 1)


# --- Vie ---------------------------------------------------------------------------------------------

def test_selection_qui_rend_q_superieur_a_1_refusee(tmp_path, capsys):
    """Avant 0.3.0 : q = 1,8 et espérance de vie négative, avec statut ok."""
    f = ecrire(tmp_path / "qx.csv", "Age,qx\n60,0.8\n61,0.9\n62,1\n")
    code, e = erreur(["survie", "--modele", "table", "--table", str(f), "--taux", "0.03", "--age", "60",
                      "--selection-facteur", "1.5", "--selection-duree", "2"], capsys)
    assert code == 2 and "> 1" in e["erreur"]


@pytest.mark.parametrize("contenu, message", [
    ("Age,qx\n60,0.01\n61,\n", "hors de [0, 1]"),
    ("Age,qx\n60,0.01\n60,0.02\n", "en double"),
    ("Age,qx\n60.5,0.01\n", "entiers"),
    ("Age,q\n60,0.01\n", "colonnes Age et qx"),
    ("Age,qx\n60,0.01\n62,0.02\n", "consécutifs"),
])
def test_table_de_mortalite_invalide(tmp_path, capsys, contenu, message):
    f = ecrire(tmp_path / "qx.csv", contenu)
    code, e = erreur(["survie", "--modele", "table", "--table", str(f), "--taux", "0.03", "--age", "60"], capsys)
    assert code == 2 and message in e["erreur"]


@pytest.mark.parametrize("argv, message", [
    (["--modele", "makeham", "--A", "0.0002"], "exige --A, --B et --c"),
    (["--modele", "table"], "exige --table"),
    (["--selection-facteur", "0.9"], "vont ensemble"),
])
def test_options_de_modele_incompletes(argv, message, capsys):
    code, e = erreur(["survie", "--taux", "0.03", "--age", "60", *argv], capsys)
    assert code == 2 and message in e["erreur"]


@pytest.mark.parametrize("argv, message", [
    (["survie", "--taux", "0.03", "--age", "131"], "au-delà du dernier âge"),
    (["survie", "--taux", "0.03", "--age", "40", "--depuis", "-1"], "positifs ou nuls"),
    (["survie", "--taux", "0.03", "--age", "40", "--n", "0"], "au moins égal à 1"),
    (["tarif-vie", "--taux", "0.03", "--type", "mixte", "--age", "40", "--capital", "1000", "--duree", "10",
      "--durees", "0,5,abc"], "liste d'entiers"),
])
def test_arguments_vie_invalides(argv, message, capsys):
    code, e = erreur(argv, capsys)
    assert code == 2 and message in e["erreur"]


def test_age_avant_le_debut_de_la_table(tmp_path, capsys):
    """Avant 0.3.0 : une table commençant à 60 ans utilisée à 40 ans supposait un décès immédiat."""
    f = ecrire(tmp_path / "qx.csv", "Age,qx\n60,0.01\n61,0.02\n62,1\n")
    code, e = erreur(["tarif-vie", "--modele", "table", "--table", str(f), "--taux", "0.03", "--type",
                      "vie-entiere", "--age", "40", "--capital", "1000"], capsys)
    assert code == 2 and "avant le premier âge" in e["erreur"]


def test_une_seule_periode_refusee(tmp_path, capsys):
    f = ecrire(tmp_path / "t.csv", "Origine,1\n2020,100\n2021,90\n")
    code, e = erreur(["chain-ladder", "--entree", str(f), "--type", "cumule"], capsys)
    assert code == 2 and "une seule période" in e["erreur"]


def test_lecture_excel(tmp_path):
    """Un triangle Excel (années lues comme nombres) donne le même résultat que le CSV."""
    import pandas as pd
    df = pd.read_csv(RAA)
    f = tmp_path / "raa.xlsx"
    df.to_excel(f, index=False, sheet_name="Triangle")
    a = calculer(["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    b = calculer(["chain-ladder", "--entree", str(f), "--feuille", "Triangle", "--type", "cumule"])
    assert a["resultats"]["par_origine"].keys() == b["resultats"]["par_origine"].keys()
    assert abs(a["resultats"]["total"]["provision"] - b["resultats"]["total"]["provision"]) < 1e-6


# --- Ligne de commande : sorties et erreurs -------------------------------------------------------

def test_format_texte(capsys):
    assert main(["chain-ladder", "--entree", str(RAA), "--type", "cumule", "--format", "texte"]) == 0
    out = capsys.readouterr().out
    assert "Méthode : chain-ladder" in out and "sha256" in out and "Hypothèse" in out and "ATTENTION" not in out


def test_erreur_interne_sans_resultat_partiel(monkeypatch, capsys):
    import cli as module_cli
    def plante(args):
        raise RuntimeError("panne simulée")
    monkeypatch.setitem(module_cli.COMMANDES, "chain-ladder", (plante, "", module_cli.COMMANDES["chain-ladder"][2]))
    code = main(["chain-ladder", "--entree", str(RAA)])
    captured = capsys.readouterr()
    assert code == 3 and captured.out == ""
    assert json.loads(captured.err)["erreur"].startswith("erreur interne (RuntimeError)")


def test_fichier_absent(capsys):
    code, e = erreur(["chain-ladder", "--entree", "/nexiste/pas.csv"], capsys)
    assert code == 2 and e["statut"] == "erreur"


def test_rejouer_signale_version_et_environnement_differents(tmp_path):
    sortie = _archiver(tmp_path, ["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    d = json.loads(sortie.read_text(encoding="utf-8"))
    d["moteur"]["version"] = "0.0.1"
    d["moteur"]["environnement"]["numpy"] = "0.0"
    sortie.write_text(json.dumps(d), encoding="utf-8")
    r = calculer(["rejouer", "--sortie", str(sortie)])
    assert r["resultats"]["identique"] is True
    assert any("autre version" in a for a in r["avertissements"])
    assert any("bibliothèques" in a for a in r["avertissements"])


def test_rejouer_signale_les_ecarts(tmp_path):
    """Un résultat archivé différent du recalcul (empreinte recalculée pour simuler un ancien moteur)."""
    from actuaire.sortie import empreinte_resultats
    sortie = _archiver(tmp_path, ["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    d = json.loads(sortie.read_text(encoding="utf-8"))
    d["resultats"]["total"]["provision"] += 1
    d["resultats"]["origines_en_plus"] = [1, 2]
    d["empreinte_resultats"] = empreinte_resultats(d["resultats"])
    sortie.write_text(json.dumps(d), encoding="utf-8")
    r = calculer(["rejouer", "--sortie", str(sortie)])
    assert r["resultats"]["identique"] is False
    assert any("total.provision" in e for e in r["resultats"]["ecarts"])
    assert any("origines_en_plus" in e for e in r["resultats"]["ecarts"])
    assert r["statut"] == "avertissements"


def test_rejouer_une_sortie_de_rejouer_refuse(tmp_path, capsys):
    premiere = _archiver(tmp_path, ["chain-ladder", "--entree", str(RAA), "--type", "cumule"])
    seconde = tmp_path / "rejeu.json"
    seconde.write_text(json.dumps(calculer(["rejouer", "--sortie", str(premiere)])), encoding="utf-8")
    code, e = erreur(["rejouer", "--sortie", str(seconde)], capsys)
    assert code == 2 and "ne se rejoue pas" in e["erreur"]


def test_ecarts_listes_de_longueurs_differentes():
    from cli import _ecarts
    assert _ecarts({"a": [1, 2]}, {"a": [1]}, 1e-9) == ["a : longueurs 2 et 1"]
    assert _ecarts({"a": "x"}, {"a": "y"}, 1e-9) == ["a : 'x' puis 'y'"]
    assert _ecarts({"a": 1.0}, {"a": 1.0 + 1e-12}, 1e-9) == []


# --- GPD : lecture et alertes -----------------------------------------------------------------------

def test_gpd_colonne_et_valeurs_non_numeriques(tmp_path):
    lignes = ["Id,Montant"] + [f"{i},{v}" for i, v in enumerate(_excedents_danish(0.0)[:400] + 1)] + ["999,n/a"]
    f = ecrire(tmp_path / "p.csv", "\n".join(lignes) + "\n")
    d = calculer(["gpd", "--entree", str(f), "--colonne", "Montant", "--seuil", "5",
                  "--diagnostic-seuils", "3,5,10", "--quantiles", "0.9999"])
    assert any("non numérique" in a for a in d["avertissements"])
    assert any("extrapolation forte" in a for a in d["avertissements"])
    assert set(d["resultats"]["excedent_moyen"]) == {"3", "5", "10"}


@pytest.mark.parametrize("contenu, args, message", [
    ("Montant\n1\n-2\n3\n", ["--seuil", "0.5"], "négatifs"),
    ("Montant\n1\n2\n", ["--colonne", "Autre", "--seuil", "0.5"], "colonne introuvable"),
    ("Nom\na\nb\n", ["--seuil", "0.5"], "aucune colonne numérique"),
    ("Montant\n1\n2\n3\n", ["--seuil", "0.5", "--tranche", "1"], "tranche mal formée"),
])
def test_gpd_entrees_invalides(tmp_path, capsys, contenu, args, message):
    f = ecrire(tmp_path / "p.csv", contenu)
    code, e = erreur(["gpd", "--entree", str(f), *args], capsys)
    assert code == 2 and message in e["erreur"]


def test_gpd_queue_tres_lourde_signalee(tmp_path):
    import numpy as np
    y = np.random.default_rng(4).pareto(0.7, 600) + 1  # xi proche de 1,4
    f = ecrire(tmp_path / "p.csv", "Montant\n" + "\n".join(map(str, y)) + "\n")
    d = calculer(["gpd", "--entree", str(f), "--seuil", "2", "--test-ajustement", "19"])
    assert d["resultats"]["xi"] > 1
    assert any("espérance infinie" in a for a in d["avertissements"])
    assert d["resultats"]["ajustement"]["simulations_valides"] >= 19


# --- Crédibilité : régression ----------------------------------------------------------------------

def test_regression_hypotheses_et_barycentre():
    f = DONNEES / "hachemeister.csv"
    a = calculer(["credibilite", "--entree", str(f), "--modele", "regression"])
    b = calculer(["credibilite", "--entree", str(f), "--modele", "regression", "--barycentre",
                  "--periode-future", "13"])
    noms_a = {h["nom"] for h in a["hypotheses"]}
    assert "periode_future" in noms_a
    assert "periode_future" not in {h["nom"] for h in b["hypotheses"]}
    assert any("barycentre" in h["justification"] for h in b["hypotheses"])


def test_notes_de_version_extraites_du_changelog():
    sys.path.insert(0, str(RACINE / "outils"))
    from notes_de_version import section
    texte = "# H\n\n## 0.3.0 (date)\n\nA\n\n## 0.2.0\n\nB\n"
    assert section("0.3.0", texte) == "A\n"
    assert section("0.2.0", texte) == "B\n"
    with pytest.raises(SystemExit):
        section("9.9.9", texte)
