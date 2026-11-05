"""Construit l'archive à téléverser sur claude.ai : dist/calcul-actuariel.zip.

L'archive contient le dossier du skill à sa racine (SKILL.md + scripts + references),
sans fichiers de cache.

Usage : python outils/construire_zip.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SKILL = RACINE / "skills" / "calcul-actuariel"
DIST = RACINE / "dist"
EXCLUS = {"__pycache__", ".pytest_cache", ".DS_Store"}
# Documents du dépôt copiés dans le skill, pour que Claude puisse les consulter.
DOCUMENTS = {RACINE / "docs" / "guide-des-methodes.md": "references/guide-des-methodes.md"}


def construire() -> Path:
    if not (SKILL / "SKILL.md").exists():
        sys.exit("SKILL.md introuvable")
    DIST.mkdir(exist_ok=True)
    cible = DIST / "calcul-actuariel.zip"
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SKILL.rglob("*")):
            if f.is_file() and not (EXCLUS & set(f.parts)) and f.suffix != ".pyc":
                z.write(f, Path("calcul-actuariel") / f.relative_to(SKILL))
        for source, cible_zip in DOCUMENTS.items():
            z.write(source, Path("calcul-actuariel") / cible_zip)
    return cible


if __name__ == "__main__":
    chemin = construire()
    with zipfile.ZipFile(chemin) as z:
        noms = z.namelist()
    print(f"{chemin} : {len(noms)} fichiers")
    for n in noms:
        print("  " + n)
