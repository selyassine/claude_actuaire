# Calcul indépendant du moteur : marge de solvabilité minimale tunisienne (Code des assurances, art. 58 et 58 bis)
# et annuités sur les tables TD99 / TV99. Lancer depuis la racine du dépôt :
#   Rscript tests/references/r/marge_tunisie.R > tests/references/r/marge_tunisie.sortie.txt
suppressPackageStartupMessages(library(jsonlite))
options(digits = 15)

retention <- function(net, brut, plancher) max(net / brut, plancher)

marge <- function(fichier) {
  d <- fromJSON(fichier, simplifyVector = TRUE)
  out <- list()
  total <- 0
  if (!is.null(d$non_vie)) {
    nv <- d$non_vie
    credit <- isTRUE(nv$assurance_credit)
    n <- if (credit) 7 else 3
    stopifnot(length(nv$sinistres$reglements) == n)
    s <- nv$sinistres
    rec <- if (is.null(s$recours_encaisses)) 0 else s$recours_encaisses
    charge <- sum(s$reglements) + s$psap_fin - s$psap_debut - rec
    a <- 0.20 * nv$primes_emises_acceptees * retention(nv$primes_retenues, nv$primes_emises_acceptees, 0.5)
    b <- 0.25 * max(charge / n, 0) * retention(s$charge_nette, charge, 0.5)
    out$non_vie_base_primes <- a
    out$non_vie_charge_periode <- charge
    out$non_vie_base_sinistres <- b
    out$non_vie_minimum <- max(a, b)
    total <- total + max(a, b)
  }
  if (!is.null(d$vie)) {
    v <- d$vie
    csr <- if (!is.null(v$capitaux_sous_risque_bruts)) v$capitaux_sous_risque_bruts else
      v$capitaux_assures_bruts - v$provisions_mathematiques_brutes
    a <- 0.04 * v$provisions_mathematiques_brutes *
      retention(v$provisions_mathematiques_nettes, v$provisions_mathematiques_brutes, 0.85)
    b <- 0.003 * csr * retention(v$capitaux_sous_risque_nets, csr, 0.5)
    out$vie_pm <- a
    out$vie_capitaux_sous_risque <- b
    out$vie_minimum <- a + b
    total <- total + a + b
  }
  out$minimum_reglementaire <- total
  if (!is.null(d$marge_constituee)) {
    m <- d$marge_constituee
    g <- function(k) if (is.null(m[[k]])) 0 else m[[k]]
    mc <- g("capital_libere") + 0.5 * g("capital_non_libere") + g("reserves") + g("benefices_reportes") +
      g("plus_values_agreees") + g("autres_elements_agrees") + g("provision_equilibrage_takaful") -
      g("pertes") - g("actifs_incorporels")
    out$marge_constituee <- mc
    out$taux_couverture <- mc / total
  }
  out
}

for (f in c("marge_non_vie", "marge_vie", "marge_mixte_credit")) {
  cat("==", f, "==\n")
  r <- marge(file.path("tests/donnees/tunisie", paste0(f, ".json")))
  for (k in names(r)) cat(sprintf("%s = %.15g\n", k, r[[k]]))
}

# Annuités viagères d'avance (paiement en début d'année) sur les l_x transcrits, taux 3 %.
t <- read.csv2("skills/calcul-actuariel/scripts/actuaire/donnees/tables_tunisie_99.csv", dec = ".")
annuite <- function(lx, x, i) {
  l <- lx[!is.na(lx)]
  ages <- seq_along(l) - 1
  k <- ages[ages >= x] - x
  sum((1 + i)^(-k) * l[k + x + 1]) / l[x + 1]
}
for (tab in c("TD99", "TV99")) for (x in c(30, 60)) {
  cat(sprintf("== %s age %d taux 0.03 ==\nannuite_due_vie_entiere = %.15g\n", tab, x,
              annuite(t[[paste0("lx_", tab)]], x, 0.03)))
}
