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
from actuaire.cli_controle import COMMANDES as COMMANDES_CONTROLE  # noqa: E402
from actuaire.cli_credibilite import COMMANDES as COMMANDES_CREDIBILITE  # noqa: E402
from actuaire.cli_extremes import COMMANDES as COMMANDES_EXTREMES  # noqa: E402
from actuaire.cli_provisionnement import (
    COMMANDES as COMMANDES_PROVISIONNEMENT,  # noqa: E402
)
from actuaire.cli_provisionnement import _triangle_cumule, args_triangle  # noqa: E402
from actuaire.cli_registre import COMMANDES as COMMANDES_REGISTRE  # noqa: E402
from actuaire.cli_scr import COMMANDES as COMMANDES_SCR  # noqa: E402
from actuaire.cli_stochastique import COMMANDES as COMMANDES_STOCHASTIQUE  # noqa: E402
from actuaire.cli_tunisie import COMMANDES as COMMANDES_TUNISIE  # noqa: E402
from actuaire.cli_validation import COMMANDES as COMMANDES_VALIDATION  # noqa: E402
from actuaire.cli_vie import COMMANDES as COMMANDES_VIE  # noqa: E402
from actuaire.sortie import (  # noqa: E402
    Resultat,
    empreinte_fichier,
    empreinte_resultats,
)


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
    """Même lecture et mêmes contrôles bloquants que les méthodes de provisionnement :
    un triangle troué, infini ou avec des doublons est refusé, jamais résumé."""
    res = Resultat(methode="triangle", resultats={}, options={"type": args.type, "feuille": args.feuille})
    cumule = _triangle_cumule(args, res)
    res.resultats = {
        "n_origines": cumule.n_origines,
        "n_developpements": cumule.n_dev,
        "origines": cumule.origines,
        "developpements": cumule.developpements,
        "type_retenu": "cumule" if args.type == "cumule" or (
            args.type == "auto" and res.hypotheses and res.hypotheses[0].valeur == "cumule") else "incremental",
        "derniere_diagonale_cumulee": dict(zip(cumule.origines, cumule.derniere_diagonale(), strict=True)),
    }
    return res


def args_rejouer(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--sortie", required=True,
                    help="Fichier JSON rendu par une commande précédente du moteur.")
    sp.add_argument("--tolerance", type=float, default=1e-9,
                    help="Écart relatif toléré entre les deux calculs (défaut 1e-9).")


