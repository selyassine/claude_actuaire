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
