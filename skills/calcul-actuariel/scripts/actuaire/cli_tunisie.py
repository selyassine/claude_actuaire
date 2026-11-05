"""Commande marge-solvabilite-tn de la ligne de commande."""

from __future__ import annotations

import argparse
import json

from .sortie import Hypothese, Resultat
from .tunisie import ARTICLE_58_BIS, calculer_marge


def args_marge(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True,
                    help="Fichier JSON : non_vie (primes_emises_acceptees, primes_retenues, sinistres : reglements "
                         "[un par exercice], psap_debut, psap_fin, recours_encaisses, charge_nette ; "
                         "assurance_credit), vie (provisions_mathematiques_brutes / _nettes, "
                         "capitaux_sous_risque_bruts ou capitaux_assures_bruts, capitaux_sous_risque_nets), "
                         "marge_constituee (éléments de l'article 58).")


def cmd_marge(args) -> Resultat:
    with open(args.entree, encoding="utf-8") as f:
        donnees = json.load(f)
    res = Resultat("marge-solvabilite-tn", {}, options={})
    res.ajouter_entree(args.entree)
    r, avert = calculer_marge(donnees)
    res.avertissements += avert
    res.hypotheses.append(Hypothese(
        "reglementation", ARTICLE_58_BIS,
        "Non-vie : max(20 % des primes × max(retenues/émises ; 50 %), 25 % de la charge moyenne × "
        "max(net/brut ; 50 %)). Vie : 4 % des PM × max(net/brut ; 85 %) + 3 ‰ des capitaux sous risque × "
        "max(net/brut ; 50 %). Mixte : somme.", "méthode"))
    if "non_vie" in r:
        res.hypotheses.append(Hypothese(
            "charge_sinistres", "règlements + PSAP fin − PSAP début − recours encaissés",
            "Lecture de l'art. 58 bis : « après déduction des PSAP de début [...] et les recours encaissés » ; "
            "les recours sont déduits. Interprétation à confirmer par l'actuaire.", "méthode"))
        res.hypotheses.append(Hypothese(
            "rapport_sinistres", "charge nette / charge brute de la même période",
            "Le rapport de rétention sinistres est calculé sur la charge de la période (même définition nette "
            "et brute), fournie par l'utilisateur.", "méthode"))
    if "vie" in r and r["vie"]["capitaux_sous_risque"]["origine"] != "donnée d'entrée":
        res.hypotheses.append(Hypothese(
            "capitaux_sous_risque", "capitaux assurés − provisions mathématiques",
            "Définition de l'art. 58 bis b.", "méthode"))
    if "marge_constituee" in r:
        res.hypotheses.append(Hypothese(
            "marge_constituee", "éléments fournis, 50 % du capital non libéré",
            "Art. 58 : le moteur additionne les éléments fournis (pertes et incorporels déduits) ; il ne vérifie "
            "pas l'accord du CGA sur les plus-values et autres éléments.", "méthode"))
    res.resultats = r
    return res


COMMANDES = {
    "marge-solvabilite-tn": (cmd_marge, "Marge de solvabilité minimale tunisienne (Code des assurances, "
                                        "art. 58 et 58 bis) et taux de couverture.", args_marge),
}
