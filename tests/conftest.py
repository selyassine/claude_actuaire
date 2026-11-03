import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "skills" / "calcul-actuariel" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
