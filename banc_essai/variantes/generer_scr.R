# Variantes SCR : agrégation formule standard écrite explicitement en R
# (règlement délégué (UE) 2015/35 : art. 87 et annexe IV, 114, 119, 136, 164, 189, 204).
# Pas de package R de référence : ces corrigés sont à recalculer par l'actuaire (Excel) avant validation.
# Exécution : Rscript generer_scr.R <dossier_taches>
suppressPackageStartupMessages(library(jsonlite))
out <- commandArgs(TRUE)[1]
agr <- function(v, M) sqrt(drop(t(v) %*% M %*% v))
corr_marche <- function(A) matrix(c(
  1, A, A, A, .25, 0,
  A, 1, .75, .75, .25, 0,
  A, .75, 1, .5, .25, 0,
  A, .75, .5, 1, .25, 0,
  .25, .25, .25, .25, 1, 0,
  0, 0, 0, 0, 0, 1), 6, byrow = TRUE)
corr_vie <- matrix(c(
  1, -.25, .25, 0, .25, 0, .25,
  -.25, 1, 0, .25, .25, .25, 0,
  .25, 0, 1, 0, .5, 0, .25,
  0, .25, 0, 1, .5, 0, .25,
  .25, .25, .5, .5, 1, .5, .25,
  0, .25, 0, 0, .5, 1, 0,
  .25, 0, .25, .25, .25, 0, 1), 7, byrow = TRUE)
corr_nv <- matrix(c(1, 0, .25, 0, 1, 0, .25, 0, 1), 3, byrow = TRUE)
corr_bscr <- matrix(c(
  1, .25, .25, .25, .25,
  .25, 1, .25, .25, .5,
  .25, .25, 1, .25, 0,
  .25, .25, .25, 1, 0,
  .25, .5, 0, 0, 1), 5, byrow = TRUE)
defaut <- function(t1, t2) sqrt(t1^2 + 1.5 * t1 * t2 + t2^2)
res <- list()

# v-scr-01 : assureur vie (milliers d'euros), choc de taux à la hausse le plus défavorable
mkt <- agr(c(41250, 63800, 9120, 27400, 3350, 5100), corr_marche(0))
def <- defaut(8640, 1270)
vie <- agr(c(6200, 18900, 0, 31500, 7800, 2100, 4300), corr_vie)
bscr <- agr(c(mkt, def, vie, 0, 0), corr_bscr)
op <- 6450
scr <- bscr + op - 9800 - 21400
res[["v-scr-01"]] <- list(scr_marche = mkt, scr_vie = vie, bscr = bscr, scr = scr)

# v-scr-02 : assureur non-vie (milliers d'euros), choc de taux à la baisse le plus défavorable
mkt2 <- agr(c(12300, 25600, 14800, 9700, 2200, 0), corr_marche(0.5))
def2 <- defaut(5400, 3900)
cat2 <- sqrt((21500 + 3800)^2 + 9200^2 + 4100^2)
nv2 <- agr(c(48700, 2600, cat2), corr_nv)
sante2 <- 7300
bscr2 <- agr(c(mkt2, def2, 0, sante2, nv2), corr_bscr) + 0   # actifs incorporels nuls
op2 <- min(0.3 * bscr2, 4900) + 0.25 * 0
scr2 <- bscr2 + op2 - 15600
res[["v-scr-02"]] <- list(scr_catastrophe_non_vie = cat2, scr_non_vie = nv2, bscr = bscr2, scr = scr2)

write_json(res, file.path(out, "corriges_scr.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
