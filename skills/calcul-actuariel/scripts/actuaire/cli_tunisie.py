"""Commande marge-solvabilite-tn de la ligne de commande."""

from __future__ import annotations

import argparse
import json

from .cli_validation import _charger_sortie
from .sortie import Hypothese, Resultat
from .tunisie import ARRETE_2001, ARTICLE_58_BIS, calculer_marge, calculer_provisions


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


def args_provisions(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--entree", required=True,
                    help="Fichier JSON avec un ou plusieurs blocs : ppna, prc, frais_gestion_sinistres, "
                         "auto_materiels, equilibrage, egalisation_grele, rentes (voir le guide des méthodes).")
    sp.add_argument("--cadences", help="Sortie JSON archivée de chain-ladder sur le triangle des règlements "
                                       "auto matériels (évaluation par les cadences de l'art. 22).")


def cmd_provisions(args) -> Resultat:
    with open(args.entree, encoding="utf-8") as f:
        donnees = json.load(f)
    res = Resultat("provisions-tn", {}, options={})
    res.ajouter_entree(args.entree)
    cadences = None
    if args.cadences:
        sortie = _charger_sortie(args.cadences)
        if sortie["methode"] != "chain-ladder":
            raise ValueError(f"--cadences : sortie chain-ladder attendue (reçu {sortie['methode']})")
        t = sortie["resultats"]["total"]
        cadences = {"fichier": args.cadences, "empreinte_resultats": sortie.get("empreinte_resultats"),
                    "ultime": t["ultime"], "derniere_diagonale": t["derniere_diagonale"],
                    "provision": t["provision"]}
        res.ajouter_entree(args.cadences, role="sortie_chain_ladder")
    r, avert = calculer_provisions(donnees, cadences)
    res.avertissements += avert
    res.hypotheses.append(Hypothese("reglementation", ARRETE_2001, "Règles de calcul des articles 17 à 27.",
                                    "méthode"))
    if "ppna" in r:
        res.hypotheses.append(Hypothese(
            "ppna", "prorata temporis en jours exacts sur la prime commerciale",
            "Art. 17 ; prime d'un contrat à effet futur entièrement non acquise.", "méthode"))
    if "prc" in r:
        res.hypotheses.append(Hypothese(
            "prc_primes", "primes acquises fournies",
            "Art. 19 : les primes des deux exercices sont fournies déjà corrigées des primes restant à émettre, "
            "des primes à annuler et de la variation de PPNA ; le moteur ne refait pas ces corrections.",
            "donnée d'entrée"))
    if "frais_gestion_sinistres" in r:
        base = r["frais_gestion_sinistres"]["base_minimum"]
        res.hypotheses.append(Hypothese(
            "base_minimum_frais", base,
            "Art. 21 : « au moins 5 % du montant des PSAP ». psap_totale : frais ≥ 5 % de la PSAP frais compris "
            "(lecture littérale) ; psap_hors_frais : frais ≥ 5 % de la PSAP hors frais. Interprétation à confirmer.",
            "valeur par défaut" if base == "psap_totale" else "option utilisateur"))
    if "auto_materiels" in r:
        res.hypotheses.append(Hypothese(
            "cadences", "provision chain-ladder sur le triangle des règlements",
            "Art. 22 : l'évaluation par les cadences de règlement reprend la provision totale d'une sortie "
            "chain-ladder archivée ; ses propres hypothèses (facteurs, queue) sont dans cette sortie.", "méthode"))
    if "equilibrage" in r or "egalisation_grele" in r:
        res.hypotheses.append(Hypothese(
            "reprise", "perte technique imputée sur la provision, dans la limite de son montant",
            "Art. 24 et 25 : la provision compense les pertes ; l'arrêté ne précise pas la reprise, le moteur "
            "impute la perte de l'exercice sur la provision existante.", "méthode"))
    res.resultats = r
    return res


COMMANDES = {
    "marge-solvabilite-tn": (cmd_marge, "Marge de solvabilité minimale tunisienne (Code des assurances, "
                                        "art. 58 et 58 bis) et taux de couverture.", args_marge),
    "provisions-tn": (cmd_provisions, "Règles de provisions non-vie de l'arrêté tunisien du 27/02/2001 : PPNA, PRC, "
                                      "frais de gestion des sinistres, auto matériels, équilibrage, égalisation, "
                                      "rentes.", args_provisions),
}
