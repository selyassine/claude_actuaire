"""Chargement des fiches de référence et comparaison aux sorties du moteur."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DOSSIER_TESTS = Path(__file__).resolve().parent
DOSSIER_REFERENCES = DOSSIER_TESTS / "references"

CHAMPS_OBLIGATOIRES = {"id", "methode", "source", "donnees", "statut", "valeurs"}
STATUTS = {"en_attente", "valide"}


@dataclass
class Fiche:
    chemin: Path
    contenu: dict[str, Any]

    @property
    def id(self) -> str:
        return self.contenu["id"]

    @property
    def validee(self) -> bool:
        return self.contenu["statut"] == "valide"


def erreurs_fiche(contenu: dict[str, Any]) -> list[str]:
    """Liste les problèmes de structure d'une fiche (vide si elle est correcte)."""
    err: list[str] = []
    manquants = CHAMPS_OBLIGATOIRES - set(contenu)
    if manquants:
        err.append(f"champs manquants : {sorted(manquants)}")
        return err
    if contenu["statut"] not in STATUTS:
        err.append(f"statut inconnu : {contenu['statut']}")
    if contenu["statut"] == "valide" and not contenu.get("valide_par"):
        err.append("statut 'valide' sans 'valide_par'")
    src = contenu["source"]
    if not isinstance(src, dict) or not src.get("reference") or not src.get("emplacement"):
        err.append("source incomplète : 'reference' et 'emplacement' obligatoires")
    if not contenu["valeurs"]:
        err.append("aucune valeur attendue")
    for i, v in enumerate(contenu["valeurs"] or []):
        for champ in ("chemin", "attendu"):
            if champ not in v:
                err.append(f"valeur {i} : '{champ}' manquant")
        if ("tolerance_absolue" in v) == ("tolerance_relative" in v):
            err.append(f"valeur {i} : indiquer soit 'tolerance_absolue', soit 'tolerance_relative'")
    return err


def charger_fiches(methode: str | None = None, inclure_modeles: bool = False) -> list[Fiche]:
    fiches = []
    for p in sorted(DOSSIER_REFERENCES.glob("*.yaml")):
        if p.name.startswith("_") and not inclure_modeles:
            continue
        contenu = yaml.safe_load(p.read_text(encoding="utf-8"))
        if methode is None or contenu.get("methode") == methode:
            fiches.append(Fiche(p, contenu))
    return fiches


def lire_chemin(d: dict[str, Any], chemin: str) -> Any:
    """Suit un chemin pointé ; une clé contenant elle-même un point (ex. quantile '0.75') est reconnue."""
    obj: Any = d
    morceaux = chemin.split(".")
    i = 0
    while i < len(morceaux):
        if isinstance(obj, list):
            obj = obj[int(morceaux[i])]
            i += 1
            continue
        for j in range(len(morceaux), i, -1):
            cle = ".".join(morceaux[i:j])
            if cle in obj:
                obj = obj[cle]
                i = j
                break
        else:
            raise KeyError(chemin)
    return obj


def ecarts(sortie: dict[str, Any], fiche: Fiche) -> list[str]:
    """Compare une sortie du moteur aux valeurs publiées. Vide si tout concorde."""
    out = []
    for v in fiche.contenu["valeurs"]:
        obtenu = lire_chemin(sortie, v["chemin"])
        attendu = float(v["attendu"])
        if "tolerance_relative" in v:
            tol, libelle = abs(attendu) * float(v["tolerance_relative"]), f"{v['tolerance_relative']:.1%}"
        else:
            tol, libelle = float(v["tolerance_absolue"]), str(v["tolerance_absolue"])
        if obtenu is None or abs(float(obtenu) - attendu) > tol:
            out.append(f"{v['chemin']} : obtenu {obtenu}, publié {v['attendu']} (tolérance {libelle})")
    return out
