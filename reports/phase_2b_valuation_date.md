# Phase 2b — Valuation-date prototype and covariate data

_Work-in-progress note for the MLR WP (Luca, Lina, Nawfal, Sarah). Prototype
results on simulated data; numbers will move as the design is agreed._

_Revised 22 Oct 2026: inflation drift corrected, out-of-time test added. Some
earlier figures changed; see §6._

_Revised 26 Oct 2026: the covariate portfolio is now the **published** SPLICE
`_cov` portfolio, with covariate labels recovered using the released package
versions. Our earlier statement that the published files "do not reproduce" was
wrong: it came from using the development version of SynthETIC (see §2). All
covariate-portfolio figures below have been recomputed._

Code: `src/features/valuation.py`, `src/models/chain_ladder.py`,
`src/models/case_estimate_factors.py`, `scripts/run_valuation_experiment.py`,
`scripts/run_open_claims_oot.py`, `notebooks/03_reserving_integration.ipynb`,
`scripts/export_splice_cov_labels.R`. Tables in `reports/tables/`, figures in
`reports/figures/`. Ex-post comparison of hierarchical clustering and K-means:
`notebooks/02_clustering_experiments.ipynb`. Theory:
`article/theory.tex`.

## 1. Summary

1. **Covariate data.**
   - `SynthETIC::test_covariates_dataset` cannot be joined to the SPLICE `_cov`
     files: it labels SynthETIC's own example portfolio (3,624 claims), not
     SPLICE Complexity 5 (3,663 claims).
   - The published `_cov` files reproduce exactly with the released packages
     (SynthETIC 1.1.1, SPLICE 1.1.2 from CRAN).
   - `SPLICE::generate_data()` returns the covariate labels, so we exported them
     and attached them to the published files. We now use the same data as the
     rest of the WP, with legal representation, injury severity and claimant age
     for every claim. No LLM correction is needed.
2. **Valuation-date features.** Every feature on Lina's list can be
   reconstructed from SPLICE with transactions cut at V. Tests check that
   deleting all data after V leaves the features unchanged, and that deleting
   data after V1 leaves the out-of-time estimates unchanged.
3. **Inflation drift corrected.** Nominal initial case estimates double over
   the period, which moved later claims into higher clusters. We now express
   them relative to their notification period. The largest shift in cluster
   mix between periods 1–20 and 21–40 falls from 11.5 to 3.8 points, and
   bootstrap stability rises from 0.70 to 0.96.
4. **Segmenting the paid Chain Ladder does not help in a robust way.**
   Notification-time clusters change the RBNS error by a few points, inside the
   range of random groups of the same sizes. Effects common to all segments
   dominate the error: the trend in settlement speed, superimposed inflation
   and the tail.
5. **Adjusting case estimates works much better.**
   - Factors fitted 8 quarters earlier and applied out of time cut the RBNS
     error from 36–38% (raw case estimates) to about 4–9%. Paid CL errs by 15–27%
     on average.
   - Most of the gain comes from a single portfolio-wide factor (7–8% error).
   - Open-claim clusters improve on it by about 2 points in the standard
     portfolio, but not at all in the covariate portfolio. Simple bands of "case
     estimate / initial estimate" do as well or better.
6. **Ex-post comparison (notebook 02).** The data contain one natural split:
   small, quickly settled claims versus the rest. K-means is preferable to
   Ward: it scores better on every diagnostic and is far more stable (bootstrap
   ARI 0.94–0.96 against 0.4–0.5). Beyond two clusters, the partition depends
   on how the three correlated "complexity" variables are weighted.
7. **Other uses of groups, on all five SPLICE scenarios (§9).**
   - Splitting the triangle fails in every scenario.
   - Treating large claims apart is the best method when there is an
     inflation shock (C4: 9% against 24% for CL), but a simple threshold rule
     works as well as the cluster.
   - Groups help consistently only inside a GLM that models calendar and speed
     trends, and even that GLM does not beat case-estimate factors.
   - As a monitoring tool, the groups show that settlement speeds up within
     every group in C5, with no false alarm in C1.

## 2. Covariate data (Sarah's suggestion)

