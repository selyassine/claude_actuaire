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
    s = noter(sortie, TACHES)
    assert s["C"]["scr"] == {"justes": 2, "total": 3, "taux": 0.6667}
