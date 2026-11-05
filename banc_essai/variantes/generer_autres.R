# Variantes du banc d'essai : GPD (evir), crédibilité (actuar), vie (lifecontingencies).
# Données simulées avec une graine fixe ; corrigés calculés par les packages R.
# Exécution : Rscript generer_autres.R <dossier_taches>
suppressPackageStartupMessages({library(evir); library(actuar); library(lifecontingencies); library(jsonlite)})
args <- commandArgs(TRUE); out <- args[1]
set.seed(20261106)
dossier <- function(id) { d <- file.path(out, id); dir.create(d, showWarnings = FALSE, recursive = TRUE); d }
res <- list()

# ---- GPD : 1 900 sinistres tempête (en millions), simulés au-delà de 1 ----
x <- round(1 + rgpd(1900, xi = 0.55, mu = 0, beta = 1.1), 4)
for (id in c("v-gpd-01", "v-gpd-02"))
  write.csv(data.frame(Montant = x), file.path(dossier(id), "sinistres_tempete.csv"), row.names = FALSE)
n <- length(x)
queue <- function(fit, t) { xi <- fit$par.ests[["xi"]]; b <- fit$par.ests[["beta"]]; u <- fit$threshold
  (fit$n.exceed / n) * (1 + xi * (t - u) / b)^(-1 / xi) }
f1 <- gpd(x, threshold = 6)
r <- 25; R <- 100
tranche <- integrate(function(t) queue(f1, t), r, R, rel.tol = 1e-12)$value
res[["v-gpd-01"]] <- list(n_depassements = f1$n.exceed, xi = f1$par.ests[["xi"]],
  quantile_999 = unname(riskmeasures(f1, 0.999)[, "quantile"]), prime_tranche = tranche)
f2 <- gpd(x, threshold = 2.5)
res[["v-gpd-02"]] <- list(n_depassements = f2$n.exceed, xi = f2$par.ests[["xi"]], sigma = f2$par.ests[["beta"]],
  quantile_995 = unname(riskmeasures(f2, 0.995)[, "quantile"]), quantile_9999 = unname(riskmeasures(f2, 0.9999)[, "quantile"]))

# ---- Crédibilité : 6 portefeuilles, 10 années, coût moyen et nombre de sinistres ----
ne <- 6; np <- 10
cohorte <- rep(c("A", "B"), each = 3)
m_coh <- c(A = 2300, B = 1900)[cohorte]
theta <- m_coh + rnorm(ne, 0, 150)
poids <- matrix(sample(300:3000, ne * np, replace = TRUE), ne)
ratio <- round(theta + matrix(rnorm(ne * np), ne) * 9000 / sqrt(poids))
long <- data.frame(Entite = rep(1:ne, times = np), Cohorte = rep(cohorte, times = np),
                   Periode = rep(1:np, each = ne), Ratio = as.vector(ratio), Poids = as.vector(poids))
long <- long[order(long$Entite, long$Periode), ]
for (id in c("v-cred-01", "v-cred-02"))
  write.csv(long, file.path(dossier(id), "experience.csv"), row.names = FALSE, quote = FALSE)
large <- data.frame(entite = 1:ne, cohorte = cohorte, ratio = ratio, poids = poids)
names(large) <- c("entite", "cohorte", paste0("ratio.", 1:np), paste0("weight.", 1:np))
bs <- cm(~entite, large, ratios = ratio.1:ratio.10, weights = weight.1:weight.10)
res[["v-cred-01"]] <- list(prime_collective = bs$means$portfolio, variance_entre = unname(bs$unbiased[1]),
  variance_intra = unname(bs$unbiased[2]), credibilite_3 = bs$cred[3], prime_entite_3 = predict(bs)[3])
hi <- cm(~cohorte + cohorte:entite, large, ratios = ratio.1:ratio.10, weights = weight.1:weight.10, method = "iterative")
p <- predict(hi)
res[["v-cred-02"]] <- list(prime_collective = hi$means$portfolio, prime_cohorte_A = p$cohorte[1],
  prime_cohorte_B = p$cohorte[2], prime_entite_5 = p$entite[5])

# ---- Vie : loi de Makeham A = 0,0002, B = 0,00004, c = 1,11 (table exacte aux âges entiers, fermée à 131 ans) ----
A <- 2e-4; B <- 4e-5; cc <- 1.11
ages <- 0:131
lx <- 1e9 * exp(-A * ages - B / log(cc) * (cc^ages - 1))
# v-vie-01 : mixte 20 ans, 45 ans, 3 %, capital 50 000, frais 40 % + 150 puis 2,5 % + 20
t1 <- new("actuarialtable", x = ages, lx = lx, interest = 0.03)
C <- 50000; x0 <- 45; nn <- 20
Am <- function(x, n) Axn(t1, x, n) + Exn(t1, x, n)   # assurance mixte, capital fin d'année du décès ou à l'échéance
a <- axn(t1, x0, nn)
P <- C * Am(x0, nn) / a
G <- (C * Am(x0, nn) + 150 + 20 * (a - 1)) / (a - 0.40 - 0.025 * (a - 1))
V <- function(t) C * Am(x0 + t, nn - t) - P * axn(t1, x0 + t, nn - t)
W <- function(t) C * Am(x0 + t, nn - t) - (G - 0.025 * G - 20) * axn(t1, x0 + t, nn - t)
res[["v-vie-01"]] <- list(prime_commerciale = G, prime_pure = P, provision_nette_10 = V(10), provision_brute_10 = W(10))
# v-vie-02 : vie entière, 55 ans, 3,5 %, capital 80 000, primes pendant 20 ans, sans frais
t2 <- new("actuarialtable", x = ages, lx = lx, interest = 0.035)
C2 <- 80000; x2 <- 55; m <- 20
P2 <- C2 * Axn(t2, x2) / axn(t2, x2, m)
V2 <- function(t) C2 * Axn(t2, x2 + t) - (if (t < m) P2 * axn(t2, x2 + t, m - t) else 0)
res[["v-vie-02"]] <- list(annuite_due_55 = axn(t2, x2), prime_pure = P2, provision_nette_10 = V2(10), provision_nette_25 = V2(25))

write_json(res, file.path(out, "corriges_autres.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
