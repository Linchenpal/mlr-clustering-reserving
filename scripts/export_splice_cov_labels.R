# Export the covariate labels of the published SPLICE Complexity 5 covariate portfolio.
#
# Why this script exists
# ----------------------
# The SPLICE repository (agi-lab/SPLICE, datasets/complexity_5) publishes the
# covariate-adjusted portfolio as claim_5_cov.csv, payment_5_cov.csv and
# incurred_5_cov.csv, but not the covariate assigned to each claim (legal
# representation, injury severity, claimant age). SPLICE::generate_data()
# returns those labels in `$covariates_data`, so we regenerate the portfolio,
# check that it matches the published files, and export the labels.
#
# Package versions matter
# -----------------------
# With the CRAN releases (SynthETIC 1.1.1, SPLICE 1.1.2; checked on R 4.3.3,
# seed 42) the regenerated tables match the published CSVs to machine precision,
# including when generate_data() is called twice in the same session.
#
# The development version SynthETIC 1.1.2 on GitHub (Aug 2026 fix to
# simulate_covariates(), not yet on CRAN) gives the SAME covariate labels and
# adjusted claim sizes, but a different random-number stream afterwards, so
# delays, payments and case-estimate histories no longer match the published
# files. Use the CRAN versions to reproduce the published data.
#
# Note also (as observed by Nigel): for the same seed, the covariate and
# no-covariate portfolios differ. This is expected; do not mix their tables.
#
# Usage (from the repo root, with the CRAN versions installed):
#   Rscript scripts/export_splice_cov_labels.R
# Output: data/raw/splice/complexity_5/covariates_5_cov.csv

suppressMessages({
  library(SynthETIC)
  library(SPLICE)
})

cat("R", as.character(getRversion()),
    "| SynthETIC", as.character(packageVersion("SynthETIC")),
    "| SPLICE", as.character(packageVersion("SPLICE")), "\n")

data_dir <- file.path("data", "raw", "splice", "complexity_5")

dc <- generate_data(
  n_claims_per_period = 90,
  n_periods = 40,
  complexity = 5,
  random_seed = 42,
  covariates_obj = SynthETIC::test_covariates_obj,
  verbose = FALSE
)

# Check against the published files
same <- function(generated, file) {
  pub <- read.csv(file.path(data_dir, file))
  pub <- pub[, setdiff(names(pub), "X"), drop = FALSE]
  isTRUE(all.equal(as.data.frame(generated), pub, check.attributes = FALSE, tolerance = 1e-10))
}
checks <- c(
  claim    = same(dc$claim_dataset, "claim_5_cov.csv"),
  payment  = same(dc$payment_dataset, "payment_5_cov.csv"),
  incurred = same(dc$incurred_dataset, "incurred_5_cov.csv")
)
print(checks)
if (!all(checks)) {
  warning("Regenerated tables do not match the published files. ",
          "Use SynthETIC 1.1.1 and SPLICE 1.1.2 from CRAN. ",
          "The covariate labels are written anyway (they do not depend on the version).")
}

# Covariate labels: one row per claim, in claim_no order
cd  <- dc$covariates_data
ids <- unlist(cd$ids)
stopifnot(identical(as.integer(ids), seq_along(ids)))
lab <- cd$data
names(lab) <- c("legal_rep", "injury_severity", "claimant_age")
lab$claim_no <- ids
write.csv(lab[, c("claim_no", "legal_rep", "injury_severity", "claimant_age")],
          file.path(data_dir, "covariates_5_cov.csv"), row.names = FALSE)
cat("Wrote", nrow(lab), "covariate labels to", file.path(data_dir, "covariates_5_cov.csv"), "\n")
