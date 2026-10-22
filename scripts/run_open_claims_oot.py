"""Out-of-time test of open-claim clusters (Phase 2b, step 2).

Fit groups and case-estimate factors at V0 using data up to V1 = V0 + H,
apply at V1, score against the actual run-off after V1.

Run from the repo root:
    python scripts/run_open_claims_oot.py
Outputs: reports/tables/oot_open_claims.csv, reports/tables/oot_summary.csv,
         reports/figures/oot_open_claims_*.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.splice import load_splice  # noqa: E402
from src.models.case_estimate_factors import BandGrouper, KMeansGrouper, SingleGroup, run_oot  # noqa: E402
from src.models.chain_ladder import actual_future_by_row, reserve_errors, segmented_reserve  # noqa: E402

TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "reports" / "figures"

H = 8  # quarters between fitting (V0) and applying (V1)
V1_DATES = [24, 28, 32, 36, 40]
OPEN_COLS = ["notidel", "age_since_notification", "initial_ce_rel", "paid_over_initial_ce",
             "ce_over_initial_ce", "n_payments_to_date", "time_since_last_payment",
             "n_revisions_to_date", "max_abs_log_revision"]
COV_COLS = ["injury_severity", "legal_rep_no", "claimant_age_band"]
PORTFOLIOS = {"standard": ("complexity_5", ""), "covariates": ("complexity_5_cov_regen", "_cov")}


def methods(has_cov: bool) -> dict:
    m = {
        "Single factor (no groups)": lambda: SingleGroup(),
        "Bands of claim age (k=4)": lambda: BandGrouper("age_since_notification", 4),
        "Bands of case estimate / initial (k=4)": lambda: BandGrouper("ce_over_initial_ce", 4),
        "K-means open-claim clusters (k=3)": lambda: KMeansGrouper(OPEN_COLS, 3),
        "K-means open-claim clusters (k=4)": lambda: KMeansGrouper(OPEN_COLS, 4),
        "K-means open-claim clusters (k=6)": lambda: KMeansGrouper(OPEN_COLS, 6),
    }
    if has_cov:
        m["K-means open-claim clusters + covariates (k=4)"] = lambda: KMeansGrouper(OPEN_COLS + COV_COLS, 4)
    return m


def main():
    rows = []
    for name, (folder, suffix) in PORTFOLIOS.items():
        p = load_splice(folder, suffix)
        for V1 in V1_DATES:
            V0 = V1 - H
            for mname, make in methods(p.covariates is not None).items():
                r = run_oot(p, V0, V1, make())
                rows.append({"portfolio": name, "method": mname, **r})
            # reference points at V1 that need no fitting at V0
            r = rows[-1]
            act = actual_future_by_row(p, V1)
            rows.append({"portfolio": name, "method": "Raw case estimates", "V0": V0, "V1": V1,
                         "estimate": np.nan, "actual": r["actual"], "total_error_pct": np.nan})
            cl = reserve_errors(segmented_reserve(p, V1), act)
            rows.append({"portfolio": name, "method": "Unsegmented paid CL (all reported claims)", "V0": V0, "V1": V1,
                         "estimate": cl["estimate"], "actual": cl["actual"], "total_error_pct": cl["total_error_pct"]})
    df = pd.DataFrame(rows)

    # Raw case estimates = single-factor estimate with factor 1: recompute directly
    for name, (folder, suffix) in PORTFOLIOS.items():
        p = load_splice(folder, suffix)
        from src.features.valuation import features_at_valuation
        for V1 in V1_DATES:
            ce = features_at_valuation(p, V1)["case_estimate"].sum()
            m = (df.portfolio == name) & (df.V1 == V1) & (df.method == "Raw case estimates")
            df.loc[m, "estimate"] = ce
            df.loc[m, "total_error_pct"] = 100 * (ce - df.loc[m, "actual"]) / df.loc[m, "actual"]

    df.to_csv(TABLES / "oot_open_claims.csv", index=False)
    summ = df.pivot_table(index=["portfolio", "method"], columns="V1", values="total_error_pct")
    summ["mean |error|"] = summ.abs().mean(axis=1)
    med = df.groupby(["portfolio", "method"])["median_abs_log_error"].mean()
    summ["claim-level median |log error|"] = med
    summ = summ.round(2)
    summ.to_csv(TABLES / "oot_summary.csv")
    print(summ.to_string())

    for name in PORTFOLIOS:
        d = df[df.portfolio == name]
        fig, ax = plt.subplots(figsize=(9, 4.2))
        for m in d.method.unique():
            s = d[d.method == m].set_index("V1")["total_error_pct"]
            ax.plot(s.index, s.values, marker="o", label=m)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xlabel(f"Application date V1 (factors fitted at V0 = V1 − {H})")
        ax.set_ylabel("RBNS reserve error vs actual (%)")
        ax.set_title(f"Out-of-time test, open claims — {name}")
        ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(1.01, 0.5))
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGS / f"oot_open_claims_{name}.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
