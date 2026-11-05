"""Lecture et contrôle des triangles de développement.

Format attendu (CSV ou Excel) : une ligne par année d'origine, une colonne
par période de développement, la première colonne contient le libellé de
l'année d'origine. Les cellules futures sont vides.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Triangle:
    origines: list[str]
    developpements: list[str]
    valeurs: np.ndarray  # NaN pour les cellules non observées

    @property
    def n_origines(self) -> int:
        return self.valeurs.shape[0]

    @property
    def n_dev(self) -> int:
        return self.valeurs.shape[1]

    def observe(self) -> np.ndarray:
        return ~np.isnan(self.valeurs)

    def derniere_diagonale(self) -> np.ndarray:
        """Dernière valeur observée de chaque ligne."""
        out = np.full(self.n_origines, np.nan)
        for i in range(self.n_origines):
            idx = np.where(self.observe()[i])[0]
            if idx.size:
                out[i] = self.valeurs[i, idx[-1]]
        return out

    def verifier_forme(self) -> None:
        """Erreur bloquante si une valeur est infinie, une ligne vide, ou s'il manque une valeur
        avant la dernière valeur observée d'une ligne (trou) : aucune méthode ne doit deviner ces cellules."""
        if np.any(np.isinf(self.valeurs)):
            raise ValueError("le triangle contient des valeurs infinies")
        if len(set(self.origines)) != len(self.origines):
            raise ValueError("années d'origine en double dans le triangle")
        if len(set(self.developpements)) != len(self.developpements):
            raise ValueError("périodes de développement en double dans le triangle")
        obs = self.observe()
        for i in range(self.n_origines):
            idx = np.where(obs[i])[0]
            if idx.size == 0:
                raise ValueError(f"ligne {self.origines[i]} : aucune valeur observée")
            if idx[0] != 0 or idx.size != idx[-1] + 1:
                raise ValueError(f"ligne {self.origines[i]} : valeur manquante avant la dernière valeur observée ; "
                                 "compléter la cellule (0 si aucun paiement) plutôt que la laisser vide")

    def en_cumule(self) -> "Triangle":
        self.verifier_forme()
        cum = np.where(self.observe(), np.cumsum(np.nan_to_num(self.valeurs), axis=1), np.nan)
        return Triangle(self.origines, self.developpements, cum)

    def en_incremental(self) -> "Triangle":
        inc = self.valeurs.copy()
        inc[:, 1:] = self.valeurs[:, 1:] - self.valeurs[:, :-1]
        return Triangle(self.origines, self.developpements, inc)

    def controles(self) -> list[str]:
        """Anomalies de forme ou de contenu, en clair. Liste vide si tout va bien."""
        alertes: list[str] = []
        obs = self.observe()
        for i in range(self.n_origines):
            idx = np.where(obs[i])[0]
            if idx.size == 0:
                alertes.append(f"Ligne {self.origines[i]} : aucune valeur observée.")
                continue
            if idx[0] != 0:
                alertes.append(f"Ligne {self.origines[i]} : la première période est vide.")
            if idx.size != idx[-1] + 1:
                alertes.append(f"Ligne {self.origines[i]} : trou dans les valeurs observées.")
        longueurs = obs.sum(axis=1)
        if np.any(np.diff(longueurs) > 0):
            alertes.append(
                "Le nombre de valeurs observées augmente d'une ligne à la suivante : "
                "vérifier l'ordre des années d'origine."
            )
        if np.any(self.valeurs[obs] < 0):
            alertes.append("Le triangle contient des valeurs négatives.")
        return alertes

    def part_croissante(self) -> float:
        """Part des passages d'une période à la suivante où le montant ne baisse pas."""
        d = np.diff(self.valeurs, axis=1)
        d = d[~np.isnan(d)]
        return float(np.mean(d >= 0)) if d.size else 1.0

    def semble_cumule(self) -> bool:
        """Vrai si au moins 80 % des passages sont croissants (indice, pas une preuve).

        Un triangle cumulé peut baisser ponctuellement (recours, réévaluations), comme
        le triangle RAA ; un triangle incrémental décroît en général après les premières périodes.
        """
        return self.part_croissante() >= 0.8


def _nombre(x) -> float:
    if x is None:
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip().replace(" ", "").replace(" ", "").replace(" ", "")
    if s == "" or s.lower() in {"nan", "na", "-"}:
        return np.nan
    if "," in s and "." in s:
        # 1.234,56 (européen) ou 1,234.56 (anglo-saxon)
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"valeur non numérique : '{x}'") from None


def nombre_ou_nan(x) -> float:
    """Comme _nombre, mais rend NaN pour un texte non numérique (lectures tolérantes qui comptent
    et signalent les valeurs ignorées)."""
    try:
        return _nombre(x)
    except ValueError:
        return np.nan


def lire_tableau(chemin: str | Path, feuille: str | int | None = None) -> pd.DataFrame:
    """Lit un CSV (séparateur détecté) ou un Excel en texte brut."""
    chemin = Path(chemin)
    if chemin.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(chemin, sheet_name=feuille or 0, header=0, dtype=object)
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        echantillon = f.read(4096)
    try:
        sep = csv.Sniffer().sniff(echantillon, delimiters=",;\t").delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(chemin, sep=sep, header=0, dtype=str, keep_default_na=False,
                       encoding="utf-8-sig")


def libelle(v) -> str:
    """Libellé d'origine ou de période normalisé : Excel lit souvent 2020 comme 2020.0."""
    s = str(v).strip()
    if re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".")[0]
    return s


def lire_triangle(chemin: str | Path, feuille: str | int | None = None) -> Triangle:
    df = lire_tableau(chemin, feuille)
    if df.shape[1] < 2 or df.shape[0] < 1:
        raise ValueError("triangle vide : une colonne de libellés et au moins une période sont attendues")
    origines = [libelle(v) for v in df.iloc[:, 0].tolist()]
    if any(o in ("", "nan", "None") for o in origines):
        raise ValueError("une année d'origine du triangle n'a pas de libellé")
    devs = [libelle(c) for c in df.columns[1:]]
    valeurs = np.array([[_nombre(v) for v in ligne] for ligne in df.iloc[:, 1:].values],
                       dtype=float)
    return Triangle(origines, devs, valeurs)
