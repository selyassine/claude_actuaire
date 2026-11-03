"""Compare le moteur aux valeurs publiées des fiches tests/references/*.yaml.

- Fiche "valide" : tout écart fait échouer les tests.
- Fiche "en_attente" : un écart est signalé (xfail) sans bloquer, en attendant
  le contrôle des valeurs par un actuaire.
"""

import pytest

from cli import calculer
from outils_reference import DOSSIER_TESTS, charger_fiches, ecarts, erreurs_fiche


@pytest.mark.parametrize("fiche", charger_fiches(inclure_modeles=True), ids=lambda f: f.chemin.name)
def test_structure_des_fiches(fiche):
    assert erreurs_fiche(fiche.contenu) == []


FICHES = charger_fiches()


@pytest.mark.parametrize("fiche", FICHES, ids=lambda f: f.id)
def test_valeurs_publiees(fiche):
    argv = [fiche.contenu["methode"]]
    if fiche.contenu["donnees"]:  # null pour les méthodes sans fichier (ex. tarif-vie sur le SSSM)
        argv += ["--entree", str(DOSSIER_TESTS / fiche.contenu["donnees"])]
    for cle, val in (fiche.contenu.get("options") or {}).items():
        if isinstance(val, str) and val.startswith("donnees/"):
            val = DOSSIER_TESTS / val
        argv += [f"--{cle}", str(val)]
    problemes = ecarts(calculer(argv), fiche)
    if problemes and not fiche.validee:
        pytest.xfail("fiche en attente de validation : " + " ; ".join(problemes))
    assert problemes == [], " ; ".join(problemes)


def test_rapport_validation():
    """Affiche combien de fiches restent à valider (n'échoue jamais)."""
    en_attente = [f.id for f in FICHES if not f.validee]
    print(f"\n{len(FICHES) - len(en_attente)} fiche(s) validée(s), {len(en_attente)} en attente : {en_attente}")