def _ecarts(a, b, tol: float, chemin: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{chemin}.{k} : présent d'un seul côté" for k in sorted(set(a) ^ set(b))]
        for k in sorted(set(a) & set(b)):
            out += _ecarts(a[k], b[k], tol, f"{chemin}.{k}" if chemin else k)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{chemin} : longueurs {len(a)} et {len(b)}"]
        return [e for i, (x, y) in enumerate(zip(a, b, strict=True)) for e in _ecarts(x, y, tol, f"{chemin}[{i}]")]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if abs(a - b) <= tol * max(1.0, abs(a), abs(b)):
            return []
        return [f"{chemin} : {a} puis {b}"]
    return [] if a == b else [f"{chemin} : {a!r} puis {b!r}"]


def cmd_rejouer(args: argparse.Namespace) -> Resultat:
    """Refait un calcul archivé et vérifie qu'il donne les mêmes chiffres sur les mêmes données."""
    with open(args.sortie, encoding="utf-8") as f:
        ancien = json.load(f)
    if not isinstance(ancien, dict) or "reproduction" not in ancien or "resultats" not in ancien:
        raise ValueError("ce fichier n'est pas une sortie du moteur avec bloc 'reproduction' (version 0.3.0 ou plus)")
    attendue = ancien.get("empreinte_resultats")
    if attendue and attendue != empreinte_resultats(ancien["resultats"]):
        raise ValueError("les résultats du fichier archivé ont été modifiés depuis le calcul (empreinte différente)")
    for e in ancien.get("entrees", []):
        if empreinte_fichier(e["fichier"]) != e["sha256"]:
            raise ValueError(f"le fichier d'entrée {e['fichier']} a changé depuis le calcul archivé")
    arguments = ancien["reproduction"]["arguments"]
    if arguments and arguments[0] == "rejouer":
        raise ValueError("une sortie de 'rejouer' ne se rejoue pas")
    nouveau = calculer(arguments)
    ecarts = _ecarts(ancien["resultats"], nouveau["resultats"], args.tolerance)
    res = Resultat(methode="rejouer", options={"sortie": args.sortie, "tolerance": args.tolerance}, resultats={
        "commande": arguments,
        "identique": not ecarts,
        "ecarts": ecarts[:50],
        "version_archivee": ancien.get("moteur", {}).get("version"),
        "version_actuelle": __version__,
    })
    res.ajouter_entree(args.sortie, "sortie_archivee")
    if ancien.get("moteur", {}).get("version") != __version__:
        res.avertissements.append("Le calcul archivé a été fait avec une autre version du moteur.")
    if ancien.get("moteur", {}).get("environnement") != nouveau["moteur"]["environnement"]:
        res.avertissements.append("Versions de Python ou des bibliothèques différentes de celles du calcul archivé.")
    if ecarts:
        res.avertissements.append(f"{len(ecarts)} écart(s) entre le calcul archivé et le nouveau calcul.")
    return res


COMMANDES = {
    "environnement": (cmd_environnement, "Vérifie que le moteur et ses dépendances sont disponibles.",
                      lambda sp: None),
    **COMMANDES_CONTROLE,
    "triangle": (cmd_triangle, "Lit un triangle, contrôle sa forme et donne la dernière diagonale.",
                 args_triangle),
    **COMMANDES_PROVISIONNEMENT,
    **COMMANDES_STOCHASTIQUE,
    **COMMANDES_VIE,
    **COMMANDES_EXTREMES,
    **COMMANDES_CREDIBILITE,
    **COMMANDES_SCR,
    **COMMANDES_TUNISIE,
    **COMMANDES_VALIDATION,
    **COMMANDES_REGISTRE,
    "rejouer": (cmd_rejouer, "Refait un calcul archivé (sortie JSON) et vérifie qu'il donne les mêmes chiffres.",
                args_rejouer),
}


def construire_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"claude_actuaire {__version__}")
    sous = p.add_subparsers(dest="commande", required=True)
    for nom, (_, aide, ajouter_args) in COMMANDES.items():
        sp = sous.add_parser(nom, help=aide, description=aide)
        sp.add_argument("--format", choices=["json", "texte"], default="json")
        ajouter_args(sp)
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


def _arguments_de_calcul(argv: list[str]) -> list[str]:
    """Arguments qui déterminent le calcul (sans --format, qui ne change que l'affichage)."""
    out, i = [], 0
    while i < len(argv):
        if argv[i] == "--format":
            i += 2
            continue
        if argv[i].startswith("--format="):
            i += 1
            continue
        out.append(argv[i])
        i += 1
    return out


def _finaliser(d: dict, argv: list[str]) -> dict:
    d["reproduction"] = {"arguments": _arguments_de_calcul(argv),
                         "commande": "python cli.py " + " ".join(_arguments_de_calcul(argv))}
    d["empreinte_resultats"] = empreinte_resultats(d["resultats"])
    return d


def calculer(argv: list[str]) -> dict:
    """Exécute une commande et rend la sortie sous forme de dictionnaire (utilisé par les tests)."""
    args = construire_parser().parse_args(argv)
    return _finaliser(COMMANDES[args.commande][0](args).en_dict(), list(argv))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = construire_parser().parse_args(argv)
    try:
        res = COMMANDES[args.commande][0](args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"statut": "erreur", "erreur": str(exc), "commande": args.commande}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    except Exception as exc:  # erreur inattendue : jamais de résultat partiel
        print(json.dumps({"statut": "erreur", "erreur": f"erreur interne ({type(exc).__name__}) : {exc}",
                          "commande": args.commande}, ensure_ascii=False), file=sys.stderr)
        return 3
    d = _finaliser(res.en_dict(), argv)
    print(afficher_texte(d) if args.format == "texte" else json.dumps(d, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