| | Claims | Joins to SPLICE C5? |
|---|---|---|
| `SynthETIC::test_covariates_dataset` | 3,624 | No. Its per-period counts match `SynthETIC::test_claim_dataset` exactly. |
| Published SPLICE `complexity_5/*_cov.csv` | 3,663 | No labels are published. |
| `complexity_5/covariates_5_cov.csv` (this repo) | 3,663 | Yes: labels of the published `_cov` files, keyed by `claim_no`, exported with `scripts/export_splice_cov_labels.R`. |

**Reproducibility** (R 4.3.3, seed 42, SPLICE generation script):

| Package versions | `_cov` tables vs published files | Covariate labels |
|---|---|---|
| SynthETIC 1.1.1 + SPLICE 1.1.2 (CRAN) | **identical** (to 1e-15), also for two calls in one session | — |
| SynthETIC 1.1.2 (GitHub, Aug 2026 fix, not on CRAN) + SPLICE 1.1.2 | same occurrence times and claim sizes; **different** delays, payments and case estimates | identical to CRAN |

- **Our earlier statement was wrong.** We said the published `_cov` files "do not
  reproduce with current package versions". In fact they reproduce with the
  released versions. We had unknowingly installed the development version of
  SynthETIC, which changes the random-number stream after the covariate step.
- **Nigel's observation:** for the same seed, the covariate and no-covariate
  portfolios differ in everything drawn after the covariate step. This is
  expected; the two are not mixed.
- **Gráinne's tutorial:** its problem 1 (the seed lost with covariates) did not
  appear in our test with the CRAN versions. It may depend on the R version;
  to be compared with her.

**The three covariates.** They are assigned at occurrence and do not change
afterwards, so in this simulation they are available at notification. In
practice, legal representation and injury severity can emerge or change after
reporting. They act through claim size, and in Complexity 5 claim size then
drives both delays.

| Injury severity | Claims | Median size | Median settlement delay (q) |
|---|---|---|---|
| 1 | 1,902 | 33.8k | 5.3 |
| 2 | 1,108 | 74.7k | 7.3 |
| 3 | 370 | 169k | 10.4 |
| 4 | 190 | 282k | 11.5 |
| 5 | 43 | 514k | 15.2 |
| 6 | 50 | 28.6k | 5.8 |

## 3. Data facts that matter for reserving

- `claim_size` is in **constant (time-0) money**. The cash actually paid
  (`payment_inflated`, which also accumulates to `cumpaid` in the incurred
  table) is larger in Complexity 5: **1.83 times** in total, and 3.7 times on average per claim
  (small claims carry the most superimposed inflation). All reserving
  figures use inflated payments.
- At **V = 40** (standard portfolio):
  - 3,462 claims are reported, of which 821 are open; 201 are IBNR.
  - Paid to date is 645m.
  - Actual future payments on reported claims (RBNS) are 386.5m, and on IBNR
    claims 89.5m.
  - Outstanding case estimates are 252.5m, about **35% below** the RBNS
    run-off. The shortfall is stable at 34–45% across valuation dates, which is
    why a single correction factor already works well (§7).

## 4. Experiment design

- **Valuation dates.** V = 20, 24, 28, 32, 36 and 40.
- **Population.** Claims reported by V. IBNR is a separate problem.
- **Triangle.** Inflated paid, with rows by **notification** period.
- **CL rule.** Factors estimated from fewer than 5 rows are set to 1, for every
  method. Without the rule, a single late payment in the oldest row produced
  f₃₄ = 1.43 at V = 36 and inflated the whole reserve by about 40%.
- **Triangle segment labels use features at notification**, so a label means
  the same thing in every cohort:
  - notification delay;
  - initial case estimate relative to the median of its notification period
    (`initial_ce_rel`);
  - plus the three covariates in the covariate portfolio.

  Clusters are refitted at each V using only the claims reported by then.
- **Open-claim groups** use valuation-date features in scale-free form:
  - age since notification and notification delay;
  - `initial_ce_rel`;
  - paid to date / initial estimate;
  - current case estimate / initial estimate;
  - number of payments and time since the last payment;
  - number and size of revisions.
- **Comparators.**
  - Unsegmented CL and raw case estimates.
  - Equal-count bands of a single variable.
  - Random groups with the same sizes as the clusters (a placebo, 30 draws).
  - In the covariate portfolio, the true injury-severity groups {1,6}, {2} and
    {3–5}.

## 5. Results — segmented Chain Ladder

