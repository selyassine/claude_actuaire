# Calcul indépendant du moteur : règles de provisions non-vie de l'arrêté tunisien du 27 février 2001
# (art. 17, 19, 21, 22, 24, 25, 27). Lancer depuis la racine du dépôt :
#   Rscript tests/references/r/provisions_tunisie.R > tests/references/r/provisions_tunisie.sortie.txt
suppressPackageStartupMessages(library(jsonlite))
d <- fromJSON("tests/donnees/tunisie/provisions.json", simplifyVector = TRUE)
p <- function(nom, x) cat(sprintf("%s = %.15g\n", nom, x))

cat("== ppna (art. 17, jours exacts) ==\n")
inv <- as.Date(d$ppna$date_inventaire)
k <- d$ppna$contrats
eff <- as.Date(k$date_effet); ech <- as.Date(k$date_echeance)
duree <- as.numeric(ech - eff)
jours <- ifelse(inv >= ech, 0, ifelse(inv < eff, duree, as.numeric(ech - inv)))
ppna <- k$prime_commerciale * jours / duree
for (cat in unique(k$categorie)) p(paste0("ppna_", cat), sum(ppna[k$categorie == cat]))
p("ppna_total", sum(ppna))

cat("== prc (art. 19) ==\n")
tot <- 0
for (cat in names(d$prc)) {
  v <- d$prc[[cat]]
  r <- (v$charge_sinistres + v$frais) / v$primes_acquises
  m <- max(r - 1, 0) * v$ppna
  p(paste0("prc_ratio_", cat), r); p(paste0("prc_", cat), m); tot <- tot + m
}
p("prc_total", tot)

cat("== frais de gestion des sinistres (art. 21, 5 % de la PSAP frais compris) ==\n")
f <- d$frais_gestion_sinistres
mini <- f$psap_hors_frais * 0.05 / 0.95
p("fgs_minimum", mini); p("fgs_retenus", max(mini, f$frais_estimes))

cat("== auto matériels (art. 22) ==\n")
tri <- as.matrix(read.csv2("tests/donnees/tunisie/auto_materiels_payes.csv", row.names = 1, check.names = FALSE))
n <- ncol(tri)
fac <- sapply(1:(n - 1), function(j) { i <- which(!is.na(tri[, j + 1])); sum(tri[i, j + 1]) / sum(tri[i, j]) })
prov <- 0
for (i in 1:nrow(tri)) {
  der <- max(which(!is.na(tri[i, ])))
  ult <- tri[i, der] * if (der < n) prod(fac[der:(n - 1)]) else 1
  prov <- prov + ult - tri[i, der]
}
p("auto_cadences", prov)
p("auto_cout_moyen", d$auto_materiels$cout_moyen$nombre_dossiers * d$auto_materiels$cout_moyen$cout_moyen)
p("auto_provision", max(prov, d$auto_materiels$dossier_par_dossier,
                        d$auto_materiels$cout_moyen$nombre_dossiers * d$auto_materiels$cout_moyen$cout_moyen))

cat("== équilibrage (art. 24) et égalisation grêle (art. 25) ==\n")
e <- d$equilibrage
pl <- 1.5 * max(e$primes_nettes_5_exercices)
p("equilibrage_plafond", pl)
p("equilibrage_dotation", min(0.75 * e$excedent_technique, max(pl - e$provision_debut, 0)))
g <- d$egalisation_grele
p("grele_plafond", 2 * g$primes_exercice)
p("grele_reprise", min(-g$excedent_technique, g$provision_debut))
p("grele_provision_fin", g$provision_debut - min(-g$excedent_technique, g$provision_debut))

cat("== rentes (art. 27) ==\n")
p("rentes_provision_chargee", 1.05 * d$rentes$provision_mathematique)
