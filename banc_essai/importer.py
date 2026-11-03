"""Découpe reponses_a_remplir.md en banc_essai/reponses/<condition>/<tâche>/1.md.

Usage : python banc_essai/importer.py banc_essai/reponses_a_remplir.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
TITRE = re.compile(r"^## ([ABC]) ([a-z0-9-]+)\s*$", re.M)


def importer(fichier: Path, sortie: Path = ICI / "reponses") -> int:
    texte = fichier.read_text("utf-8")
    morceaux = TITRE.split(texte)
    n = 0
    for i in range(1, len(morceaux), 3):
        cond, tache, contenu = morceaux[i], morceaux[i + 1], morceaux[i + 2].strip()
        if not contenu:
            continue
        if not (ICI / "taches" / tache).is_dir():
            raise ValueError(f"tâche inconnue : {tache}")
        d = sortie / cond / tache
        d.mkdir(parents=True, exist_ok=True)
        (d / "1.md").write_text(contenu + "\n", encoding="utf-8")
        n += 1
    return n


if __name__ == "__main__":
    print(f"{importer(Path(sys.argv[1]))} réponse(s) importée(s)")
