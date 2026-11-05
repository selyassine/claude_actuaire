"""Version 0.4.0 : tarification annuelle d'une tranche XL et commande comparer.

Les valeurs de référence de la tranche XL sont dans les fiches r-*-tranche-xl-*.yaml (calcul R
indépendant). Ce fichier teste les propriétés, les cas limites et les refus."""

import json
import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from actuaire.reassurance import discretiser_charge, panjer_poisson
from cli import calculer, main
from conftest import RACINE

DANISH = str(RACINE / "tests" / "donnees" / "danish_mcneil.csv")
RAA = str(RACINE / "tests" / "donnees" / "raa_cumule.csv")
BASE = ["tranche-xl", "--entree", DANISH, "--seuil", "10", "--annees", "11"]


def erreur(argv, capsys):
    code = main(argv)
    err = capsys.readouterr().err
    return code, (json.loads(err) if err.strip() else {})


# --- Tranche XL : cohérence ----------------------------------------------------------------------

def test_prime_annuelle_coherente_avec_la_prime_par_sinistre_de_mcneil():
    """Prime annuelle = prime par sinistre (commande gpd, McNeil 1997) × nombre de sinistres par an."""
    xl = calculer(BASE + ["--tranche", "50,200"])["resultats"]
    gpd = calculer(["gpd", "--entree", DANISH, "--seuil", "10", "--tranche", "50,200"])["resultats"]
    attendu = gpd["tranches"]["50-200"]["prime_pure"] * gpd["n"] / 11
    assert xl["prime_pure_annuelle"] == pytest.approx(attendu, rel=1e-9)
    assert xl["xi"] == pytest.approx(gpd["xi"], abs=1e-12)


def test_discretisation_proche_de_la_prime_exacte():
    r = calculer(BASE + ["--tranche", "50,200"])["resultats"]
    assert abs(r["discretisation"]["ecart_relatif_prime"]) < 1e-5
    assert r["var"]["0.99"] <= r["esperance_conditionnelle_queue"]["0.99"]
    assert r["var"]["0.99"] <= r["var"]["0.995"]


def test_sans_conditions_annuelles_pas_de_bloc():
    r = calculer(BASE + ["--tranche", "50,200"])["resultats"]
    assert "conditions_annuelles" not in r


def test_franchise_seule_sans_limite():
    c = calculer(BASE + ["--tranche", "50,200", "--franchise-annuelle", "10"])["resultats"]["conditions_annuelles"]
    assert c["limite_annuelle"] is None and c["probabilite_limite_epuisee"] is None
    assert 0 < c["prime_pure_annuelle"]


def test_conditions_annuelles_reduisent_la_prime():
    sans = calculer(BASE + ["--tranche", "50,200"])["resultats"]["prime_pure_annuelle"]
    avec = calculer(BASE + ["--tranche", "50,200", "--franchise-annuelle", "20", "--limite-annuelle", "300"])
    assert avec["resultats"]["conditions_annuelles"]["prime_pure_annuelle"] < sans


def test_panjer_reproduit_une_loi_de_poisson():
    """Sévérité 0 ou 1 : S suit une loi de Poisson de paramètre lambda × P(L = 1)."""
    g = panjer_poisson(3.0, np.array([0.6, 0.4]))
    k = np.arange(len(g))
    assert np.allclose(g, stats.poisson.pmf(k, 1.2), atol=1e-14)
    assert abs(g.sum() - 1) < 1e-11


def test_panjer_reproduit_la_convolution_directe():
    f, lam = np.array([0.2, 0.5, 0.3]), 0.7
    g = panjer_poisson(lam, f)
    direct = np.zeros(40)
    conv = np.zeros(40)
    conv[0] = 1.0
    for n in range(30):
        direct += stats.poisson.pmf(n, lam) * conv
        conv = np.convolve(conv, f)[:40]
    assert np.allclose(g[:20], direct[:20], atol=1e-13)


def test_discretisation_somme_a_un_et_porte_l_epuisement_sur_le_dernier_point():
    f = discretiser_charge(10, 0.5, 7, 50, 200, 1.5)
    assert len(f) == 101 and abs(f.sum() - 1) < 1e-12 and f[-1] > 0


