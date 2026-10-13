# Phase 2 — first exploratory run

This is an exploratory starting point for discussion with Nawfal, Luca and Sarah.
It does not establish a final segmentation or improved reserving performance.
Source: repository main at 3e645ed88c34f702d85d37732688160058da6def.

## Completed

- Validated 3,663 unique claims and the four baseline input features.
- Applied log(1+x) followed by standardisation, retaining all claims.
- Compared Ward hierarchical clustering and K-means for 2–8 groups.
- Produced a dendrogram, diagnostics, original-unit profiles and claim assignments.
- Checked feature sensitivity, upper-tail influence and ten 80% subsamples.
- Executed all five notebook code cells successfully and validated notebook structure.

## Initial findings

Among the tested counts, two groups have the highest sampled silhouette for
both methods: 0.346 for Ward and 0.406 for K-means. These geometric measures
do not establish the existence of true groups or actuarial usefulness.
Ward and K-means at k=2 agree only partially (adjusted Rand index 0.585).

The working Ward candidate has these descriptive profiles:

| Group | Claims | Median ultimate size | Median settlement delay (quarters) | Median payment count | Share of ultimate cost |
|---|---:|---:|---:|---:|---:|
| 1 | 2,325 | 147,167 | 11.70 | 5 | 93.05% |
| 2 | 1,338 | 13,852 | 2.30 | 3 | 6.95% |

Both groups appear in all 40 occurrence periods, with a minimum of 21 claims
in a period/group cell. This does not establish sufficient development support
or credibility for reserving.

The partition is sensitive to modelling choices. Relative to the baseline,
ARI is 0.583 without payment count, 0.408 without settlement delay, and 0.432
after excluding the highest 1% of claim costs as a diagnostic. Across ten 80%
subsamples, ARI averages 0.365 (range 0.222–0.655). These results argue against
accepting the Ward labels as a robust final solution yet.

## Next work

1. Compare K-means sampling and initialisation stability, and neighbouring k
   profiles, before selecting an algorithm or cluster count.
2. Investigate alternative linkage and feature weighting; explain which
   observations change groups and whether the differences matter actuarially.
3. Agree with the team what volume and development support a reserving group
   needs. Test downstream reserving separately with valuation-date information.
4. Coordinate with Nawfal's existing work before combining implementations.

## Reproduction and files

Open `notebooks/02_clustering_experiments.ipynb` and run all cells from the root
or notebooks folder. Alternatively, `python scripts/build_phase2.py` rebuilds
and executes it. Install `requirements.txt` first. The executed notebook records
library versions. Tables and figures are in `reports/phase_2/`.

Baseline scope is ex-post: ultimate cost, final settlement delay and final
payment count are unavailable for open claims. The `_cov` portfolio and
transaction-history features remain deferred.
