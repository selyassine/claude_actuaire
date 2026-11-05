"""Commandes survie et tarif-vie de la ligne de commande."""

from __future__ import annotations

import argparse

from .sortie import Hypothese, Resultat
from .triangle import _nombre, lire_tableau
from .vie import Base, Contrat, ModeleSurvie, tarifer

# Paramètres publiés dans AMLCR (Dickson, Hardy et Waters), sections 4.3 et 6.3
SUSM = {"A": 0.00022, "B": 2.7e-6, "c": 1.124}
SSSM_SELECTION = {"facteur": 0.9, "duree": 2}


def args_modele(sp: argparse.ArgumentParser) -> None:
    g = sp.add_argument_group("modèle de survie")
    g.add_argument("--modele", choices=["sssm", "susm", "makeham", "table"], default="sssm",
                   help="sssm (défaut) : Standard Select Survival Model d'AMLCR ; susm : modèle ultime ; "
                        "makeham : paramètres --A --B --c ; table : fichier --table (colonnes Age, qx).")
    g.add_argument("--A", type=float, help="Makeham : constante A.")
    g.add_argument("--B", type=float, help="Makeham : B.")
    g.add_argument("--c", type=float, help="Makeham : c.")
    g.add_argument("--table", help="CSV ou Excel avec les colonnes Age et qx (modèle table).")
    g.add_argument("--selection-facteur", type=float,
                   help="Facteur de sélection k (mu ou q sélectionné = k^(d-s) × ultime).")
    g.add_argument("--selection-duree", type=int, help="Période de sélection d, en années.")
    g.add_argument("--taux", type=float, required=True, help="Taux d'intérêt annuel effectif, ex. 0.04.")


def args_survie(sp: argparse.ArgumentParser) -> None:
    args_modele(sp)
    sp.add_argument("--age", type=int, required=True, help="Âge à la sélection (souscription), x.")
    sp.add_argument("--depuis", type=int, default=0, help="Années écoulées depuis la sélection, s (défaut 0).")
    sp.add_argument("--n", type=int, help="Durée des fonctions temporaires (annuité, temporaire décès, mixte).")


def args_tarif(sp: argparse.ArgumentParser) -> None:
    args_modele(sp)
    c = sp.add_argument_group("contrat")
    c.add_argument("--type", choices=["vie-entiere", "temporaire", "mixte"], required=True)
    c.add_argument("--age", type=int, required=True, help="Âge à la souscription (vie sélectionnée à cet âge).")
    c.add_argument("--capital", type=float, required=True)
    c.add_argument("--duree", type=int, help="Durée de couverture (temporaire, mixte).")
    c.add_argument("--duree-primes", type=int, help="Durée de paiement des primes (défaut : durée du contrat).")
    c.add_argument("--frais-initiaux-pct", type=float, default=0.0, help="Frais initiaux en %% de la prime commerciale.")
    c.add_argument("--frais-initiaux-fixe", type=float, default=0.0, help="Frais initiaux fixes.")
    c.add_argument("--frais-renouvellement-pct", type=float, default=0.0,
                   help="Frais en %% de chaque prime commerciale après la première.")
    c.add_argument("--frais-renouvellement-fixe", type=float, default=0.0,
                   help="Frais fixes à chaque échéance de prime après la première.")
    c.add_argument("--durees", default="0,1,2,5,10",
                   help="Durées (années) où calculer les provisions, séparées par des virgules.")


def _lire_qx(chemin: str) -> dict[int, float]:
    df = lire_tableau(chemin)
    cols = {str(c).strip().lower(): c for c in df.columns}
    if "age" not in cols or "qx" not in cols:
        raise ValueError("la table doit contenir les colonnes Age et qx")
    ages = [_nombre(a) for a in df[cols["age"]]]
    if any(not float(a).is_integer() for a in ages):
        raise ValueError("table de mortalité : âges entiers attendus")
    ages = [int(a) for a in ages]
    if len(set(ages)) != len(ages):
        raise ValueError("table de mortalité : âges en double")
    return dict(zip(ages, (float(_nombre(q)) for q in df[cols["qx"]]), strict=True))


