# Clustering for Reserving — MLR Working Party

A research project of the IFoA GI **Machine Learning in Reserving (MLR) Working Party**,
proposed by Luca Alberici, exploring **unsupervised clustering (K-means and beyond)
as a feature-engineering / segmentation step ahead of reserving**.

## Goal

Investigate whether clustering claims or portfolios by similar development
characteristics can:

- support meaningful segmentation *prior to* reserving, and/or
- improve the interpretation of reserve analyses.

This extends the WP's existing Foundations material with a practical ML angle.

## Team

- Sarah MacDonnell (LCP) — WP Chair
- Luca Alberici (City St George's) — proposal lead
- Nawfal Khodabacchas — reserving background
- Lina Palacios — WP member

## Project layout

```
.
├── data/
│   ├── raw/          # original, untouched source data (never edit in place)
│   └── processed/    # cleaned / derived datasets used by notebooks & code
├── notebooks/        # exploratory analysis, one notebook per stage
├── src/
│   ├── data/          # loading & cleaning code
│   ├── features/      # feature engineering, incl. the clustering step
│   ├── models/         # reserving models that consume clustering output
│   └── utils/          # shared helpers
├── reports/
│   ├── figures/       # exported charts/plots
│   └── summary.md     # write-ups to share back with the wider WP
├── docs/              # background material (incl. WP navigation guide)
└── tests/             # unit tests for src/
```

Rationale: `data/raw` stays immutable (candidate sources: SPLICE simulated data,
Canadian regulator data) so any cleaning step is reproducible; `src/features/`
isolates the clustering logic so it can be swapped or extended independently of
the reserving models in `src/models/`; `notebooks/` is for exploration only —
anything reusable should graduate into `src/`.

## Getting started

```bash
git clone <repo-url>.git
cd mlr-clustering-reserving
pip install -r requirements.txt
```

See `CONTRIBUTING.md` for how to make changes and share them with the group —
written for anyone new to Git.
