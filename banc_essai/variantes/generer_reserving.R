# Variantes du banc d'essai : données modifiées et corrigés calculés par le package R ChainLadder.
# Exécution : Rscript generer_reserving.R <dossier_taches>
suppressPackageStartupMessages({library(ChainLadder); library(jsonlite)})
args <- commandArgs(TRUE); out <- args[1]
set.seed(20261105)

perturber <- function(tri, echelle, sd = 0.08) {
  inc <- cum2incr(tri)
  bruit <- matrix(exp(rnorm(length(inc), 0, sd)), nrow(inc))
  inc2 <- round(inc * bruit * echelle)
  incr2cum(as.triangle(inc2))
}
ecrire_tri <- function(tri, fichier, origines) {
  m <- unclass(tri); df <- data.frame(Origine = origines, m, check.names = FALSE)
  colnames(df) <- c("Origine", seq_len(ncol(m)))
  df[is.na(df)] <- ""
  write.csv(df, fichier, row.names = FALSE, quote = FALSE, na = "")
}
dossier <- function(id) { d <- file.path(out, id); dir.create(d, showWarnings = FALSE, recursive = TRUE); d }
res <- list()
prov <- function(tri, cdf) { n <- nrow(tri); diag <- getLatestCumulative(tri); sum(diag * (cdf[n:1] - 1)) }

# v-cl-01 : RAA modifié, Chain Ladder pondéré toutes années, sans queue
t1 <- perturber(RAA, 1.37); dimnames(t1) <- list(origin = 2011:2020, dev = 1:10)
ecrire_tri(t1, file.path(dossier("v-cl-01"), "triangle.csv"), 2011:2020)
cl <- chainladder(t1); f <- sapply(cl$Models, function(m) coef(m)[[1]])
cdf <- rev(cumprod(rev(c(f, 1))))
lat <- getLatestCumulative(t1); ult <- lat * cdf[10:1]
res[["v-cl-01"]] <- list(provision_totale = sum(ult - lat), ultime_2020 = unname(ult[10]), facteur_1_2 = f[1])

# v-cl-02 : UKMotor modifié, facteurs pondérés sur les 3 dernières années calendaires
t2 <- perturber(UKMotor, 0.83); n2 <- nrow(t2); dimnames(t2) <- list(origin = 2014:(2014 + n2 - 1), dev = 1:ncol(t2))
ecrire_tri(t2, file.path(dossier("v-cl-02"), "triangle.csv"), 2014:(2014 + n2 - 1))
w <- matrix(0, n2, n2); for (i in 1:n2) for (j in 1:n2) if (i + j - 1 >= n2 - 3) w[i, j] <- 1  # liens dont la fin tombe dans les 3 dernières diagonales
cl2 <- chainladder(t2, weights = w); f2 <- sapply(cl2$Models, function(m) coef(m)[[1]])
cdf2 <- rev(cumprod(rev(c(f2, 1)))); lat2 <- getLatestCumulative(t2); ult2 <- lat2 * cdf2[n2:1]
res[["v-cl-02"]] <- list(provision_totale = sum(ult2 - lat2), cdf_1 = cdf2[1], facteur_1_2 = f2[1])