def construire_modele(args, res: Resultat) -> ModeleSurvie:
    sel = {}
    if args.modele == "sssm":
        sel = SSSM_SELECTION
    if args.selection_facteur is not None or args.selection_duree is not None:
        if args.selection_facteur is None or args.selection_duree is None:
            raise ValueError("--selection-facteur et --selection-duree vont ensemble")
        sel = {"facteur": args.selection_facteur, "duree": args.selection_duree}
    kw = {"facteur_selection": sel.get("facteur", 1.0), "periode_selection": sel.get("duree", 0)}

    if args.modele in ("sssm", "susm"):
        m = ModeleSurvie.makeham(SUSM["A"], SUSM["B"], SUSM["c"], **kw)
        res.hypotheses.append(Hypothese(
            "loi_de_mortalite", f"Makeham A={SUSM['A']}, B={SUSM['B']}, c={SUSM['c']}",
            "Standard Ultimate Survival Model d'AMLCR (section 4.3).", "valeur par défaut"))
    elif args.modele == "makeham":
        if None in (args.A, args.B, args.c):
            raise ValueError("le modèle makeham exige --A, --B et --c")
        m = ModeleSurvie.makeham(args.A, args.B, args.c, **kw)
        res.hypotheses.append(Hypothese("loi_de_mortalite", m.description, "Paramètres fournis."))
    else:
        if not args.table:
            raise ValueError("le modèle table exige --table")
        m = ModeleSurvie.table(_lire_qx(args.table), **kw)
        res.ajouter_entree(args.table, role="table_mortalite")
        res.hypotheses.append(Hypothese(
            "fermeture_table", "q = 1 après le dernier âge de la table",
            "Une vie qui dépasse le dernier âge de la table est considérée comme décédée dans l'année.",
            "méthode"))
    if m.periode_selection:
        portee = "la force de mortalité" if m.makeham_params else "q (années entières)"
        res.hypotheses.append(Hypothese(
            "selection", f"k = {m.facteur_selection}, d = {m.periode_selection}",
            f"Sélection appliquée à {portee} : k^(d-s) × ultime pendant d ans"
            + (" (SSSM d'AMLCR, section 6.3)." if args.modele == "sssm" else "."),
            "valeur par défaut" if args.modele == "sssm" and args.selection_facteur is None else "option utilisateur"))
    res.hypotheses.append(Hypothese("taux", args.taux, "Taux d'intérêt annuel effectif."))
    res.hypotheses.append(Hypothese(
        "temps", "discret annuel",
        "Capital décès payé en fin d'année du décès ; primes et annuités payables d'avance.", "méthode"))
    return m


def cmd_survie(args) -> Resultat:
    res = Resultat("survie", {}, options={"modele": args.modele, "taux": args.taux, "age": args.age,
                                          "depuis": args.depuis, "n": args.n})
    b = Base(construire_modele(args, res), args.taux)
    x, s, n = args.age, args.depuis, args.n
    if x < 0 or s < 0:
        raise ValueError("--age et --depuis doivent être positifs ou nuls")
    if n is not None and n < 1:
        raise ValueError("--n doit être un entier au moins égal à 1")
    if x + s > max(b.modele.q_ultime):
        raise ValueError(f"âge atteint {x + s} au-delà du dernier âge du modèle ({max(b.modele.q_ultime)})")
    r = {
        "q": b.modele.q(x, s),
        "esperance_vie_entiere": b.esperance_vie_entiere(x, s),
        "annuite_due_vie_entiere": b.annuite_due(x, s),
        "assurance_vie_entiere": b.assurance_deces(x, s),
    }
    if n:
        r.update({
            "survie_n": float(b.survie(x, s, n)[n]),
            "capital_differe": b.capital_differe(x, s, n),
            "annuite_due_temporaire": b.annuite_due(x, s, n),
            "assurance_temporaire": b.assurance_deces(x, s, n),
            "assurance_mixte": b.assurance_deces(x, s, n) + b.capital_differe(x, s, n),
        })
    res.resultats = r
    return res


def cmd_tarif(args) -> Resultat:
    try:
        durees = sorted({int(t) for t in str(args.durees).split(",") if t.strip()})
    except ValueError:
        raise ValueError(f"--durees : liste d'entiers séparés par des virgules attendue, reçu '{args.durees}'") from None
    if any(t < 0 for t in durees):
        raise ValueError("--durees : durées positives ou nulles attendues")
    res = Resultat("tarif-vie", {}, options={
        "modele": args.modele, "taux": args.taux, "type": args.type, "age": args.age,
        "capital": args.capital, "duree": args.duree, "duree_primes": args.duree_primes, "durees": durees})
    b = Base(construire_modele(args, res), args.taux)
    c = Contrat(args.type, args.age, args.capital, args.duree, args.duree_primes,
                args.frais_initiaux_pct, args.frais_initiaux_fixe,
                args.frais_renouvellement_pct, args.frais_renouvellement_fixe)
    res.hypotheses.append(Hypothese(
        "frais", {"initiaux": f"{c.frais_initiaux_pct:.2%} de la prime + {c.frais_initiaux_fixe}",
                  "renouvellement": f"{c.frais_renouvellement_pct:.2%} de la prime + {c.frais_renouvellement_fixe}"},
        "Frais initiaux à la souscription, frais de renouvellement à chaque échéance suivante "
        "(convention AMLCR, exemple SN2.3)."))
    res.hypotheses.append(Hypothese(
        "provisions", "prospectives, juste avant la prime de l'année t",
        "Nette : base de la prime pure ; brute : prime commerciale et frais ; frais = brute - nette ; "
        "FPT : Zillmer complet (1re année = coût du risque, ensuite prime pure à [x]+1).", "méthode"))
    if c.duree and any(t > c.duree for t in durees):
        res.avertissements.append("Certaines durées dépassent le terme du contrat : provision nulle au-delà.")
    res.resultats = tarifer(b, c, durees)
    return res


COMMANDES = {
    "survie": (cmd_survie, "Fonctions de survie : q, espérance de vie, annuités, assurances, capital différé.",
               args_survie),
    "tarif-vie": (cmd_tarif, "Primes pure et commerciale, provisions nette, brute et Zillmer (FPT).", args_tarif),
}