def test_support_borne_xi_negatif():
    """xi < 0 : au-delà de u - sigma/xi aucun sinistre n'existe, la tranche n'est jamais épuisée."""
    r = calculer(BASE + ["--tranche", "20,100", "--parametres=-0.3,10"])["resultats"]
    assert r["probabilite_sinistre_epuise_tranche"] == 0
    assert r["prime_pure_annuelle"] > 0


def test_tranche_au_dessus_des_donnees_avertit(capsys):
    d = calculer(BASE + ["--tranche", "150,300"])
    assert any("burning cost n'est pas fiable" in a for a in d["avertissements"])


def test_peu_de_depassements_avertit():
    d = calculer(["tranche-xl", "--entree", DANISH, "--seuil", "60", "--annees", "11", "--tranche", "60,200"])
    assert any("dépassements du seuil" in a for a in d["avertissements"])


def test_pas_grossier_signale_l_ecart_de_discretisation():
    d = calculer(BASE + ["--tranche", "50,200", "--pas", "75"])
    assert any("discrétisation écarte la prime" in a for a in d["avertissements"])


def test_tranche_xl_se_rejoue(tmp_path):
    f = tmp_path / "xl.json"
    f.write_text(json.dumps(calculer(BASE + ["--tranche", "50,200"])), encoding="utf-8")
    assert calculer(["rejouer", "--sortie", str(f)])["resultats"]["identique"]


# --- Tranche XL : refus --------------------------------------------------------------------------

@pytest.mark.parametrize("options,message", [
    (["--tranche", "5,200"], "au moins égale au seuil"),
    (["--tranche", "200,50"], "doit dépasser la priorité"),
    (["--tranche", "50"], "tranche mal formée"),
    (["--tranche", "50,200", "--pas", "7"], "doit diviser la portée"),
    (["--tranche", "50,200", "--pas", "0"], "pas de discrétisation invalide"),
    (["--tranche", "50,200", "--niveaux", "1.2"], "niveau hors"),
    (["--tranche", "50,200", "--parametres", "0.5,-1"], "paramètres GPD imposés invalides"),
    (["--tranche", "50,200", "--parametres", "0.5"], "paramètres mal formés"),
    (["--tranche", "50,200", "--limite-annuelle", "0"], "limite annuelle"),
    (["--tranche", "50,200", "--franchise-annuelle", "-1"], "franchise annuelle négative"),
])
def test_tranche_xl_refus(options, message, capsys):
    code, e = erreur(BASE + options, capsys)
    assert code == 2 and message in e["erreur"]


@pytest.mark.parametrize("annees", ["0", "-3", "nan"])
def test_tranche_xl_refuse_des_annees_invalides(annees, capsys):
    code, e = erreur(["tranche-xl", "--entree", DANISH, "--seuil", "10", "--annees", annees, "--tranche", "50,200"],
                     capsys)
    assert code == 2 and "années" in e["erreur"]


def test_tranche_xl_refuse_un_seuil_sans_depassement(tmp_path, capsys):
    f = tmp_path / "p.csv"
    f.write_text("Montant\n1\n2\n3\n", encoding="utf-8")
    code, e = erreur(["tranche-xl", "--entree", str(f), "--seuil", "10", "--annees", "1", "--tranche", "10,20",
                      "--parametres", "0.5,2"], capsys)
    assert code == 2 and "aucune perte au-dessus" in e["erreur"]


def test_tranche_xl_refuse_des_montants_negatifs(tmp_path, capsys):
    f = tmp_path / "p.csv"
    f.write_text("Montant\n12\n-2\n30\n", encoding="utf-8")
    code, e = erreur(["tranche-xl", "--entree", str(f), "--seuil", "10", "--annees", "1", "--tranche", "10,20"], capsys)
    assert code == 2 and "négatifs" in e["erreur"]


def test_frequence_trop_elevee_refusee():
    with pytest.raises(ValueError, match="fréquence trop élevée"):
        panjer_poisson(800.0, np.array([0.0, 1.0]))


# --- Commande comparer ---------------------------------------------------------------------------

@pytest.fixture()
def sortie_cl(tmp_path):
    d = calculer(["chain-ladder", "--entree", RAA])
    f = tmp_path / "cl.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    return f, d["resultats"]


