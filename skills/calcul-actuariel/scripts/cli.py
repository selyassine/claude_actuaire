"""Point d'entrée unique du moteur de calcul actuariel.

Usage :
    python cli.py <commande> [options]
    python cli.py --help
    python cli.py <commande> --help

Chaque commande écrit un JSON traçable sur la sortie standard
(ou un résumé lisible avec --format texte).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from actuaire import __version__  # noqa: E402
from actuaire.sortie import Hypothese, Resultat  # noqa: E402
from actuaire.triangle import lire_triangle  # noqa: E402


def cmd_environnement(args: argparse.Namespace) -> Resultat:
    import numpy
    import pandas
    import scipy

    return Resultat(
        methode="environnement",
        resultats={
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "pandas": pandas.__version__,
            "moteur": __version__,
            "statut": "pret",
        },
    )


def cmd_triangle(args: argparse.Namespace) -> Resultat:
    tri = lire_triangle(args.entree, args.feuille)
    cumule = tri.semble_cumule() if args.type == "auto" else args.type == "cumule"
    res = Resultat(
        methode="triangle",
        options={"type": args.type, "feuille": args.feuille},
        resultats={
            "n_origines": tri.n_origines,
            "n_developpements": tri.n_dev,
            "origines": tri.origines,
            "developpements": tri.developpements,
            "type_retenu": "cumule" if cumule else "incremental",
            "derniere_diagonale_cumulee": dict(
                zip(tri.origines, (tri if cumule else tri.en_cumule()).derniere_diagonale())
            ),
        },
    )
    res.ajouter_entree(args.entree)
    if args.type == "auto":
        res.hypotheses.append(
            Hypothese(
                nom="type_de_triangle",
                valeur=res.resultats["type_retenu"],
                justification="Détecté automatiquement : lignes croissantes = cumulé.",
                source="valeur par défaut",
            )
        )
    res.avertissements.extend(tri.controles())
    return res


COMMANDES = {
    "environnement": (cmd_environnement, "Vérifie que le moteur et ses dépendances sont disponibles."),
    "triangle": (cmd_triangle, "Lit un triangle, contrôle sa forme et donne la dernière diagonale."),
}


def construire_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"claude_actuaire {__version__}")
    sous = p.add_subparsers(dest="commande", required=True)
    for nom, (_, aide) in COMMANDES.items():
        sp = sous.add_parser(nom, help=aide, description=aide)
        sp.add_argument("--format", choices=["json", "texte"], default="json")
        if nom == "triangle":
            sp.add_argument("--entree", required=True, help="Fichier CSV ou Excel du triangle.")
            sp.add_argument("--feuille", default=None, help="Onglet Excel (nom ou numéro).")
            sp.add_argument("--type", choices=["auto", "cumule", "incremental"], default="auto")
    return p


def afficher_texte(d: dict) -> str:
    lignes = [f"Méthode : {d['methode']} (moteur {d['moteur']['version']})"]
    for e in d["entrees"]:
        lignes.append(f"Entrée : {e['fichier']} (sha256 {e['sha256'][:12]}…)")
    if d["options"]:
        lignes.append("Options : " + ", ".join(f"{k}={v}" for k, v in d["options"].items()))
    for h in d["hypotheses"]:
        lignes.append(f"Hypothèse : {h['nom']} = {h['valeur']} ({h['justification']})")
    lignes.append("Résultats :")
    lignes.append(json.dumps(d["resultats"], ensure_ascii=False, indent=2))
    for a in d["avertissements"]:
        lignes.append(f"ATTENTION : {a}")
    return "\n".join(lignes)


def calculer(argv: list[str]) -> dict:
    """Exécute une commande et rend la sortie sous forme de dictionnaire (utilisé par les tests)."""
    args = construire_parser().parse_args(argv)
    return COMMANDES[args.commande][0](args).en_dict()


def main(argv: list[str] | None = None) -> int:
    args = construire_parser().parse_args(argv)
    try:
        res = COMMANDES[args.commande][0](args)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"erreur": str(exc), "commande": args.commande}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    d = res.en_dict()
    print(afficher_texte(d) if args.format == "texte" else json.dumps(d, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
