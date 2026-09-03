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


├── data/
│   ├── raw/          # original, untouched source data (never edit in place)
│   └── processed/    # cleaned / derived datasets used by notebooks & code
├── notebooks/         # exploratory analysis — the "dev" space, one notebook per stage
├── src/                # reusable code, once something from a notebook is proven out
│   ├── data/           # loading & cleaning code
│   ├── features/       # feature engineering, incl. the clustering step
│   ├── models/         # reserving models that consume clustering output
│   └── utils/          # shared helpers
├── reports/
│   ├── figures/        # exported charts/plots
│   └── summary.md      # living write-up to share back with the wider WP
├── docs/               # background material (incl. WP navigation guide)
└── tests/              # unit tests for src/


**How it fits together:** 
raw data stays untouched in `data/raw/`, gets cleaned into
`data/processed/`, gets explored in `notebooks/`. 
Anything from a notebook worth reusing — like the clustering function — "graduates" into `src/`, so it can be imported anywhere instead of copy-pasted between notebooks. `reports/` and `docs/`
are what we actually share outward with the rest of the working party.

## Getting started

```bash
git clone https://github.com/Linchenpal/mlr-clustering-reserving.git
cd mlr-clustering-reserving
pip install -r requirements.txt
```

See `CONTRIBUTING.md` for how to make changes and share them with the group —
written for anyone new to Git.
