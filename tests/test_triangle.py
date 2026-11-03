"""Tests de lecture et de contrôle des triangles (propriétés, pas de valeurs publiées)."""

import numpy as np

from actuaire.triangle import lire_triangle
from conftest import RACINE

DONNEES = RACINE / "tests" / "donnees"


def test_lecture_point_virgule_et_virgule_decimale():
    tri = lire_triangle(DONNEES / "lecture_point_virgule.csv")
    assert tri.origines == ["2021", "2022", "2023"]
    assert tri.developpements == ["1", "2", "3"]
    assert tri.valeurs[0, 0] == 100.5
    assert np.isnan(tri.valeurs[2, 1])
    assert tri.semble_cumule()
    assert tri.controles() == []


def test_derniere_diagonale():
    tri = lire_triangle(DONNEES / "lecture_point_virgule.csv")
    assert tri.derniere_diagonale().tolist() == [175, 160, 120]


def test_aller_retour_cumule_incremental():
    inc = lire_triangle(DONNEES / "lecture_incremental.csv")
    assert not inc.semble_cumule()
    cum = inc.en_cumule()
    assert cum.derniere_diagonale().tolist() == [175, 160, 120]
    retour = cum.en_incremental()
    np.testing.assert_array_equal(retour.observe(), inc.observe())
    np.testing.assert_allclose(retour.valeurs[inc.observe()], inc.valeurs[inc.observe()])


def test_anomalies_signalees():
    alertes = lire_triangle(DONNEES / "lecture_anomalies.csv").controles()
    assert any("trou" in a for a in alertes)
    assert any("aucune valeur" in a for a in alertes)


def test_lecture_excel(tmp_path):
    import pandas as pd

    src = lire_triangle(DONNEES / "lecture_point_virgule.csv")
    df = pd.DataFrame(src.valeurs, columns=src.developpements)
    df.insert(0, "Origine", src.origines)
    chemin = tmp_path / "tri.xlsx"
    df.to_excel(chemin, index=False, sheet_name="Payés")
    tri = lire_triangle(chemin, "Payés")
    np.testing.assert_array_equal(np.isnan(tri.valeurs), np.isnan(src.valeurs))
    assert tri.derniere_diagonale().tolist() == [175, 160, 120]