Mean absolute total RBNS error over the six valuation dates:

| Method | Standard | Covariates |
|---|---|---|
| Unsegmented CL | 31.8% | 21.2% |
| K-means, notification features, k = 3 | 33.6% | 22.7% |
| K-means, notification features, k = 4 | 30.6% | 21.4% |
| Ward, notification features, k = 3 | 30.5% | 20.7% |
| K-means, notification + covariates, k = 3 | – | 23.0% |
| True injury-severity groups | – | 20.6% |
| Bands of relative initial case estimate, k = 3 | 32.1% | 21.6% |
| Random groups (placebo), k = 3 | 32.2% | 21.4% |
| Case estimates | 37.4% | 38.2% |

At V = 40:

| Method | Standard | Covariates |
|---|---|---|
| Unsegmented CL | +35.0% | +28.3% |
| K-means, notification features, k = 3 | +34.0% | +30.8% |
| K-means, notification + covariates, k = 3 | – | +22.8% |
| True injury-severity groups | – | +22.7% |
| Random groups (5th–95th percentile) | +33.9% to +37.1% | +27.1% to +31.6% |

Interpretation:
- **The error is driven by effects common to all segments.** Every method moves
  together over time: every segmentation underestimates by 45–59% at V = 20 and
  overestimates from V = 32 onwards (up to 80% at V = 36 in the standard
  portfolio). Segmenting by claim type cannot correct calendar-period
  effects.
- **There is no robust gain from segmentation.** Most methods lie within a few
  points of unsegmented CL and of the random groups. The best result changes
  with k and with the feature version.
- **Covariates help at some dates, not on average.** At V = 40, clusters with
  covariates and the true severity groups (+22.8%, +22.7%) lie below the random
  range. Over all dates, however, the severity groups are only 0.6 points better
  than unsegmented CL (20.6% against 21.2%), and clusters with covariates are
  worse (23.0%). A gain at a single date is not evidence of a useful
  segmentation.
- **Correction to earlier versions.** The first draft reported a 5-point gain
  for notification clusters at V = 40 in the covariate portfolio, and the
  version of 22 Oct a "weak but consistent" gain from covariates. Both used the
  regenerated (development-version) covariate portfolio and neither holds on
  the published data.

## 6. Results — open claims at V = 40 (descriptive)

K-means (k = 4) on scale-free valuation-date features of the 821 open claims.
Payments after V are used only to describe the clusters.

| Cluster (standard) | Open claims | Median age since notification (q) | Median paid to date | Actual future / case estimate |
|---|---|---|---|---|
| 0 — just reported, nothing paid | 264 | 1.9 | 0 | 2.65 |
| 1 — mid-age | 308 | 7.9 | 45k | 1.48 |
| 2 — old, largely paid, small residual estimate | 41 | 14.2 | 337k | 0.97 |
| 3 — old, large outstanding estimate | 208 | 12.5 | 48k | 1.01 |

Share of the variation in log future payments explained, in-sample:

| | Standard | Covariates |
|---|---|---|
| Case estimate alone | 0.18 | 0.27 |
| Clusters alone | 0.32 | 0.01 |
| Clusters + case estimate within cluster | 0.45 | 0.39 |

**Correction.** The first draft showed a cluster with an actual-to-estimate
ratio of 9.9 (181 claims). It was formed on nominal amounts, and the script
still reports it as a sensitivity (`key_numbers.json`). With scale-free features the
ratios range from 1.0 to 2.65, and the pattern is mainly about **claim age**:
recently reported claims are the most under-reserved, while old claims are
reserved about right.

## 7. Results — out-of-time test of case-estimate factors

**Design.** At V0 we group the open claims and compute, for each group, a
factor
`(paid in (V0, V1] + case estimate at V1) / case estimate at V0`, using only
data up to V1 = V0 + 8. At V1 the open claims are assigned with the rule fitted
at V0 (same scaler and centroids, same band edges). The reserve is estimated as
factor × case estimate, and scored against the actual run-off after V1. The
factor understates full development a little, because case estimates at V1 are
themselves short. This affects every grouping equally, including the single
factor.

Total RBNS error (%), V1 = 24 … 40:

