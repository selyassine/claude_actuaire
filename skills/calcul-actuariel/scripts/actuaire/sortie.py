"""Sortie traçable commune à toutes les méthodes.

Chaque calcul rend un dictionnaire de la même forme : méthode, version du
moteur, empreinte des entrées, options retenues, hypothèses, résultats et
avertissements. Cette forme alimentera plus tard le registre des hypothèses.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__


def empreinte_fichier(chemin: str | Path) -> str:
    """SHA-256 du fichier d'entrée, pour prouver sur quelles données on a calculé."""
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()


@dataclass
class Hypothese:
    """Un choix de calcul qui influence le résultat, avec sa justification."""

    nom: str
    valeur: Any
    justification: str
    source: str = "option utilisateur"  # ou "valeur par défaut", "donnée d'entrée"…


@dataclass
class Resultat:
    methode: str
    resultats: dict[str, Any]
    options: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[Hypothese] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    entrees: list[dict[str, str]] = field(default_factory=list)

    def ajouter_entree(self, chemin: str | Path, role: str = "donnees") -> None:
        self.entrees.append(
            {"role": role, "fichier": str(chemin), "sha256": empreinte_fichier(chemin)}
        )

    def en_dict(self) -> dict[str, Any]:
        return _nettoyer(
            {
                "methode": self.methode,
                "moteur": {"nom": "claude_actuaire", "version": __version__},
                "horodatage_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "entrees": self.entrees,
                "options": self.options,
                "hypotheses": [h.__dict__ for h in self.hypotheses],
                "resultats": self.resultats,
                "avertissements": self.avertissements,
            }
        )

    def en_json(self) -> str:
        return json.dumps(self.en_dict(), ensure_ascii=False, indent=2)


def _nettoyer(obj: Any) -> Any:
    """Convertit les types numpy et les NaN en types JSON standard."""
    if isinstance(obj, dict):
        return {str(k): _nettoyer(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nettoyer(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _nettoyer(obj.tolist())
    if isinstance(obj, np.generic):
        return _nettoyer(obj.item())
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