# v-bf-01 et v-bf-02 : GenIns modifié, BF et Cape Cod avec cadence ChainLadder toutes années
t3 <- perturber(GenIns, 0.61); n3 <- nrow(t3); or3 <- 2013:(2013 + n3 - 1); dimnames(t3) <- list(origin = or3, dev = 1:n3)
cl3 <- chainladder(t3); f3 <- sapply(cl3$Models, function(m) coef(m)[[1]]); cdf3 <- rev(cumprod(rev(c(f3, 1))))
lat3 <- getLatestCumulative(t3); cdfo <- cdf3[n3:1]; ultcl <- lat3 * cdfo
prime <- round(ultcl / runif(n3, 0.58, 0.74) * exp(rnorm(n3, 0, 0.05)))
apriori <- round(prime * 0.66)
for (id in c("v-bf-01", "v-bf-02")) {
  ecrire_tri(t3, file.path(dossier(id), "triangle.csv"), or3)
  write.csv(data.frame(Origine = or3, Prime = prime, Ultime_a_priori = apriori), file.path(dossier(id), "primes.csv"), row.names = FALSE, quote = FALSE)
}
ultbf <- lat3 + (1 - 1 / cdfo) * apriori
res[["v-bf-01"]] <- list(ultime_total = sum(ultbf), ibnr_total = sum(ultbf - lat3), ultime_derniere = unname(ultbf[n3]))
elr <- sum(lat3) / sum(prime / cdfo)
ultcc <- lat3 + (1 - 1 / cdfo) * elr * prime
res[["v-bf-02"]] <- list(ratio_cape_cod = elr, ultime_total = sum(ultcc), ibnr_total = sum(ultcc - lat3))

# v-mack-01 et v-mack-02 : MackChainLadder (extrapolation de Mack pour le dernier sigma)
t4 <- perturber(ABC, 0.0021); n4 <- nrow(t4); or4 <- 2012:(2012 + n4 - 1); dimnames(t4) <- list(origin = or4, dev = 1:ncol(t4))
ecrire_tri(t4, file.path(dossier("v-mack-01"), "triangle.csv"), or4)
m4 <- MackChainLadder(t4, est.sigma = "Mack"); lat4 <- getLatestCumulative(t4)
res[["v-mack-01"]] <- list(provision_totale = sum(m4$FullTriangle[, n4] - lat4),
  erreur_prediction_totale = m4$Total.Mack.S.E, erreur_prediction_derniere = unname(m4$Mack.S.E[n4, n4]))
t5 <- perturber(MW2008, 1.9); n5 <- nrow(t5); dimnames(t5) <- list(origin = 1:n5, dev = 1:ncol(t5))
ecrire_tri(t5, file.path(dossier("v-mack-02"), "triangle.csv"), 1:n5)
m5 <- MackChainLadder(t5, est.sigma = "Mack"); lat5 <- getLatestCumulative(t5); R5 <- m5$FullTriangle[, ncol(t5)] - lat5
res[["v-mack-02"]] <- list(erreur_relative_totale = m5$Total.Mack.S.E / sum(R5),
  erreur_relative_derniere = unname(m5$Mack.S.E[n5, ncol(t5)] / R5[n5]), sigma2_1_2 = m5$sigma[1]^2)

# v-odp-01 : MW2014 (incréments tous positifs, RAA en a un négatif) ; glmReserve (Poisson sur-dispersé, dispersion de Pearson) ; v-boot-01 : BootChainLadder
t6 <- perturber(MW2014, 0.8, sd = 0.1); n6 <- nrow(t6); or6 <- 2006:(2006 + n6 - 1); dimnames(t6) <- list(origin = or6, dev = 1:n6)
ecrire_tri(t6, file.path(dossier("v-odp-01"), "triangle.csv"), or6)
g <- glmReserve(t6, var.power = 1, mse.method = "formula")
res[["v-odp-01"]] <- list(dispersion = summary(g$model)$dispersion,
  provision_totale = g$summary["total", "IBNR"], erreur_prediction_totale = g$summary["total", "S.E"],
  erreur_prediction_derniere = g$summary[as.character(or6[n6]), "S.E"])
t7 <- perturber(GenIns, 0.0012, sd = 0.1); n7 <- nrow(t7); or7 <- 2011:(2011 + n7 - 1); dimnames(t7) <- list(origin = or7, dev = 1:n7)
ecrire_tri(t7, file.path(dossier("v-boot-01"), "triangle.csv"), or7)
set.seed(42); b <- BootChainLadder(t7, R = 20000, process.distr = "od.pois")
tot <- b$IBNR.Totals
res[["v-boot-01"]] <- list(provision_moyenne = mean(tot), erreur_prediction = sd(tot), quantile_95 = unname(quantile(tot, 0.95)))

write_json(res, file.path(out, "corriges_reserving.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