def externe(tmp_path, lignes, entete="chemin;valeur"):
    f = tmp_path / "ext.csv"
    f.write_text(entete + "\n" + "\n".join(lignes) + "\n", encoding="utf-8")
    return str(f)


def comparer(f, ext, *opts):
    return calculer(["comparer", "--resultats", str(f), "--externe", ext, *opts])


def test_comparer_tout_conforme(tmp_path, sortie_cl):
    f, r = sortie_cl
    lignes = [f"par_origine.{o}.ultime;{v['ultime']!r}" for o, v in r["par_origine"].items()]
    d = comparer(f, externe(tmp_path, lignes))
    assert d["resultats"]["conclusion"] == "conforme"
    assert d["resultats"]["decompte"]["conforme"] == len(lignes)
    assert d["resultats"]["chemins_moteur_non_compares"] > 0


def test_comparer_accepte_le_prefixe_resultats_et_les_listes(tmp_path, sortie_cl):
    f, r = sortie_cl
    d = comparer(f, externe(tmp_path, [f"resultats.facteurs.1-2;{r['facteurs']['1-2']!r}"]))
    assert d["resultats"]["lignes"][0]["statut"] == "conforme"


def test_comparer_reconnait_un_arrondi_publie(tmp_path, sortie_cl):
    f, r = sortie_cl
    u = r["par_origine"]["1990"]["ultime"]  # 18402,4425...
    texte = f"{u:.1f}".replace(".", ",")
    d = comparer(f, externe(tmp_path, [f"par_origine.1990.ultime;{texte}"]), "--tolerance-relative", "0")
    assert d["resultats"]["lignes"][0]["statut"] == "arrondi"
    assert d["resultats"]["conclusion"] == "conforme"


def test_comparer_detecte_un_facteur_d_unite(tmp_path, sortie_cl):
    f, r = sortie_cl
    lignes = [f"par_origine.{o}.ultime;{v['ultime'] / 1000!r}" for o, v in list(r["par_origine"].items())[:4]]
    d = comparer(f, externe(tmp_path, lignes))
    assert d["resultats"]["conclusion"] == "ecarts_a_analyser"
    assert any("milliers" in a for a in d["avertissements"])


def test_comparer_detecte_une_convention_de_signe(tmp_path, sortie_cl):
    f, r = sortie_cl
    lignes = [f"par_origine.{o}.ultime;{-v['ultime']!r}" for o, v in list(r["par_origine"].items())[:3]]
    d = comparer(f, externe(tmp_path, lignes))
    assert any("signe" in a for a in d["avertissements"])


def test_comparer_facteur_commun_inconnu(tmp_path, sortie_cl):
    f, r = sortie_cl
    lignes = [f"par_origine.{o}.ultime;{v['ultime'] * 1.05!r}" for o, v in list(r["par_origine"].items())[:3]]
    d = comparer(f, externe(tmp_path, lignes))
    assert any("hypothèse commune" in a for a in d["avertissements"])


def test_comparer_tolerance_par_ligne(tmp_path, sortie_cl):
    f, r = sortie_cl
    u = r["par_origine"]["1990"]["ultime"]
    d = comparer(f, externe(tmp_path, [f"par_origine.1990.ultime;{u * 1.01!r};0.02"],
                            "chemin;valeur;tolerance_relative"))
    assert d["resultats"]["lignes"][0]["statut"] == "conforme"


def test_comparer_chemin_absent_et_valeur_invalide(tmp_path, sortie_cl):
    f, _ = sortie_cl
    d = comparer(f, externe(tmp_path, ["inexistant;3", "par_origine.1990.ultime;abc", "par_origine.1990;5"]))
    st = [li["statut"] for li in d["resultats"]["lignes"]]
    assert st == ["chemin_absent", "valeur_externe_invalide", "non_numerique_moteur"]
    assert d["resultats"]["conclusion"] == "ecarts_a_analyser"


def test_comparer_valeur_moteur_nulle(tmp_path):
    d = calculer(["chain-ladder", "--entree", RAA])
    f = tmp_path / "cl.json"
    d["resultats"]["zero"] = 0.0
    from actuaire.sortie import empreinte_resultats
    d["empreinte_resultats"] = empreinte_resultats(d["resultats"])
    f.write_text(json.dumps(d), encoding="utf-8")
    r = comparer(f, externe(tmp_path, ["zero;0", "queue;1"]))["resultats"]
    assert [li["statut"] for li in r["lignes"]] == ["conforme", "conforme"]


