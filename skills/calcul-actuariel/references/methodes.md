# Méthodes et publications de validation

Chaque méthode n'est marquée « disponible » que lorsque ses tests reproduisent les valeurs publiées et que ces valeurs ont été contrôlées par un actuaire.

| Méthode | Publication de référence | Statut |
| --- | --- | --- |
| Chain Ladder | Friedland (2010), ch. 7, Exhibit I (déclarés et payés, au dollar près) ; Mack (1993), tableau 2 (Taylor-Ashe, au millier près) | disponible, fiches validées par Yassine |
| Bornhuetter-Ferguson, Cape Cod | Friedland (2010), ch. 9 Exhibit I et ch. 10 Exhibit I (au dollar près) | disponible, fiches validées par Yassine |
| Mack | Mack (1993), tableau 3 (Taylor-Ashe) ; England et Verrall (2002), tableaux 12-14 (RAA, à l'unité) | disponible, fiches validées par Yassine |
| ODP analytique, bootstrap ODP | England et Verrall (2002), tableaux 2-3 (à 0,1 %) et 33-34 (à 5 %, Monte-Carlo) | disponible, fiches validées par Yassine |
| Survie, primes, provisions nette, brute et FPT | Dickson, Hardy, Waters, note MLC (SOA 2012), exemples SN2.3 et SN2.4 (SSSM, 4 %, au centime) | disponible, fiche validée par Yassine |
| GPD | McNeil (1997), ASTIN Bulletin 27(1), tableau 1 et section 4.5 (données danoises du paquet R evir ; dépassements et xi exacts, quantiles à 1,5 %) | disponible, fiches validées par Yassine |
| Tranche XL annuelle (Poisson × GPD, Panjer) | Calcul indépendant du moteur avec R : evir (ajustement GPD des données danoises) et actuar (discrétisation, récurrence de Panjer, VaR, CTE) ; cohérence avec la prime par sinistre de McNeil (1997) section 4.5 | disponible, fiches validées par Yassine |
| Crédibilité | Vignette « Credibility theory features of actuar » (Dutang, Goulet, Milhaud, Pigeon), sorties publiées sur les données de Hachemeister (1975) ; formules de Bühlmann et Gisler (2005) | disponible, fiches validées par Yassine |
| Marge de solvabilité tunisienne (art. 58 et 58 bis) | Code des assurances tunisien (loi n° 2002-37) ; aucun exemple publié : 3 cas construits recalculés indépendamment en R | disponible, fiches en attente de validation |
| Tables TD99 / TV99 | Arrêté du 27/02/2001, art. 5 (modifié le 5/01/2009), tables du Code des assurances pp. 200-207 ; q_x imprimés recoupés avec les l_x jusqu'à 91 ans ; annuités recalculées en R | disponible, transcription et fiches en attente de validation |
| Agrégation SCR | Règlement délégué (UE) 2015/35 (annexe IV, art. 114, 119, 136, 144, 146, 151, 160, 164, 200, 204) ; testé sur les SFCR publiés de CCR (2024, S.25.01) et de l'IPBP (2016 : BSCR, marché, contrepartie, vie, santé), à l'euro | disponible, fiches et matrices validées par Yassine ; matrices non-vie (art. 114, 119) contrôlées contre le règlement mais sans cas publié détaillé |