| Method | Standard: mean \|error\| | Covariates: mean \|error\| |
|---|---|---|
| Raw case estimates | 35.9 | 37.7 |
| Unsegmented paid CL | 26.7 | 15.4 |
| Single factor (no groups) | 7.4 | 7.9 |
| Bands of claim age, k = 4 | 6.3 | **7.8** |
| Bands of case estimate / initial, k = 4 | **3.5** | 8.6 |
| K-means open-claim clusters, k = 3 | 4.9 | 8.3 |
| K-means open-claim clusters, k = 4 | 5.2 | 8.0 |
| K-means open-claim clusters, k = 6 | 5.7 | **7.8** |
| K-means + covariates, k = 4 | – | 8.2 |

Interpretation:
- **Correcting case estimates is the big win.** Even one portfolio-wide factor
  is far better than raw case estimates or paid CL.
- **Grouping adds little.** In the standard portfolio, clusters (k = 3–4) add
  2.2–2.5 points over the single factor, but bands of case estimate / initial
  estimate do better (3.5%). In the covariate portfolio no grouping improves
  on the single factor (7.8–8.6% against 7.9%), with or without the covariates.
- **At claim level, groups do not help.** The median absolute log error per
  claim is 0.52–0.55 for the single factor and 0.51–0.68 for the groupings.
  Group factors improve the total, not individual claim estimates.
- **The errors drift negative at later dates** (−2% to −15% at V1 = 36–40).
  This is the expected understatement of the factor, and it is common to all
  groupings.

## 8. Stability

- **Bootstrap.** Mean adjusted Rand index of K-means on notification features
  (30 resamples) is 0.96 (k = 3) in both portfolios, and 0.95 (standard) and
  0.94 (covariates) for k = 4. Before
  the drift fix it was 0.70 and 0.86.
- **Drift over time.** The largest change in cluster share between notification
  periods 1–20 and 21–40 is 3.8 points (standard) and 3.6 points (covariates).
  With nominal amounts it was 11.5 and 11.8 points. The fix also removes any
  genuine change in severity mix between periods, which is a deliberate
  trade-off.

## 9. Other uses of groups, on all five SPLICE scenarios

_Added 22 Oct 2026. Code: `src/models/group_uses.py`,
`scripts/run_group_uses.py`, `notebooks/04_group_uses.ipynb`. Standard
portfolios, valuation dates V = 24, 28, 32, 36 and 40. Groups are K-means
clusters on notification features (k = 3), refitted at each V._

The five scenarios:

| Scenario | Design |
|---|---|
| C1 | simple, homogeneous, no inflation |
| C2 | size-dependent delays, 2% p.a. inflation |
| C3 | settlement speeds up over time |
| C4 | inflation shock at time 30 |
| C5 | full complexity (the main study) |

Mean absolute RBNS error (%), V = 24–40:

| Method | C1 | C2 | C3 | C4 | C5 | Mean |
|---|---|---|---|---|---|---|
| Raw case estimates | 40.2 | 43.5 | 42.4 | 47.4 | 35.9 | 41.9 |
| Paid CL, unsegmented | 15.0 | 18.6 | 21.7 | 24.5 | 26.7 | 21.3 |
| Paid CL by clusters | 16.9 | 19.4 | 21.1 | 24.1 | 28.8 | 22.1 |
| Paid CL by random groups | 15.1 | 18.8 | 21.7 | 24.0 | 27.2 | 21.4 |
| Case-estimate factor, single | 9.3 | 10.2 | 8.6 | 12.3 | 7.4 | 9.6 |
| Case-estimate factors, bands | 8.5 | 10.7 | 6.8 | 15.5 | 3.5 | **9.0** |
| Case-estimate factors, clusters | 8.7 | 10.6 | 8.2 | 14.2 | 5.2 | 9.4 |
| Large claims apart (cluster) | 10.6 | 8.8 | 10.7 | 9.4 | 14.3 | 10.8 |
| Large claims apart (rule, same size) | 9.2 | 11.2 | 10.2 | 9.1 | 13.4 | 10.6 |
| GLM, calendar trend | 17.4 | 19.4 | 20.2 | 29.7 | 21.1 | 21.6 |
| GLM, calendar trend, by clusters | 17.7 | 19.4 | 21.3 | 27.2 | 23.0 | 21.7 |
| GLM, calendar + speed trend | 20.0 | 25.3 | 25.5 | 33.9 | 14.5 | 23.8 |
| GLM, calendar + speed trend, by clusters | 19.6 | 23.8 | 24.4 | 29.1 | 12.5 | 21.9 |