def test_comparer_fichier_excel(tmp_path, sortie_cl):
    f, r = sortie_cl
    x = tmp_path / "ext.xlsx"
    pd.DataFrame({"Chemin": ["par_origine.1990.ultime"], "Valeur": [r["par_origine"]["1990"]["ultime"]],
                  "Libelle": ["ultime 1990"]}).to_excel(x, index=False)
    d = comparer(f, str(x))
    assert d["resultats"]["lignes"][0]["statut"] == "conforme"
    assert d["resultats"]["lignes"][0]["libelle"] == "ultime 1990"


def test_comparer_lister(sortie_cl):
    f, _ = sortie_cl
    d = calculer(["comparer", "--resultats", str(f), "--lister"])
    assert "resultats.par_origine.1990.ultime" in d["resultats"]["chemins_disponibles"]


def test_comparer_refuse_une_sortie_modifiee(tmp_path, sortie_cl, capsys):
    f, _ = sortie_cl
    d = json.loads(f.read_text(encoding="utf-8"))
    d["resultats"]["par_origine"]["1990"]["ultime"] = 1.0
    f.write_text(json.dumps(d), encoding="utf-8")
    code, e = erreur(["comparer", "--resultats", str(f), "--lister"], capsys)
    assert code == 2 and "modifiés" in e["erreur"]


@pytest.mark.parametrize("contenu,message", [
    ("autre;valeur\nx;1\n", "colonnes 'chemin' et 'valeur'"),
    ("chemin;valeur\nqueue;1\nqueue;1\n", "en double"),
    ("chemin;valeur\n;1\n", "pas de chemin"),
    ("chemin;valeur\n", "aucune ligne"),
    ("chemin;valeur;tolerance_relative\nqueue;1;-2\n", "tolérance invalide"),
])
def test_comparer_refus_fichier_externe(tmp_path, sortie_cl, contenu, message, capsys):
    f, _ = sortie_cl
    x = tmp_path / "e.csv"
    x.write_text(contenu, encoding="utf-8")
    code, e = erreur(["comparer", "--resultats", str(f), "--externe", str(x)], capsys)
    assert code == 2 and message in e["erreur"]


def test_comparer_refus_divers(tmp_path, sortie_cl, capsys):
    f, _ = sortie_cl
    code, e = erreur(["comparer", "--resultats", str(f)], capsys)
    assert code == 2 and "--externe est obligatoire" in e["erreur"]
    code, e = erreur(["comparer", "--resultats", str(f), "--lister", "--tolerance-relative", "-1"], capsys)
    assert code == 2 and "positives" in e["erreur"]
    autre = tmp_path / "a.json"
    autre.write_text(json.dumps({"x": 1}), encoding="utf-8")
    code, e = erreur(["comparer", "--resultats", str(autre), "--lister"], capsys)
    assert code == 2 and "pas une sortie JSON du moteur" in e["erreur"]


def test_comparer_signale_une_sortie_avec_avertissements(tmp_path, sortie_cl):
    f, r = sortie_cl
    d = comparer(f, externe(tmp_path, [f"queue;{r['queue']!r}"]))
    statut = json.loads(f.read_text(encoding="utf-8"))["statut"]
    assert (statut == "ok") or any("statut" in a for a in d["avertissements"])


def test_demi_unite_publiee():
    from actuaire.cli_validation import demi_unite_publiee
    assert demi_unite_publiee("1 234,5") == pytest.approx(0.05)
    assert demi_unite_publiee("1,234.56") == pytest.approx(0.005)
    assert demi_unite_publiee("52135") == 0.5
    assert demi_unite_publiee("1e3") is None
    assert demi_unite_publiee("abc") is None
    assert not math.isnan(demi_unite_publiee("-0.25"))


# --- Commande controler (0.4.1) ------------------------------------------------------------------

def controle(tmp_path, texte, *opts, nom="f.csv"):
    f = tmp_path / nom
    f.write_text(texte, encoding="utf-8")
    return calculer(["controler", "--entree", str(f), *opts])["resultats"]


