# Regenerate the SPLICE Complexity 5 covariate portfolio and export the covariate labels.
#
# Why this script exists
# ----------------------
# The published SPLICE `_cov` CSVs (agi-lab/SPLICE, datasets/complexity_5) do
# not include the covariates assigned to each claim, and they cannot be
# reproduced exactly with the current package versions: occurrence times and
# claim sizes match, but notification delay, settlement delay, payments and
# case-estimate histories differ. `SynthETIC::test_covariates_dataset` cannot
# be used instead, because it labels SynthETIC's own example portfolio
# (3,624 claims, different per-period counts), not the SPLICE portfolio
# (3,663 claims).
#
# `SPLICE::generate_data()` returns the covariate labels in
# `$covariates_data`, so regenerating the portfolio gives a claim, payment,
# incurred and covariates set that is internally consistent.
#
# Checked with R 4.3.3, SynthETIC 1.1.2, SPLICE 1.1.2 (installed from the
# agi-lab GitHub sources). With these versions the standard (non-covariate)
# Complexity 5 tables reproduce the published CSVs to machine precision.
#
# Usage (from the repo root):
#   Rscript scripts/regenerate_splice_cov.R
# Output: data/raw/splice/complexity_5_cov_regen/

suppressMessages({
  library(SynthETIC)
  library(SPLICE)
})

out_dir <- file.path("data", "raw", "splice", "complexity_5_cov_regen")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("SynthETIC", as.character(packageVersion("SynthETIC")),
    "| SPLICE", as.character(packageVersion("SPLICE")), "\n")

dc <- generate_data(
  n_claims_per_period = 90,
  n_periods = 40,
  complexity = 5,
  random_seed = 42,
  covariates_obj = SynthETIC::test_covariates_obj
)

write.csv(dc$claim_dataset,    file.path(out_dir, "claim_5_cov.csv"))
write.csv(dc$payment_dataset,  file.path(out_dir, "payment_5_cov.csv"))
write.csv(dc$incurred_dataset, file.path(out_dir, "incurred_5_cov.csv"))

# Covariate labels: one row per claim, in claim_no order
cd  <- dc$covariates_data
ids <- unlist(cd$ids)
stopifnot(identical(as.integer(ids), seq_along(ids)))
lab <- cd$data
names(lab) <- c("legal_rep", "injury_severity", "claimant_age")
lab$claim_no <- ids
write.csv(lab[, c("claim_no", "legal_rep", "injury_severity", "claimant_age")],
          file.path(out_dir, "covariates_5_cov.csv"), row.names = FALSE)

cat("Claims:", nrow(dc$claim_dataset), "\n")
print(table(lab$injury_severity))
