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
| `complexity_5/` | `claim_5`, `payment_5`, `incurred_5` (standard) and `*_cov` (covariate-adjusted, **no covariate labels**) | agi-lab/SPLICE `datasets/complexity_5`, seed 42 |
| `complexity_5_cov_regen/` | covariate-adjusted portfolio **with** `covariates_5_cov.csv` (legal_rep, injury_severity, claimant_age per claim) | regenerated with `scripts/regenerate_splice_cov.R` |

Notes:

- The published `*_cov` CSVs do not reproduce with SynthETIC 1.1.2 / SPLICE 1.1.2. Claim
  sizes and occurrence times match, but delays, payments and incurred histories do not.
  The standard tables do reproduce exactly. Use `complexity_5_cov_regen/` whenever
  covariate labels are needed, and do not mix it with the published `*_cov` files.
- `SynthETIC::test_covariates_dataset` (the `.rda` Sarah linked) labels SynthETIC's own
  example portfolio (3,624 claims), not SPLICE Complexity 5 (3,663 claims), so it cannot
  be joined to these files.
- `claim_size` is in constant (time-0) money. Paid cash is `payment_inflated`, which
  accumulates to `cumpaid` in the incurred table. In Complexity 5 total inflated payments are
  1.83 times total `claim_size` (3.7 times on average per claim, because small claims carry
  the most superimposed inflation). Use `payment_inflated` for reserving.

To regenerate (requires R with SynthETIC and SPLICE ≥ 1.1.0):

```bash
Rscript scripts/regenerate_splice_cov.R
```
