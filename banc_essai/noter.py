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
import sys
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


def noter(dossier_reponses: Path, dossier_taches: Path, conditions: list[str] | None = None,
          taches: list[str] | None = None, repetitions: int = 1) -> dict:
    """Taux de bonnes valeurs par condition et par famille, sur la liste COMPLÈTE des essais attendus.

    Essais attendus : chaque condition × chaque tâche × repetitions (au moins). Par défaut, les conditions
    sont les dossiers présents et les tâches sont toutes celles de dossier_taches. Un essai manquant compte
    toutes ses valeurs comme fausses, pour qu'une campagne incomplète ne gonfle pas le score. La clé
    "completude" liste les essais manquants et les dossiers de réponse sans corrigé.
    """
    if repetitions < 1:
        raise ValueError("repetitions doit valoir au moins 1")
    corriges = {p.name: yaml.safe_load((p / "corrige.yaml").read_text("utf-8"))
                for p in sorted(dossier_taches.iterdir()) if (p / "corrige.yaml").is_file()}
    taches = sorted(corriges) if taches is None else list(taches)
    inconnues = [t for t in taches if t not in corriges]
    if inconnues:
        raise ValueError(f"tâches sans corrigé : {inconnues}")
    presentes = sorted(p.name for p in dossier_reponses.iterdir() if p.is_dir()) if dossier_reponses.is_dir() else []
    conditions = presentes if conditions is None else list(conditions)

    scores: dict = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # condition -> famille -> [justes, total]
    manquants, sans_corrige = [], []
    for cond in conditions:
        dcond = dossier_reponses / cond
        if dcond.is_dir():
            sans_corrige += [f"{cond}/{p.name}" for p in sorted(dcond.iterdir())
                             if p.is_dir() and p.name not in corriges]
        for t in taches:
            corrige = corriges[t]
            essais = sorted((dcond / t).glob("*.md")) if (dcond / t).is_dir() else []
            textes = [e.read_text("utf-8") for e in essais]
            if len(textes) < repetitions:
                manquants += [f"{cond}/{t}/{k + 1}" for k in range(len(textes), repetitions)]
                textes += [""] * (repetitions - len(textes))
            for texte in textes:
                res = extraire_resultats(texte)
                for v in corrige["valeurs"]:
                    ok = juste(res.get(v["nom"]), v)
                    for fam in (corrige["famille"], "ensemble"):
                        scores[cond][fam][0] += ok
                        scores[cond][fam][1] += 1
    out = {c: {f: {"justes": j, "total": t, "taux": round(j / t, 4) if t else None}
               for f, (j, t) in fams.items()} for c, fams in scores.items()}
    out["completude"] = {"conditions": conditions, "taches": len(taches), "repetitions": repetitions,
                         "essais_manquants": manquants, "reponses_sans_corrige": sans_corrige}
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reponses", default=str(ICI / "reponses"))
    p.add_argument("--taches", default=str(ICI / "taches"))
    p.add_argument("--conditions", help="conditions attendues, ex. A,B,C (défaut : dossiers présents)")
    p.add_argument("--seulement", help="tâches attendues, ex. scr-01,scr-02 (défaut : toutes celles de --taches)")
    p.add_argument("--repetitions", type=int, default=1, help="réponses attendues par condition et par tâche")
    a = p.parse_args()
    d = noter(Path(a.reponses), Path(a.taches),
              a.conditions.split(",") if a.conditions else None,
              a.seulement.split(",") if a.seulement else None, a.repetitions)
    print(json.dumps(d, ensure_ascii=False, indent=2))
    if d["completude"]["essais_manquants"]:
        print(f"ATTENTION : {len(d['completude']['essais_manquants'])} essai(s) manquant(s), comptés faux.",
              file=sys.stderr)
