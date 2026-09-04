# Phase 1 — SPLICE Data Understanding and Exploration

## 1. Purpose

The purpose of Phase 1 was to establish a reproducible dataset, understand its
structure, validate the relationships between its tables, and determine an
appropriate starting point for clustering reserving-related claim profiles.

This phase provides the data foundation for the clustering experiments in
Phase 2.

## 2. Data source

The data comes from the
[SPLICE project](https://github.com/agi-lab/SPLICE), which generates synthetic
individual-claim reserving data.

We selected the **Complexity 5** scenario because it contains the most complex
dependency structure among the five published SPLICE scenarios. This makes it
a useful starting point for investigating whether clustering can identify
different types of claim-development behaviour.

The files are stored in:

```text
data/raw/splice/complexity_5/
```

## 3. Structure of the data

The selected scenario contains three related tables:

| File | Unit of observation | Description |
|---|---|---|
| `claim_5.csv` | One row per claim | Claim characteristics and final outcomes |
| `payment_5.csv` | One row per payment | Timing and value of individual payments |
| `incurred_5.csv` | One row per transaction | Development of incurred values, cumulative payments, and case estimates |

The portfolio contains:

- **3,663 claims**
- **19,322 payment transactions**
- **31,554 incurred transactions**

The common key `claim_no` connects the claim table with the payment and
incurred transaction tables.

## 4. Data validation

Before performing exploratory analysis, we checked the consistency of the
three tables.

The validation confirmed that:

- every payment transaction belongs to a known claim;
- every incurred transaction belongs to a known claim;
- the observed number of payment rows per claim agrees with `no_payment` in
  the claim table;
- no relational inconsistencies were identified.

These checks indicate that the three files form a consistent relational
dataset and can be used together in later phases.

## 5. Initial claim-level exploration

The first exploratory analysis focused on four variables from the claim table:

| Variable | Interpretation |
|---|---|
| `claim_size` | Ultimate claim severity |
| `notidel` | Delay between occurrence and notification |
| `setldel` | Time taken to settle the claim |
| `no_payment` | Number of payments made for the claim |

These variables provide an interpretable initial description of claim size,
reporting behaviour, settlement speed, and payment complexity.

### Distributional findings

The variables are right-skewed, particularly claim size and settlement delay.
A small number of claims are substantially larger or develop for much longer
than the typical claim.

Log transformations were investigated because they:

- reduce the influence of extreme values;
- make distances between observations more meaningful;
- prevent the largest-scale variable from dominating the clustering result.

The extreme observations were retained because they are valid simulated claims
and may represent actuarially meaningful high-severity or long-development
profiles.

### Relationships between variables

The Spearman correlation analysis identified several important relationships:

- claim size and settlement delay have a correlation of approximately **0.68**;
- claim size and number of payments have a correlation of approximately **0.68**;
- settlement delay and number of payments have a correlation of approximately
  **0.54**;
- notification delay has weaker negative relationships with the other
  variables.

Larger claims therefore tend to remain open longer and involve more payments.
Claim size, settlement delay, and payment count may partially represent the
same underlying concept of **claim complexity**.

This matters because using several correlated variables may give claim
complexity too much weight in a distance-based clustering model. Phase 2 will
retain the variables initially and then use sensitivity analysis to assess
their influence.

## 6. Choice of clustering unit

Two possible units of analysis were considered:

1. individual claims;
2. aggregated occurrence periods.

An occurrence-period summary was produced using claim frequency and median or
mean claim characteristics. However, the dataset contains only 40 occurrence
periods, compared with 3,663 individual claims. The period-level plots also did
not show clear and persistent regimes.

Individual claims were therefore selected as the primary clustering unit
because they:

- provide a sufficiently large sample for clustering;
- preserve variation between claims;
- allow the analysis to identify distinct claim-development profiles;
- avoid hiding heterogeneous claims inside period-level averages.

## 7. Why the transaction tables are not yet clustering inputs

The payment and incurred tables contain multiple observations for each claim.
They cannot be passed directly into a model whose unit of analysis is one row
per claim.

Phase 1 therefore used the claim table as a transparent baseline. The payment
and incurred tables were validated but have not yet been converted into
clustering features.

Later work can aggregate the transaction histories into one row per claim and
derive features such as:

- time to first payment;
- proportion paid at different development ages;
- average and maximum payment size;
- payment-development speed;
- number and magnitude of incurred revisions;
- case-estimate volatility;
- reopening or unusual transaction behaviour.

These features would allow the project to move from clustering final claim
outcomes towards clustering development patterns.

## 8. Important limitation

The baseline features include ultimate claim size, final settlement delay, and
final number of payments. These quantities are known only after a claim has
developed or settled.

The initial model is consequently an **ex-post segmentation exercise**: it can
describe different completed claim profiles, but it cannot yet assign a new
claim to a cluster at notification.

A later reserving application should distinguish between:

- features available at the valuation date; and
- future outcomes that the analysis is intended to understand or predict.

## 9. Covariate-adjusted SPLICE data

The Complexity 5 folder also contains files ending in `_cov`. These represent a
separate simulated portfolio generated with SynthETIC's default covariate-based
claim-size adjustments. They are not supplementary rows that should be joined
to the non-covariate files.

The recommended project structure is:

- use the standard Complexity 5 portfolio for the baseline experiment;
- use the `_cov` portfolio later as a robustness or extension experiment;
- do not mix standard and `_cov` tables within the same portfolio.

The published `_cov` CSV files do not expose the underlying assigned covariate
labels. If the team wants to compare clusters against the true simulated risk
factors, the portfolio would need to be regenerated in R and the covariate
assignment data exported separately.

## 10. Phase 1 conclusion

Phase 1 established that:

- the SPLICE Complexity 5 data is internally consistent;
- individual claims are the most appropriate initial clustering unit;
- the claim-level variables require transformation and standardisation;
- correlated measures of severity and development complexity require
  sensitivity testing;
- transaction-level development features are an important later extension;
- the `_cov` dataset should be treated as a separate experiment.

The detailed code and outputs are available in:

```text
notebooks/01_data_exploration.ipynb
```

## 11. Phase 2 plan

Phase 2 will:

1. construct the claim-level feature matrix;
2. transform skewed variables;
3. standardise the features before calculating distances;
4. apply hierarchical clustering and inspect the dendrogram;
5. compare candidate cluster solutions using quantitative diagnostics;
6. cross-check the results with K-means;
7. assess cluster stability and actuarial interpretability;
8. document the effect of correlated features through sensitivity analysis.

The Phase 2 implementation will be developed in:

```text
notebooks/02_clustering_experiments.ipynb
```
