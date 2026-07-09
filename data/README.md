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
