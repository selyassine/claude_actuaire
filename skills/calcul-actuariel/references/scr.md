# Agrégation SCR (Solvabilité II)

Fichier de référence du skill `calcul-actuariel` pour la commande `scr`. Les règles générales (aucun chiffre sans script, citer la sortie et ses hypothèses, ne pas contourner un refus) sont dans SKILL.md et s'appliquent ici.

| Commande | Rôle | Statut |
| --- | --- | --- |
| `scr` | Agrégation formule standard : sous-modules, modules, BSCR, risque opérationnel, ajustements, SCR | testé : SFCR CCR 2024 (S.25.01) et IPBP 2016, à l'euro |

`scr` agrège des SCR déjà calculés (il n'applique pas les chocs). Entrée JSON, chaque module étant un nombre ou un dictionnaire de sous-modules :

```json
{"marche": {"scenario_taux": "baisse", "taux": 65.0, "actions": 49.2, "immobilier": 7.4, "spread": 20.1, "change": 1.9, "concentration": 4.0},
 "contrepartie": {"type1": 11.2, "type2": 0.05},
 "vie": {"mortalite": 0, "longevite": 30.3, "invalidite": 0, "cessation": 0, "frais": 19.3, "revision": 0, "catastrophe": 0},
 "sante": {"slt": {"longevite": 1.6, "frais": 0.3, "revision": 3.4}, "nslt": {"primes_provisions": 9.4, "cessation": 0}, "catastrophe": {"accident_de_masse": 1.0, "concentration": 0.75, "pandemie": 1.0}},
 "non_vie": {"primes_provisions": 50, "cessation": 5, "catastrophe": {"naturelle": 30, "reassurance_non_proportionnelle_dommages": 0, "humaine": 20, "autres": 5}},
 "incorporels": 0,
 "operationnel": {"op": 4.0, "exp_ul": 0},
 "ajustements": {"provisions_techniques": -4.2, "impots_differes": -11.2, "fonds_cantonnes": 0}}
```

`scenario_taux` (`hausse` ou `baisse`) fixe le paramètre A de l'article 164 : demande-le à l'utilisateur s'il manque, ne le devine pas. Les capacités d'absorption se saisissent en négatif. `operationnel` peut aussi être un montant déjà calculé.
