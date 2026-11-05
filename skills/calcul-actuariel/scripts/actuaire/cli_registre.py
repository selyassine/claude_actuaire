"""Commande registre : registre des hypothèses d'un dossier de calculs.

Un dossier actuariel réunit plusieurs calculs (Chain Ladder, Mack, BF, GPD…) faits à des moments
différents. Le registre relit toutes leurs sorties JSON archivées et rend :
- la liste des calculs (méthode, statut, version, commande, empreinte vérifiée) ;
- les données utilisées, avec leur empreinte, et les calculs qui les utilisent ;
- les hypothèses, classées en choix de jugement (options de l'utilisateur), valeurs par défaut
  à confirmer et hypothèses de méthode ;
- les incohérences du dossier : résultats retouchés, même fichier avec des contenus différents
  d'un calcul à l'autre, fichier modifié depuis le calcul, hypothèses divergentes sur les mêmes
  données, versions du moteur différentes, calculs incomplets.
Avec --note, il écrit la note d'hypothèses du dossier en Markdown.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sortie import Resultat, empreinte_fichier, empreinte_obligatoire, empreinte_resultats

CATEGORIES = {"option utilisateur": "choix_de_jugement", "valeur par défaut": "valeurs_par_defaut"}


def _fichiers(chemins: list[str]) -> list[Path]:
    out: list[Path] = []
    for c in chemins:
        p = Path(c)
        if p.is_dir():
            out += sorted(q for q in p.rglob("*.json") if q.is_file())
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f"introuvable : {c}")
    vus, uniques = set(), []
    for p in out:
        if p.resolve() not in vus:
            vus.add(p.resolve())
            uniques.append(p)
    return uniques


def _cle(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _incoherence(gravite: str, code: str, message: str, calculs: list[str]) -> dict:
    return {"gravite": gravite, "code": code, "message": message, "calculs": calculs}


def construire_registre(fichiers: list[Path], verifier_entrees: bool = True) -> dict:
    calculs, ignores, incoherences = [], [], []
    for p in fichiers:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            ignores.append({"fichier": str(p), "raison": f"JSON illisible ({type(exc).__name__})"})
            continue
        if not isinstance(d, dict) or "methode" not in d or "resultats" not in d or "moteur" not in d:
            ignores.append({"fichier": str(p), "raison": "pas une sortie du moteur"})
            continue
        if d["methode"] == "registre":
            ignores.append({"fichier": str(p), "raison": "sortie d'un registre"})
            continue
        calculs.append((p, d))
    if not calculs:
        raise ValueError("aucune sortie du moteur trouvée dans les fichiers donnés")

    # noms courts : chemins relatifs au dossier commun des sorties
    base = Path(os.path.commonpath([str(p.resolve().parent) for p, _ in calculs]))
    noms = {p: p.resolve().relative_to(base).as_posix() for p, _ in calculs}
    liste, usages = [], defaultdict(lambda: defaultdict(list))  # usages[fichier][sha] -> calculs
    for p, d in calculs:
        nom = noms[p]
        attendue = d.get("empreinte_resultats")
        empreinte_ok = None if not attendue else attendue == empreinte_resultats(d["resultats"])
        if empreinte_ok is False:
            incoherences.append(_incoherence("bloquant", "resultats_retouches",
                                             "Les résultats ne correspondent plus à leur empreinte : le fichier a été "
                                             "modifié après le calcul.", [nom]))
        for e in d.get("entrees", []):
            usages[e["fichier"]][e["sha256"]].append(nom)
        liste.append({
            "fichier": nom, "methode": d["methode"], "statut": d.get("statut"),
            "version_moteur": d["moteur"].get("version"), "horodatage_utc": d.get("horodatage_utc"),
            "commande": (d.get("reproduction") or {}).get("commande"),
            "empreinte_resultats": attendue, "empreinte_verifiee": empreinte_ok,
            "entrees": d.get("entrees", []), "avertissements": d.get("avertissements", []),
        })
        if d.get("statut") == "incomplet":
            incoherences.append(_incoherence("alerte", "calcul_incomplet",
                                             "Calcul au statut incomplet : des valeurs non définies ne doivent pas être "
                                             "reportées.", [nom]))
        if not attendue and empreinte_obligatoire(d):
            incoherences.append(_incoherence("bloquant", "empreinte_retiree",
                                             "Sortie sans empreinte alors que sa version du moteur en produit une "
                                             "(0.3.0 ou plus) : résultats non vérifiables.", [nom]))
        elif not attendue:
            incoherences.append(_incoherence("info", "sans_empreinte",
                                             "Sortie antérieure à la 0.3.0 : résultats non vérifiables par empreinte.", [nom]))

    donnees = []
    for fichier, par_sha in sorted(usages.items()):
        actuel = None
        if verifier_entrees and Path(fichier).is_file():
            actuel = empreinte_fichier(fichier)
        donnees.append({"fichier": fichier, "versions": [{"sha256": s, "calculs": c} for s, c in par_sha.items()],
                        "sha256_actuel": actuel})
        if len(par_sha) > 1:
            incoherences.append(_incoherence("bloquant", "donnees_differentes",
                                             f"{fichier} n'a pas le même contenu d'un calcul à l'autre : les résultats "
                                             "du dossier ne portent pas sur les mêmes données.",
                                             [c for cs in par_sha.values() for c in cs]))
        if actuel is not None and any(s != actuel for s in par_sha):
            incoherences.append(_incoherence("alerte", "donnees_modifiees_depuis",
                                             f"{fichier} a changé depuis le calcul : relancer avec « rejouer » pour "
                                             "savoir si les chiffres tiennent toujours.",
                                             [c for s, cs in par_sha.items() if s != actuel for c in cs]))
        if verifier_entrees and actuel is None:
            incoherences.append(_incoherence("info", "donnees_introuvables",
                                             f"{fichier} est introuvable depuis le dossier courant : empreinte actuelle "
                                             "non vérifiée.", [c for cs in par_sha.values() for c in cs]))

    # hypothèses : regroupées par nom, valeur et catégorie
    hyp: dict[tuple, dict] = {}
    par_nom: dict[str, dict[str, list[tuple[str, set[str]]]]] = defaultdict(lambda: defaultdict(list))
    for p, d in calculs:
        shas = {e["sha256"] for e in d.get("entrees", [])}
        for h in d.get("hypotheses", []):
            cat = CATEGORIES.get(h.get("source"), "hypotheses_de_methode")
            k = (cat, h["nom"], _cle(h.get("valeur")))
            entree = hyp.setdefault(k, {"nom": h["nom"], "valeur": h.get("valeur"), "source": h.get("source"),
                                        "justification": h.get("justification"), "calculs": []})
            entree["calculs"].append(f"{noms[p]} ({d['methode']})")
            par_nom[h["nom"]][_cle(h.get("valeur"))].append((noms[p], shas))
    for nom, valeurs in sorted(par_nom.items()):
        if len(valeurs) < 2:
            continue
        cles = list(valeurs)
        for i in range(len(cles)):
            for j in range(i + 1, len(cles)):
                communs = [(a, b) for a, sa in valeurs[cles[i]] for b, sb in valeurs[cles[j]] if sa & sb]
                if communs:
                    a, b = communs[0]
                    incoherences.append(_incoherence(
                        "alerte", "hypotheses_divergentes",
                        f"Hypothèse « {nom} » : {json.loads(cles[i])!r} dans un calcul, {json.loads(cles[j])!r} dans "
                        "un autre, sur les mêmes données. Volontaire (sensibilité) ou incohérence du dossier ?", [a, b]))
    versions = sorted({c["version_moteur"] for c in liste if c["version_moteur"]})
    if len(versions) > 1:
        incoherences.append(_incoherence("alerte", "versions_differentes",
                                         f"Calculs faits avec plusieurs versions du moteur : {versions}.",
                                         [c["fichier"] for c in liste]))
    environnements = {_cle(d["moteur"].get("environnement")) for _, d in calculs if d["moteur"].get("environnement")}
    if len(environnements) > 1:
        incoherences.append(_incoherence("info", "environnements_differents",
                                         "Versions de Python ou des bibliothèques différentes selon les calculs.",
                                         [c["fichier"] for c in liste]))

    registre: dict[str, list] = {"choix_de_jugement": [], "valeurs_par_defaut": [], "hypotheses_de_methode": []}
    for (cat, _, _), v in sorted(hyp.items(), key=lambda t: (t[0][0], t[0][1], t[0][2])):
        registre[cat].append(v)
    ordre = {"bloquant": 0, "alerte": 1, "info": 2}
    incoherences.sort(key=lambda i: ordre[i["gravite"]])
    decompte = {g: sum(1 for i in incoherences if i["gravite"] == g) for g in ordre}
    return {
        "dossier_des_sorties": str(base),
        "conclusion": "bloquant" if decompte["bloquant"] else ("a_examiner" if decompte["alerte"] else "coherent"),
        "n_calculs": len(liste),
        "decompte_incoherences": decompte,
        "incoherences": incoherences,
        "calculs": liste,
        "donnees": donnees,
        "hypotheses": registre,
        "fichiers_ignores": ignores,
    }


def _md(v: Any) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return str(s).replace("|", "\\|").replace("\n", " ")


def note_markdown(r: dict, titre: str) -> str:
    l = [f"# {titre}", "",
         f"Registre établi le {datetime.now(timezone.utc).strftime('%Y-%m-%d à %H:%M UTC')} par le moteur "
         f"claude_actuaire à partir de {r['n_calculs']} sortie(s) archivée(s) du dossier `{r['dossier_des_sorties']}`. "
         f"Conclusion du contrôle : "
         f"**{r['conclusion'].replace('_', ' ')}**.", ""]
    l += ["## Incohérences du dossier", ""]
    if r["incoherences"]:
        l += ["| Gravité | Problème | Calculs |", "| --- | --- | --- |"]
        l += [f"| {i['gravite']} | {_md(i['message'])} | {_md(', '.join(i['calculs']))} |" for i in r["incoherences"]]
    else:
        l.append("Aucune.")
    l += ["", "## Calculs", "", "| Fichier | Méthode | Statut | Version | Date (UTC) | Empreinte des résultats |",
          "| --- | --- | --- | --- | --- | --- |"]
    for c in r["calculs"]:
        emp = "absente" if c["empreinte_resultats"] is None else (
            f"{c['empreinte_resultats'][:12]}… " + ("vérifiée" if c["empreinte_verifiee"] else "**ne correspond pas**"))
        l.append(f"| {_md(c['fichier'])} | {c['methode']} | {c['statut']} | {c['version_moteur']} | "
                 f"{c['horodatage_utc']} | {emp} |")
    l += ["", "Commandes de reproduction :", ""]
    l += [f"- `{c['commande']}`" for c in r["calculs"] if c["commande"]]
    l += ["", "## Données", "", "| Fichier | SHA-256 | Utilisé par | État actuel |", "| --- | --- | --- | --- |"]
    for d in r["donnees"]:
        for v in d["versions"]:
            etat = ("introuvable" if d["sha256_actuel"] is None else
                    ("inchangé" if d["sha256_actuel"] == v["sha256"] else "**modifié depuis**"))
            l.append(f"| {_md(d['fichier'])} | {v['sha256'][:16]}… | {_md(', '.join(v['calculs']))} | {etat} |")
    titres = {"choix_de_jugement": ("Choix de jugement", "Options passées explicitement : chacune doit être justifiée "
                                    "dans le dossier (source, date, auteur)."),
              "valeurs_par_defaut": ("Valeurs par défaut à confirmer", "Le moteur les a retenues faute d'option : "
                                     "l'actuaire confirme qu'elles conviennent au dossier."),
              "hypotheses_de_methode": ("Hypothèses de méthode", "Propres à la méthode, rappelées pour la note.")}
    for cat, (t, intro) in titres.items():
        l += ["", f"## {t}", "", intro, ""]
        if not r["hypotheses"][cat]:
            l.append("Aucune.")
            continue
        l += ["| Hypothèse | Valeur | Justification | Calculs |", "| --- | --- | --- | --- |"]
        l += [f"| {_md(h['nom'])} | {_md(h['valeur'])} | {_md(h['justification'])} | {_md(', '.join(h['calculs']))} |"
              for h in r["hypotheses"][cat]]
    l += ["", "## Avertissements du moteur", ""]
    av = [(c["fichier"], a) for c in r["calculs"] for a in c["avertissements"]]
    l += [f"- {_md(f)} : {_md(a)}" for f, a in av] or ["Aucun."]
    if r["fichiers_ignores"]:
        l += ["", "## Fichiers ignorés", ""] + [f"- {_md(i['fichier'])} : {i['raison']}" for i in r["fichiers_ignores"]]
    l += ["", "---", "", "Note générée par le moteur : les décisions et leurs justifications restent à compléter et à "
          "signer par l'actuaire responsable.", ""]
    return "\n".join(l)


def args_registre(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--sorties", nargs="+", required=True,
                    help="Sorties JSON du moteur, ou dossiers (tous leurs fichiers .json, sous-dossiers compris).")
    sp.add_argument("--note", help="Écrit la note d'hypothèses du dossier en Markdown à ce chemin.")
    sp.add_argument("--titre", default="Registre des hypothèses du dossier", help="Titre de la note.")
    sp.add_argument("--sans-verifier-entrees", action="store_true",
                    help="Ne pas recalculer l'empreinte actuelle des fichiers de données.")


def cmd_registre(args) -> Resultat:
    fichiers = _fichiers(args.sorties)
    if args.note and any(Path(args.note).resolve() == f.resolve() for f in fichiers):
        raise ValueError("la note ne peut pas remplacer une des sorties lues")
    res = Resultat("registre", {}, options={"note": args.note, "verifier_entrees": not args.sans_verifier_entrees})
    for f in fichiers:
        res.ajouter_entree(f, "sortie_moteur")
    r = construire_registre(fichiers, not args.sans_verifier_entrees)
    if args.note:
        texte = note_markdown(r, args.titre)
        Path(args.note).parent.mkdir(parents=True, exist_ok=True)
        Path(args.note).write_text(texte, encoding="utf-8")
        r["note"] = {"fichier": args.note, "sha256": empreinte_fichier(args.note)}
    res.resultats = r
    d = r["decompte_incoherences"]
    if d["bloquant"]:
        res.avertissements.append(f"{d['bloquant']} incohérence(s) bloquante(s) : le dossier ne peut pas être présenté "
                                  "tel quel.")
    if d["alerte"]:
        res.avertissements.append(f"{d['alerte']} incohérence(s) à examiner.")
    if r["fichiers_ignores"]:
        res.avertissements.append(f"{len(r['fichiers_ignores'])} fichier(s) ignoré(s) : pas des sorties du moteur.")
    return res


COMMANDES = {
    "registre": (cmd_registre, "Registre des hypothèses d'un dossier : consolide les sorties archivées, classe les "
                 "hypothèses, détecte les incohérences, écrit la note d'hypothèses.", args_registre),
}
