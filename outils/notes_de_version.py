"""Extrait du CHANGELOG la section d'une version, pour les notes de publication GitHub.

Usage : python outils/notes_de_version.py 0.3.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def section(version: str, texte: str) -> str:
    m = re.search(rf"^## {re.escape(version)}\b.*?$(.*?)(?=^## |\Z)", texte, re.M | re.S)
    if not m:
        raise SystemExit(f"version {version} absente du CHANGELOG")
    return m.group(1).strip() + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage : python outils/notes_de_version.py <version>")
    print(section(sys.argv[1], CHANGELOG.read_text(encoding="utf-8")), end="")
