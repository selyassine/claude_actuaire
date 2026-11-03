"""Assurance vie : modèles de survie, valeurs actuelles, primes et provisions mathématiques.

Conventions (AMLCR, Dickson, Hardy et Waters) :
- temps discret annuel : capital décès payé en fin d'année du décès, primes et annuités payables
  d'avance (annuité « due ») ;
- modèle de survie : loi de Makeham mu_x = A + B c^x, ou table de q_x fournie ;
- sélection optionnelle de type SSSM : mu_[x]+s = k^(d-s) mu_(x+s) pour 0 <= s <= d, appliquée
  à la force de mortalité pour Makeham (SSSM d'AMLCR : k = 0,9, d = 2, sur le Makeham du SUSM) ;
  pour une table de q_x, on applique q_[x]+s = k^(d-s) q_(x+s) pour s entier < d.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Points et poids de Gauss-Legendre sur [0, 1] pour intégrer la force de mortalité
_GL_X, _GL_W = np.polynomial.legendre.leggauss(20)
_GL_X = (_GL_X + 1.0) / 2.0
_GL_W = _GL_W / 2.0

AGE_MAX = 130


@dataclass
class ModeleSurvie:
    """Probabilités de décès annuelles, ultimes et sélectionnées."""

    q_ultime: dict[int, float]
    facteur_selection: float = 1.0
    periode_selection: int = 0
    description: str = ""
    makeham_params: tuple[float, float, float] | None = None

    @classmethod
    def makeham(cls, A: float, B: float, c: float, **kw) -> "ModeleSurvie":
        lc = math.log(c)
        q = {y: 1.0 - math.exp(-A - B * c ** y * (c - 1.0) / lc) for y in range(0, AGE_MAX + 1)}
        return cls(q, description=f"Makeham A={A}, B={B}, c={c}", makeham_params=(A, B, c), **kw)

    def _q_select_makeham(self, x: int, s: int) -> float:
        A, B, c = self.makeham_params
        k, d = self.facteur_selection, self.periode_selection
        u = s + _GL_X
        mu = A + B * c ** (x + u)
        facteur = np.where(u < d, k ** (d - u), 1.0)
        return 1.0 - math.exp(-float(np.sum(_GL_W * facteur * mu)))

    @classmethod
    def table(cls, qx: dict[int, float], **kw) -> "ModeleSurvie":
        return cls(dict(qx), description="table de q_x fournie", **kw)

    def q(self, age_selection: int, duree: int) -> float:
        """q_[x]+s : probabilité de décès dans l'année pour une vie sélectionnée à x, après s années."""
        y = age_selection + duree
        if y not in self.q_ultime:
            return 1.0
        base = self.q_ultime[y]
        if duree < self.periode_selection and self.makeham_params is not None:
            return self._q_select_makeham(age_selection, duree)
        if duree < self.periode_selection:
            return base * self.facteur_selection ** (self.periode_selection - duree)
        return base

    def vecteur_q(self, age_selection: int, duree: int, n: int | None = None) -> np.ndarray:
        """q successifs à partir de [x]+s, jusqu'à l'âge maximal (ou n années)."""
        nb = AGE_MAX - (age_selection + duree) + 1 if n is None else n
        out = np.array([self.q(age_selection, duree + t) for t in range(max(nb, 0))])
        if n is None and out.size:
            out[-1] = 1.0  # fermeture de la table
        return out


@dataclass
class Base:
    modele: ModeleSurvie
    taux: float

    @property
    def v(self) -> float:
        return 1.0 / (1.0 + self.taux)

    def survie(self, x: int, s: int, n: int) -> np.ndarray:
        """t p_[x]+s pour t = 0..n."""
        q = self.modele.vecteur_q(x, s)
        p = np.concatenate([[1.0], np.cumprod(1.0 - q)])
        if n + 1 > p.size:
            p = np.concatenate([p, np.zeros(n + 1 - p.size)])
        return p[: n + 1]

    def horizon(self, x: int, s: int, n: int | None) -> int:
        reste = AGE_MAX - (x + s) + 1
        return reste if n is None else min(n, reste)

    def annuite_due(self, x: int, s: int = 0, n: int | None = None) -> float:
        """ä_[x]+s:n (n = None : vie entière)."""
        h = self.horizon(x, s, n)
        p = self.survie(x, s, h)
        return float(sum(p[t] * self.v ** t for t in range(h)))

    def assurance_deces(self, x: int, s: int = 0, n: int | None = None) -> float:
        """A^1_[x]+s:n, capital payé en fin d'année du décès (n = None : vie entière)."""
        h = self.horizon(x, s, n)
        q = self.modele.vecteur_q(x, s)
        p = self.survie(x, s, h)
        return float(sum(p[t] * q[t] * self.v ** (t + 1) for t in range(h)))

    def capital_differe(self, x: int, s: int, n: int) -> float:
        """nE_[x]+s."""
        return float(self.survie(x, s, n)[n] * self.v ** n)

    def esperance_vie_entiere(self, x: int, s: int = 0) -> float:
        """e_[x]+s (espérance de vie en années entières)."""
        h = self.horizon(x, s, None)
        return float(self.survie(x, s, h)[1:].sum())


