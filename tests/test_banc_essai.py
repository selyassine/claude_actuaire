"""Cohérence du banc d'essai : corrigés lisibles, import et notation."""

import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "banc_essai"))

from importer import importer  # noqa: E402
from noter import noter  # noqa: E402

TACHES = RACINE / "banc_essai" / "taches"


def test_chaque_tache_a_consigne_et_corrige():
    ids = [p for p in TACHES.iterdir() if p.is_dir()]
    assert len(ids) == 16
    for d in ids:
        c = yaml.safe_load((d / "corrige.yaml").read_text("utf-8"))
        consigne = (d / "consigne.md").read_text("utf-8")
        assert c["valeurs"]
        for v in c["valeurs"]:
            assert f'"{v["nom"]}"' in consigne
        assert "corrige" not in consigne.lower()


def test_import_et_notation(tmp_path):
    f = tmp_path / "r.md"
    f.write_text('## C scr-01\n\nTexte\n\n```resultats\n{"diversification": -542418, "bscr": 2738047, "scr": 1}\n```\n\n## A scr-01\n\n')
    sortie = tmp_path / "reponses"
    assert importer(f, sortie) == 1
    s = noter(sortie, TACHES, taches=["scr-01"])
    assert s["C"]["scr"] == {"justes": 2, "total": 3, "taux": 0.6667}
    assert s["completude"]["essais_manquants"] == []


PIEGES = RACINE / "banc_essai" / "pieges" / "taches"


def test_pieges_consignes_et_corriges():
    ids = sorted(p.name for p in PIEGES.iterdir() if p.is_dir())
    assert len(ids) == 9
    assert sum(i.startswith("p-tn-") for i in ids) == 5
    for i in ids:
        c = yaml.safe_load((PIEGES / i / "corrige.yaml").read_text("utf-8"))
        consigne = (PIEGES / i / "consigne.md").read_text("utf-8")
        assert c["famille"] == "pieges" and c["piege"] and c["source"]
        for v in c["valeurs"]:
            assert f'"{v["nom"]}"' in consigne
        assert "piège" not in consigne.lower() and "corrige" not in consigne.lower()


def test_notation_null_et_booleens(tmp_path):
    from noter import ABSENT, juste

    nul = {"attendu": None}
    assert juste(None, nul) and not juste(ABSENT, nul) and not juste(0, nul)
    faux = {"attendu": False}
    assert juste(False, faux) and not juste(True, faux) and not juste(0, faux) and not juste(ABSENT, faux)
    nombre = {"attendu": 1.0, "tolerance_absolue": 0.5}
    assert not juste(True, nombre) and not juste(None, nombre) and juste(1.2, nombre)

    d = tmp_path / "reponses" / "C" / "p-tn-marge-2ex"
    d.mkdir(parents=True)
    (d / "1.md").write_text('Il manque un exercice.\n\n```resultats\n{"minimum_reglementaire": null}\n```\n')
    s = noter(tmp_path / "reponses", PIEGES, taches=["p-tn-marge-2ex"])
    assert s["C"]["pieges"]["taux"] == 1.0