def codes(r):
    return {a["code"]: a["gravite"] for a in r["anomalies"]}


def test_controler_raa_signale_la_baisse_et_le_facteur_atypique():
    r = calculer(["controler", "--entree", RAA, "--nature", "triangle", "--type", "cumule"])["resultats"]
    assert r["conclusion"] == "a_examiner" and r["decompte"]["bloquant"] == 0
    assert codes(r) == {"baisse_du_cumule": "alerte", "facteur_atypique": "alerte"}
    atypique = next(a for a in r["anomalies"] if a["code"] == "facteur_atypique")
    assert atypique["lieu"] == "origine 1982, facteur 3-4" and "--exclure '1982@3-4'" in atypique["message"]


def test_controler_triangle_propre():
    r = calculer(["controler", "--entree", str(RACINE / "tests/donnees/friedland_us_auto_declares.csv"),
                  "--nature", "triangle", "--type", "cumule"])["resultats"]
    assert r["conclusion"] == "pret" and r["anomalies"] == []


def test_controler_triangle_toutes_les_anomalies_bloquantes(tmp_path):
    texte = ("Origine,1,2,3,3\n2020,100,abc,130,1\n2020,110,,inf,\n,120,,,\n2023,,,,\n")
    r = controle(tmp_path, texte, "--nature", "triangle", "--type", "cumule")
    c = codes(r)
    for code in ("origine_en_double", "periode_en_double", "texte_non_numerique", "valeur_infinie",
                 "origine_sans_libelle", "ligne_vide", "trou"):
        assert c[code] == "bloquant", code
    assert r["conclusion"] == "bloquant"
    assert r["anomalies"][0]["gravite"] == "bloquant"


def test_controler_triangle_alertes(tmp_path):
    texte = "Origine,1,2,3\n2020,0,50,40\n2021,-5,10,\n2022,10,,\n"
    r = controle(tmp_path, texte, "--nature", "triangle", "--type", "cumule")
    c = codes(r)
    assert c["zero_puis_positif"] == "alerte" and c["valeur_negative"] == "alerte"
    assert c["baisse_du_cumule"] == "alerte"


def test_controler_triangle_incremental_cumule_pour_les_facteurs(tmp_path):
    texte = "Origine,1,2\n2020,0,5\n2021,10,2\n"
    r = controle(tmp_path, texte, "--nature", "triangle", "--type", "incremental")
    assert "zero_puis_positif" in codes(r) and "baisse_du_cumule" not in codes(r)


def test_controler_triangle_forme_et_une_periode(tmp_path):
    r = controle(tmp_path, "Origine,1,2\n2020,1,\n2021,1,2\n", "--nature", "triangle")
    assert codes(r)["forme_inattendue"] == "alerte" and codes(r)["type_devine"] == "info"
    r = controle(tmp_path, "Origine,1\n2020,1\n", "--nature", "triangle")
    assert codes(r)["une_seule_periode"] == "bloquant"
    r = controle(tmp_path, "Origine\n2020\n", "--nature", "triangle")
    assert codes(r) == {"triangle_vide": "bloquant"}


def test_controler_sinistres(tmp_path):
    texte = "Id,Montant\n1,10\n2,abc\n3,0\n4,-2\n5,10\n6,\n7,500\n8,inf\n"
    r = controle(tmp_path, texte, "--nature", "sinistres", "--colonne", "Montant")
    c = codes(r)
    assert c["montant_negatif"] == "bloquant" and c["valeur_infinie"] == "bloquant"
    assert c["texte_non_numerique"] == "alerte" and c["montants_nuls"] == "alerte"
    assert c["montants_repetes"] == "alerte" and c["maximum_isole"] == "info" and c["cellules_vides"] == "info"
    assert r["resume"]["colonne"] == "Montant"


def test_controler_sinistres_colonne_absente_ou_aucune(tmp_path):
    assert codes(controle(tmp_path, "A\n1\n", "--nature", "sinistres", "--colonne", "X")) == {"colonne_introuvable": "bloquant"}
    assert codes(controle(tmp_path, "A\nx\ny\n", "--nature", "sinistres")) == {"aucune_colonne_numerique": "bloquant"}
    assert codes(controle(tmp_path, "A\n", "--nature", "sinistres")) == {"fichier_vide": "bloquant"}


