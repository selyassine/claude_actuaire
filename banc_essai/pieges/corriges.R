# Corrigés numériques de la famille « pièges », calculés indépendamment du moteur.
# Lancer depuis la racine du dépôt :
#   Rscript banc_essai/pieges/corriges.R > banc_essai/pieges/corriges.sortie.txt
options(digits = 15)
ret <- function(net, brut, plancher) max(net / brut, plancher)
cat0 <- function(k, v) cat(sprintf("%s = %.15g\n", k, v))

# p-tn-marge-2ex : seuls 2 exercices de règlements fournis ; seule la base primes est calculable.
cat("== p-tn-marge-2ex ==\n")
cat0("base_primes", 0.20 * 52000 * ret(39000, 52000, 0.5))

# p-tn-marge-ttc : primes données TTC (taxes 9 200) ; l'art. 58 bis porte sur les primes hors taxes.
cat("== p-tn-marge-ttc ==\n")
p_ht <- 61200 - 9200
bp <- 0.20 * p_ht * ret(20000, p_ht, 0.5)
ch <- sum(c(14000, 15500, 16000)) + 61000 - 55000 - 1500
bs <- 0.25 * (ch / 3) * ret(46000, ch, 0.5)
cat0("base_primes", bp); cat0("base_sinistres", bs); cat0("minimum_reglementaire", max(bp, bs))

# p-tn-marge-recours : recours encaissés importants, à déduire de la charge.
cat("== p-tn-marge-recours ==\n")
bp <- 0.20 * 20000 * ret(18000, 20000, 0.5)
ch <- sum(c(31000, 33000, 35000)) + 90000 - 70000 - 12000
bs <- 0.25 * (ch / 3) * ret(40000, ch, 0.5)
cat0("charge_periode", ch); cat0("base_primes", bp); cat0("base_sinistres", bs)
cat0("minimum_reglementaire", max(bp, bs))
