"""Le skill installé seul (plugin ou archive) doit contenir tout ce que SKILL.md cite."""

import re

from conftest import RACINE

SKILL = RACINE / "skills" / "calcul-actuariel"


def test_chaque_reference_citee_existe():
    texte = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    cites = sorted(set(re.findall(r"references/[\w.\-/]+\.md", texte)))
    assert cites, "SKILL.md ne cite aucun fichier references/"
    manquants = [c for c in cites if not (SKILL / c).is_file()]
    assert manquants == [], f"fichiers cités par SKILL.md absents du skill : {manquants}"


def test_les_references_ne_citent_pas_de_fichier_hors_du_skill():
    for md in (SKILL / "references").glob("*.md"):
        texte = md.read_text(encoding="utf-8")
        for c in set(re.findall(r"`references/([\w.\-]+\.md)`", texte)):
            assert (SKILL / "references" / c).is_file(), f"{md.name} cite references/{c}, absent"


FAMILLES = {
    "provisionnement.md": ["controler", "triangle", "chain-ladder", "bf", "cape-cod", "mack", "odp", "bootstrap"],
    "vie.md": ["survie", "tarif-vie"],
    "extremes-reassurance.md": ["gpd", "tranche-xl"],
    "credibilite.md": ["credibilite"],
    "scr.md": ["scr"],
    "tunisie.md": ["marge-solvabilite-tn", "provisions-tn"],
    "dossiers-validation.md": ["rejouer", "registre", "comparer"],
}


def test_skill_md_reste_court():
    taille = len((SKILL / "SKILL.md").read_bytes())
    assert taille < 10_000, f"SKILL.md fait {taille} octets : déplacer le détail dans references/"


def test_chaque_commande_a_une_famille_et_son_fichier_la_decrit():
    texte = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    toutes = {c for cmds in FAMILLES.values() for c in cmds} | {"environnement"}
    import subprocess
    import sys

    aide = subprocess.run([sys.executable, str(SKILL / "scripts" / "cli.py"), "--help"],
                          capture_output=True, text=True, check=True).stdout
    cli_cmds = set(re.search(r"\{([\w,-]+)\}", aide).group(1).split(","))
    assert cli_cmds == toutes, f"commandes sans famille : {cli_cmds - toutes} ; familles en trop : {toutes - cli_cmds}"
    for fichier, cmds in FAMILLES.items():
        assert f"`references/{fichier}`" in texte, f"SKILL.md ne renvoie pas à references/{fichier}"
        contenu = (SKILL / "references" / fichier).read_text(encoding="utf-8")
        for c in cmds:
            assert f"`{c}`" in texte, f"commande {c} absente du tableau de SKILL.md"
            assert f"`{c}" in contenu, f"commande {c} non décrite dans references/{fichier}"
