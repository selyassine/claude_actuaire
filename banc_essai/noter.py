"""Note les réponses du banc d'essai contre les corrigés.

Organisation attendue :
    banc_essai/taches/<id_tache>/corrige.yaml      valeurs attendues et tolérances
    banc_essai/reponses/<condition>/<id_tache>/<essai>.md   réponse brute de Claude

Format de corrige.yaml :
    famille: chain_ladder
    valeurs:
      - nom: ibnr_total
        attendu: 123456
        tolerance_absolue: 0.5      # ou tolerance_relative: 0.02

Usage : python banc_essai/noter.py [--reponses banc_essai/reponses]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

ICI = Path(__file__).resolve().parent
BLOC = re.compile(r"```resultats\s*\n(.*?)```", re.S)


def extraire_resultats(texte: str) -> dict:
    """Dernier bloc ```resultats``` de la réponse, ou {} s'il est absent ou illisible."""
    blocs = BLOC.findall(texte)
    if not blocs:
        return {}
    try:
        d = json.loads(blocs[-1])
    except json.JSONDecodeError:
        return {}
    return d if isinstance(d, dict) else {}


def juste(obtenu, attendu: dict) -> bool:
    try:
        x = float(obtenu)
    except (TypeError, ValueError):
        return False
    cible = float(attendu["attendu"])
    if "tolerance_relative" in attendu:
        return abs(x - cible) <= abs(cible) * float(attendu["tolerance_relative"])
    return abs(x - cible) <= float(attendu.get("tolerance_absolue", 0.5))


def noter(dossier_reponses: Path, dossier_taches: Path) -> dict:
    scores: dict = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # condition -> famille -> [justes, total]
    for cond in sorted(p for p in dossier_reponses.iterdir() if p.is_dir()):
        for tache in sorted(p for p in cond.iterdir() if p.is_dir()):
            corrige = yaml.safe_load((dossier_taches / tache.name / "corrige.yaml").read_text("utf-8"))
            for essai in sorted(tache.glob("*.md")):
                res = extraire_resultats(essai.read_text("utf-8"))
                for v in corrige["valeurs"]:
                    ok = juste(res.get(v["nom"]), v)
                    for fam in (corrige["famille"], "ensemble"):
                        scores[cond.name][fam][0] += ok
                        scores[cond.name][fam][1] += 1
    return {c: {f: {"justes": j, "total": t, "taux": round(j / t, 4) if t else None}
                for f, (j, t) in fams.items()} for c, fams in scores.items()}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reponses", default=str(ICI / "reponses"))
    p.add_argument("--taches", default=str(ICI / "taches"))
    a = p.parse_args()
    print(json.dumps(noter(Path(a.reponses), Path(a.taches)), ensure_ascii=False, indent=2))
