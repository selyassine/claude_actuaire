"""La sortie de chaque commande respecte le format traçable."""

import hashlib
import json
import subprocess
import sys

from cli import calculer
from conftest import RACINE

CLI = RACINE / "skills" / "calcul-actuariel" / "scripts" / "cli.py"
DONNEES = RACINE / "tests" / "donnees"
CLES = {"methode", "moteur", "horodatage_utc", "entrees", "options", "hypotheses",
        "resultats", "avertissements"}


def test_environnement():
    d = calculer(["environnement"])
    assert set(d) == CLES
    assert d["resultats"]["statut"] == "pret"


def test_triangle_tracable():
    chemin = DONNEES / "lecture_incremental.csv"
    d = calculer(["triangle", "--entree", str(chemin)])
    assert set(d) == CLES
    assert d["entrees"][0]["sha256"] == hashlib.sha256(chemin.read_bytes()).hexdigest()
    assert d["resultats"]["type_retenu"] == "incremental"
    assert d["resultats"]["derniere_diagonale_cumulee"] == {"2021": 175, "2022": 160, "2023": 120}
    assert d["hypotheses"][0]["nom"] == "type_de_triangle"


def test_appel_en_ligne_de_commande_depuis_un_autre_dossier(tmp_path):
    """Claude appelle le script par son chemin, depuis n'importe quel dossier."""
    out = subprocess.run([sys.executable, str(CLI), "environnement"], cwd=tmp_path,
                         capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["methode"] == "environnement"


def test_fichier_absent_message_clair(tmp_path):
    out = subprocess.run([sys.executable, str(CLI), "triangle", "--entree", "absent.csv"],
                         cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 2
    assert "erreur" in json.loads(out.stderr)
