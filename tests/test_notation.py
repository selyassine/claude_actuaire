"""Le script de notation du banc d'essai lit et note correctement les réponses."""

import sys

import yaml

from conftest import RACINE

sys.path.insert(0, str(RACINE / "banc_essai"))
from noter import extraire_resultats, juste, noter  # noqa: E402


def test_extraction_dernier_bloc():
    texte = 'Brouillon\n```resultats\n{"x": 1}\n```\nFinal\n```resultats\n{"x": 2}\n```\n'
    assert extraire_resultats(texte) == {"x": 2}
    assert extraire_resultats("pas de bloc") == {}
    assert extraire_resultats("```resultats\nillisible\n```") == {}


def test_tolerances():
    assert juste(100.4, {"attendu": 100, "tolerance_absolue": 0.5})
    assert not juste(100.6, {"attendu": 100, "tolerance_absolue": 0.5})
    assert juste(101.9, {"attendu": 100, "tolerance_relative": 0.02})
    assert not juste("abc", {"attendu": 100})
    assert not juste(None, {"attendu": 100})


def test_notation_de_bout_en_bout(tmp_path):
    taches, reps = tmp_path / "taches", tmp_path / "reponses"
    (taches / "t1").mkdir(parents=True)
    (taches / "t1" / "corrige.yaml").write_text(yaml.safe_dump(
        {"famille": "f", "valeurs": [{"nom": "v", "attendu": 10, "tolerance_absolue": 0.5}]}))
    for cond, val in (("A", 12), ("C", 10)):
        (reps / cond / "t1").mkdir(parents=True)
        (reps / cond / "t1" / "1.md").write_text(f'```resultats\n{{"v": {val}}}\n```')
    s = noter(reps, taches)
    assert s["A"]["ensemble"]["taux"] == 0
    assert s["C"]["ensemble"]["taux"] == 1