@dataclass
class Contrat:
    type: str                    # "vie-entiere", "temporaire", "mixte"
    age: int
    capital: float
    duree: int | None = None     # durée de couverture (None pour vie entière)
    duree_primes: int | None = None
    frais_initiaux_pct: float = 0.0
    frais_initiaux_fixe: float = 0.0
    frais_renouvellement_pct: float = 0.0
    frais_renouvellement_fixe: float = 0.0

    def __post_init__(self):
        if self.type not in ("vie-entiere", "temporaire", "mixte"):
            raise ValueError(f"type de contrat inconnu : {self.type}")
        if self.type != "vie-entiere" and not self.duree:
            raise ValueError("la durée est obligatoire pour un contrat temporaire ou mixte")
        if self.duree_primes is None:
            self.duree_primes = self.duree


def _restant(total: int | None, t: int) -> int | None:
    return None if total is None else max(total - t, 0)


def epv_prestations(base: Base, c: Contrat, t: int) -> float:
    """Valeur actuelle des prestations futures à la durée t (vie sélectionnée à l'âge de souscription)."""
    if c.duree is not None and t > c.duree:
        return 0.0
    n = _restant(c.duree, t)
    if n == 0:
        return c.capital if c.type == "mixte" else 0.0
    a = base.assurance_deces(c.age, t, n)
    if c.type == "mixte":
        a += base.capital_differe(c.age, t, n)
    return c.capital * a


def annuite_primes(base: Base, c: Contrat, t: int) -> float:
    m = _restant(c.duree_primes, t)
    if m == 0:
        return 0.0
    return base.annuite_due(c.age, t, m)


def tarifer(base: Base, c: Contrat, durees: list[int]) -> dict:
    """Primes pure, commerciale et de chargement ; provisions nette, brute, de frais et Zillmer FPT."""
    B0 = epv_prestations(base, c, 0)
    a0 = annuite_primes(base, c, 0)
    if a0 <= 0:
        raise ValueError("aucune prime à payer : vérifier la durée de paiement des primes")
    Pn = B0 / a0
    rp, rf = c.frais_renouvellement_pct, c.frais_renouvellement_fixe
    ip, if_ = c.frais_initiaux_pct, c.frais_initiaux_fixe
    # Frais initiaux à t = 0 à la place des frais de renouvellement, renouvellement aux échéances suivantes
    denom = (1 - rp) * a0 - (ip - rp)
    Pg = (B0 + rf * a0 + (if_ - rf)) / denom
    Pe = Pg - Pn

    # Méthode de Zillmer complète (FPT) : coût d'assurance de la 1re année, puis prime nette à [x]+1
    P1 = c.capital * base.v * base.modele.q(c.age, 0)
    B1 = epv_prestations(base, c, 1)
    a1 = annuite_primes(base, c, 1)
    P_fpt = B1 / a1 if a1 > 0 else 0.0

    provisions = {}
    for t in durees:
        if t == 0:
            provisions[str(t)] = {"nette": 0.0, "brute": 0.0, "frais": 0.0, "fpt": 0.0}
            continue
        Bt = epv_prestations(base, c, t)
        at = annuite_primes(base, c, t)
        Vn = Bt - Pn * at
        Vg = Bt + rf * at - (1 - rp) * Pg * at
        Vfpt = Bt - P_fpt * at
        provisions[str(t)] = {"nette": Vn, "brute": Vg, "frais": Vg - Vn, "fpt": Vfpt}

    return {
        "prime_nette": Pn,
        "prime_commerciale": Pg,
        "chargement": Pe,
        "fpt": {"prime_premiere_annee": P1, "prime_annees_suivantes": P_fpt},
        "valeurs_actuelles": {"prestations": B0, "annuite_primes": a0},
        "provisions": provisions,
    }