def test_controler_sinistres_danois_detecte_la_colonne():
    r = calculer(["controler", "--entree", DANISH, "--nature", "sinistres"])["resultats"]
    assert r["resume"]["n_montants"] == 2167 and r["decompte"]["bloquant"] == 0


def test_controler_primes(tmp_path):
    tri = tmp_path / "t.csv"
    tri.write_text("Origine,1,2\n2020,1,2\n2021,1,\n2022,1,\n", encoding="utf-8")
    texte = "Origine,Prime,Ratio\n2020,100,0.6\n2020,100,0.6\n2021,0,65\n2023,-1,x\n,5,\n2024,,\n"
    r = controle(tmp_path, texte, "--nature", "primes", "--triangle", str(tri), nom="p.csv")
    c = codes(r)
    for code in ("origine_en_double", "valeur_negative", "texte_non_numerique", "origine_sans_libelle",
                 "prime_manquante", "origines_manquantes"):
        assert c[code] == "bloquant", code
    assert c["prime_nulle"] == "alerte" and c["ratio_eleve"] == "alerte" and c["origines_en_trop"] == "alerte"


def test_controler_primes_sans_colonne_ou_vide(tmp_path):
    assert codes(controle(tmp_path, "Origine,P\n2020,1\n", "--nature", "primes")) == {"colonne_prime_absente": "bloquant"}
    assert codes(controle(tmp_path, "Origine,Prime\n", "--nature", "primes")) == {"fichier_vide": "bloquant"}


def test_controler_primes_friedland_pret():
    r = calculer(["controler", "--entree", str(RACINE / "tests/donnees/friedland_us_auto_primes.csv"), "--nature",
                  "primes", "--triangle", str(RACINE / "tests/donnees/friedland_us_auto_declares.csv")])
    assert r["resultats"]["conclusion"] == "pret" and r["statut"] == "ok"
    assert len(r["entrees"]) == 2


def test_controler_coherent_avec_le_refus_des_methodes(tmp_path, capsys):
    """Ce que controler classe bloquant, la méthode le refuse."""
    f = tmp_path / "t.csv"
    f.write_text("Origine,1,2,3\n2020,100,,130\n2021,110,140,\n2022,120,,\n", encoding="utf-8")
    r = calculer(["controler", "--entree", str(f), "--nature", "triangle", "--type", "cumule"])["resultats"]
    assert r["conclusion"] == "bloquant"
    code, _ = erreur(["chain-ladder", "--entree", str(f), "--type", "cumule"], capsys)
    assert code == 2


def test_periode_en_double_refusee_par_les_methodes(tmp_path, capsys):
    """Avant 0.4.1 : pandas renommait la seconde période « 2 » en « 2.1 » et le calcul passait."""
    f = tmp_path / "t.csv"
    f.write_text("Origine,1,2,2\n2020,1,2,3\n2021,1,2,\n2022,1,,\n", encoding="utf-8")
    code, e = erreur(["chain-ladder", "--entree", str(f), "--type", "cumule"], capsys)
    assert code == 2 and "périodes de développement en double" in e["erreur"]
    r = calculer(["controler", "--entree", str(f), "--nature", "triangle", "--type", "cumule"])["resultats"]
    assert codes(r)["periode_en_double"] == "bloquant"


def test_colonne_en_double_refusee_ailleurs(tmp_path, capsys):
    f = tmp_path / "s.csv"
    f.write_text("Montant,Montant\n12,3\n30,4\n", encoding="utf-8")
    code, e = erreur(["gpd", "--entree", str(f), "--seuil", "1"], capsys)
    assert code == 2 and "colonne(s) en double" in e["erreur"]
    r = calculer(["controler", "--entree", str(f), "--nature", "sinistres"])["resultats"]
    assert codes(r) == {"colonne_en_double": "bloquant"}


def test_entetes_excel_numeriques(tmp_path):
    x = tmp_path / "t.xlsx"
    pd.DataFrame([[2020, 100, 150], [2021, 110, None]], columns=["Origine", 12, 24]).to_excel(x, index=False)
    r = calculer(["chain-ladder", "--entree", str(x), "--type", "cumule"])["resultats"]
    assert list(r["facteurs"]) == ["12-24"]
