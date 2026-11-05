# Valeurs de référence des fiches r-actuar-danish-tranche-xl-*.yaml, calculées sans le moteur.
# Rscript tests/references/r/tranche_xl.R > tests/references/r/tranche_xl.sortie.txt
# Paquets : evir (jeu danish, ajustement gpd) et actuar (discretize, aggregateDist, quantile, CTE).
suppressMessages({library(evir); library(actuar)})
data(danish)
x <- as.numeric(danish)
calc <- function(xi, beta, u=10, r=50, R=200, annees=11, h=0.15, D=20, L=300, lv=c(0.99,0.995)) {
  nu <- sum(x > u); lam <- nu/annees
  surv <- function(t) if (abs(xi) < 1e-12) exp(-(t-u)/beta) else pmax(1 + xi*(t-u)/beta, 0)^(-1/xi)
  m1 <- integrate(function(t) surv(t), r, R, rel.tol=1e-12)$value
  m2 <- integrate(function(t) 2*(t-r)*surv(t), r, R, rel.tol=1e-12)$value
  FL <- function(y) ifelse(y < 0, 0, ifelse(y < R - r, 1 - surv(r + pmax(y, 0)), 1))
  # depuis -h : le point 0 reçoit F(h/2) - F(-h/2), atome en 0 compris
  f <- discretize(FL(x), from=-h, to=R-r, step=h, method="rounding")[-1]
  f <- c(f, 1 - sum(f))
  Fs <- aggregateDist("recursive", model.freq="poisson", model.sev=f, lambda=lam, x.scale=h,
                      tol=1e-12, maxit=1e6)
  k <- knots(Fs); p <- diff(c(0, Fs(k)))
  ced <- pmin(pmax(k - D, 0), L)
  e <- sum(ced*p)
  out <- list(xi=xi, sigma=beta, n_dep=nu, lam=lam, m1=m1, prime=lam*m1, sd=sqrt(lam*m2),
              p0=p[1], prime_disc=sum(k*p),
              var=as.numeric(quantile(Fs, lv)), cte=as.numeric(CTE(Fs, lv)),
              aad_prime=e, aad_sd=sqrt(sum(ced^2*p)-e^2), p_D=sum(p[k > D]), p_L=sum(p[k >= D+L-1e-9]),
              s_r=surv(r), s_R=surv(R))
  out
}
g <- gpd(x, 10)
cat("== evir fit\n"); print(unlist(calc(g$par.ests[["xi"]], g$par.ests[["beta"]])), digits=15)
cat("== exponentielle xi=0 sigma=7\n"); print(unlist(calc(0, 7)), digits=15)
bc <- sum(pmin(pmax(x-50,0),150))/11; cat("burning cost", format(bc, digits=15), sum(x>50), sum(x>=200), "\n")
cat(R.version.string, "actuar", as.character(packageVersion("actuar")), "evir", as.character(packageVersion("evir")), "\n")
