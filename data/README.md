# Data

## Sources under discussion (per Sarah's proposal email, 30 June 2026)

- **SPLICE** — simulated claims data used for most of the WP's research.
  Suitability for clustering not yet confirmed.
- **Canadian regulator data** — previously flagged by other WP members as too
  "messy" to be useful without further cleaning.

## Folder convention

- `raw/` — exactly as received, never edited. If you clean it, save the result
  to `processed/` instead.
- `processed/` — cleaned/derived datasets that notebooks and `src/` code read from.

Add a short note here (or a per-dataset `.md` file) whenever a new data source is added.

## SPLICE datasets in `raw/splice/`

| Folder | Content | Source |
|---|---|---|
| `complexity_1/` … `complexity_4/` | `claim_k`, `payment_k`, `incurred_k` (standard portfolios) | agi-lab/SPLICE `datasets/`, seed 42 |
| `complexity_5/` | standard tables, the published covariate tables `*_cov`, and `covariates_5_cov.csv` (legal_rep, injury_severity, claimant_age per claim, keyed by `claim_no`) | agi-lab/SPLICE `datasets/complexity_5`, seed 42; labels exported with `scripts/export_splice_cov_labels.R` |

Notes:

- **Reproducibility depends on package versions.** With the CRAN releases (SynthETIC 1.1.1,
  SPLICE 1.1.2; R 4.3.3, seed 42) the published `*_cov` files reproduce exactly. The GitHub
  development version SynthETIC 1.1.2 (Aug 2026 fix to `simulate_covariates()`) gives the same
  covariate labels and claim sizes but different delays, payments and case estimates. Use the
  CRAN versions to reproduce the published data. (An earlier version of this repo used a
  portfolio regenerated with the development version, `complexity_5_cov_regen/`; it is no
  longer used and can be deleted.)
- For the same seed, the covariate and standard portfolios differ in everything drawn after
  the covariate step. Do not mix their tables.
- `SynthETIC::test_covariates_dataset` (the `.rda` Sarah linked) labels SynthETIC's own
  example portfolio (3,624 claims), not SPLICE Complexity 5 (3,663 claims), so it cannot
  be joined to these files.
- `claim_size` is in constant (time-0) money. Paid cash is `payment_inflated`, which
  accumulates to `cumpaid` in the incurred table. In Complexity 5 total inflated payments are
  1.83 times total `claim_size` (3.7 times on average per claim, because small claims carry
  the most superimposed inflation). Use `payment_inflated` for reserving.

To re-export the covariate labels (and check the published files), with the CRAN versions:

```bash
Rscript scripts/export_splice_cov_labels.R
```