**Splitting the triangle (Experiment 1) fails in every scenario,** including
C1 and C2, where there is no calendar-period trend to blame. Clusters are never
better than random groups. The negative result is robust, not a feature of
Complexity 5.

**Case-estimate factors (Experiment 2) are the best approach in C1, C3 and
C5,** at 7–12% error with a single factor; in C2 and C4 the large-claims split
below is better. Groups add
nothing on average across scenarios (9.4% against 9.6%), and the simple bands
are as good as clusters.

**Use 4 — large claims apart.** Chain ladder on the other claims, with the
large group reserved as case estimate × an out-of-time factor.
- This is the best method in **C2 and C4** (8.8% and 9.1–9.4%). In C4 it does
  much better than either pure approach: CL 24.5%, single factor 12.3%.
- It reduces the CL error in every scenario, by 29% (C1) to 62% (C4).
- A simple threshold rule on the relative initial estimate does as well as the
  cluster.

**Use 5 — groups inside a model with calendar effects.** We fit a quasi-Poisson
GLM for incremental paid per notified claim, with development effects, a
linear calendar trend and optionally a trend in the speed of development.
- The calendar trend helps only where one exists: in C5 it cuts the error from
  26.7% to 21.1%.
- The speed trend helps C5 further (14.5%), but hurts C1–C4, where there is no
  such trend to find.
- **Adding cluster-specific development patterns helps consistently inside the
  speed-trend model** (mean 21.9% against 23.8%; C4 29.1% against 33.9%; C5
  12.5% against 14.5%). This is the one setting where clusters add value
  systematically: once the model handles the change over time, separating
  claim types refines it.
- Even so, these GLMs do not beat the case-estimate factors in any scenario.

**Use 3 — monitoring.** At V = 40 we tracked, by notification cohort and
cluster, the cluster mix and the share of claims settled within 8 quarters.
This is observable at V for cohorts up to period 32.

| Scenario | Speed-up within groups (Spearman, p-value) | Mix change |
|---|---|---|
| C1 | none significant (ρ 0.11–0.24, p ≥ 0.18) | none |
| C3 | weak in all three groups (ρ 0.26–0.35, p 0.06–0.16) | none |
| C5 | clear in two groups (ρ 0.51, p = 0.004; ρ 0.42, p = 0.018) | large-claim cluster growing (ρ 0.60, p < 0.001) |

- The monitor **gives no false alarm** in C1.
- In C5 it shows that settlement is speeding up **within** groups, not only
  through a change in mix. This explains why splitting the triangle cannot
  help, and it points to a method that models the trend.
- In C3, where the speed-up is the designed feature, the signal is present but
  weak with 30 cohorts. Monitoring at this granularity has limited power.

**Other checks made along the way.**
- **Case estimates are 35–49% short at V = 40 in every scenario,** including C1,
  which has no inflation. The shortfall is therefore a feature of how SPLICE
  generates case estimates, not an inflation effect.
- **The nominal initial case estimate is stable in C1,** drifts slightly in C2
  (2% p.a.), jumps after period 30 in C4 and doubles in C5. This confirms that
  the drift corrected in §8 is inflation.

**What this means for the project.** Groups are useful for **understanding**
the portfolio:
- which claims are under-reserved;
- whether the mix or the speed is changing;
- which claims to treat apart.

They are also useful as a **refinement inside a model** that already handles
the calendar effects. They are **not** useful for splitting a chain-ladder
triangle, and in no scenario do they beat a simple case-estimate correction or
a simple rule.

## 10. Proposed next steps

1. Agree the evaluation design with the group:
   - notification-period RBNS triangles;
   - IBNR treated separately;
   - the rule on minimum rows;
   - random-group placebo;
   - out-of-time case-estimate test.
2. Improve the case-estimate factor:
   - chain it, or use a longer window, to remove the understatement;
   - compare with an incurred Chain Ladder.
3. Combine the two best ideas: case-estimate factors for open claims inside a
   model with a calendar trend, and the large-claims split for portfolios with
   inflation shocks.
4. Add model-based clustering (Gaussian mixtures) to notebook 02, as the
   theory section anticipates.
5. Compare later with the WP's NN models on the same V = 40 split.
