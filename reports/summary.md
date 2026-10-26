# Project summary

_Living document — update after each working session so the wider WP can follow
progress without digging through notebooks._

## Status
- [x] Kick-off call held (Sarah, Luca, Nawfal, Lina)
- [x] Data source(s) confirmed — SPLICE Complexity 5 (standard + published covariate portfolio with recovered labels), Complexities 1–4
- [x] Phase 1 — data understanding (`reports/phase_1_summary.md`)
- [x] Phase 2 — hierarchical vs K-means on the ex-post baseline (`notebooks/02_clustering_experiments.ipynb`)
- [x] Phase 2b — valuation-date features, reserving backtest, drift correction and out-of-time test (`reports/phase_2b_valuation_date.md`)
- [x] Theoretical background section (`article/theory.tex`)
- [x] Full draft of the paper: methodology, results, conclusions, appendix (`article/main.pdf`)
- [x] Other uses of groups and robustness on SPLICE Complexities 1–5 (`notebooks/04_group_uses.ipynb`)
- [ ] Work-in-progress presentation at the WP meeting (date and length to be confirmed by Sarah)
- [ ] Findings written up and posted to VLE "Potential Projects and Ideas"

## Latest findings
- **Ex-post (Phase 2).**
  - There is one natural split: small, quickly settled claims versus the rest.
  - K-means beats Ward on every diagnostic and on stability (bootstrap ARI
    0.94–0.96 against 0.4–0.5).
  - Finer partitions depend on how the correlated complexity variables are
    weighted.
- **Covariate data.** We use the published SPLICE `_cov` portfolio with the
  covariate labels recovered via the generator. The published files reproduce
  exactly with the CRAN package versions; our earlier claim that they did not
  was due to using the development version of SynthETIC. The `.rda` Sarah
  linked belongs to a different portfolio.
- **Valuation-date features.** All of Lina's features can be reconstructed
  from SPLICE, cut off at V. Monetary features are made scale-free to remove
  the inflation drift.
- **Triangle segmentation.** Segmenting a paid Chain Ladder by
  notification-time clusters gives no robust gain over random groups.
  Calendar effects dominate the error.
- **Case-estimate adjustment.** Factors applied out of time cut the RBNS error
  from 36–38% to about 4–9%. Most of the gain comes from a single factor;
  clusters add about 2 points in the standard portfolio and nothing in the
  covariate portfolio, and simple bands do as well.
- **Other uses of groups (Complexities 1–5).**
  - Splitting the triangle never beats random groups, in any scenario.
  - Large claims apart is best with an inflation shock (C4), but a simple rule
    works as well as the cluster.
  - Groups help consistently only inside a GLM with calendar and speed trends.
  - As a monitor, groups detect the speed-up within groups in C5, with no false
    alarm in C1.
