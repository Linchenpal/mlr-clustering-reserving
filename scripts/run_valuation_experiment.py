"""Valuation-date reserving experiment (Phase 2b prototype).

Question: does segmenting claims with clusters built from information
available at the valuation date improve a paid Chain Ladder estimate of the
RBNS reserve, compared with an unsegmented Chain Ladder and with simple
non-clustering segmentations?

Run from the repo root:
    python scripts/run_valuation_experiment.py
Outputs: reports/tables/*.csv, reports/figures/*.png, reports/tables/key_numbers.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.splice import load_splice, validate  # noqa: E402
from src.features.clustering import (bootstrap_ari, fit_kmeans_clusters, fit_ward_clusters,  # noqa: E402
                                     prepare, quantile_bands, silhouette_by_k)
from src.features.valuation import features_at_notification, features_at_valuation, future_payments  # noqa: E402
from src.models.chain_ladder import (actual_future_by_row, chain_ladder, paid_triangle,  # noqa: E402
                                     reserve_errors, segmented_reserve)

TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "reports" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

VALUATION_DATES = [20, 24, 28, 32, 36, 40]
KS = [2, 3, 4, 5]
N_PLACEBO = 30
# Initial case estimate relative to its notification period (removes inflation drift).
NOTIF_COLS = ["notidel", "initial_ce_rel"]
NOTIF_COLS_NOMINAL = ["notidel", "initial_case_estimate"]
NOTIF_COLS_COV = NOTIF_COLS + ["injury_severity", "legal_rep_no", "claimant_age_band"]
# Valuation-date features for open claims; monetary ones in scale-free form.
OPEN_COLS = ["notidel", "age_since_notification", "initial_ce_rel", "paid_over_initial_ce",
             "ce_over_initial_ce", "n_payments_to_date", "time_since_last_payment",
             "n_revisions_to_date", "max_abs_log_revision"]
SEVERITY_GROUPS = {1: "low (1,6)", 6: "low (1,6)", 2: "mid (2)", 3: "high (3-5)", 4: "high (3-5)", 5: "high (3-5)"}

PORTFOLIOS = {
    "standard": ("complexity_5", ""),
    "covariates": ("complexity_5_cov_regen", "_cov"),
}


def evaluate(p, V, labels, act):
    est = segmented_reserve(p, V, labels)
    return reserve_errors(est, act)


def run_backtest(name, p):
    rows = []
    for V in VALUATION_DATES:
        fn = features_at_notification(p, V)
        act = actual_future_by_row(p, V)

        def add(method, k, labels, **extra):
            r = evaluate(p, V, labels, act)
            rows.append({"portfolio": name, "V": V, "method": method, "k": k, **r, **extra})

        add("Unsegmented CL", 1, None)
        r = reserve_errors(segmented_reserve(p, V, None, min_rows=1), act)
        rows.append({"portfolio": name, "V": V, "method": "Unsegmented CL (no min-rows rule)", "k": 1, **r})
        open_ce = features_at_valuation(p, V)["case_estimate"].sum()
        rows.append({"portfolio": name, "V": V, "method": "Case estimates", "k": 0, "estimate": open_ce,
                     "actual": act.sum(), "total_error_pct": 100 * (open_ce - act.sum()) / act.sum(),
                     "row_abs_error_pct": np.nan})

        for k in KS:
            _, lab_nom = fit_kmeans_clusters(fn, k, columns=NOTIF_COLS_NOMINAL)
            add("K-means [notif, nominal CE]", k, lab_nom)
        feature_sets = {"notif": NOTIF_COLS}
        if p.covariates is not None:
            feature_sets["notif+cov"] = NOTIF_COLS_COV
        for fs_name, cols in feature_sets.items():
            sil = silhouette_by_k(fn, cols, ks=KS)
            k_sil = int(sil.idxmax())
            for k in KS:
                _, lab_km = fit_kmeans_clusters(fn, k, columns=cols)
                add(f"K-means [{fs_name}]", k, lab_km, k_by_silhouette=k_sil)
                _, lab_w = fit_ward_clusters(fn, k, columns=cols)
                add(f"Ward [{fs_name}]", k, lab_w, k_by_silhouette=k_sil)

        for k in KS:
            add("Bands of initial case estimate", k, quantile_bands(fn["initial_ce_rel"], k))
            # Placebo: random groups of the same sizes as the K-means solution
            _, lab_km = fit_kmeans_clusters(fn, k, columns=NOTIF_COLS)
            rng = np.random.default_rng(1000 * V + k)
            errs = []
            for _ in range(N_PLACEBO):
                perm = pd.Series(rng.permutation(lab_km.values), index=lab_km.index)
                errs.append(evaluate(p, V, perm, act))
            e = pd.DataFrame(errs)
            rows.append({"portfolio": name, "V": V, "method": "Random groups (placebo, mean)", "k": k,
                         "estimate": e.estimate.mean(), "actual": act.sum(),
                         "total_error_pct": e.total_error_pct.mean(), "row_abs_error_pct": e.row_abs_error_pct.mean(),
                         "placebo_total_err_p5": e.total_error_pct.quantile(0.05),
                         "placebo_total_err_p95": e.total_error_pct.quantile(0.95)})

        if p.covariates is not None:
            add("Injury-severity groups (true covariate)", 3, fn["injury_severity"].map(SEVERITY_GROUPS))
    return pd.DataFrame(rows)


def cluster_profiles(name, p, V=40, k=3):
    """Size, shares over time and CL development pattern by cluster (notification features)."""
    fn = features_at_notification(p, V)
    _, lab = fit_kmeans_clusters(fn, k, columns=NOTIF_COLS)
    fut = future_payments(p, V)
    c = p.claims.set_index("claim_no").loc[fn.index]
    prof = pd.DataFrame({
        "n_claims": lab.value_counts().sort_index(),
        "median_notidel": fn["notidel"].groupby(lab).median(),
        "median_initial_case_estimate": fn["initial_case_estimate"].groupby(lab).median(),
        "share_notif_periods_1_20": lab[fn["notif_period"] <= 20].value_counts(normalize=True).sort_index(),
        "share_notif_periods_21_40": lab[fn["notif_period"] > 20].value_counts(normalize=True).sort_index(),
        # hindsight columns, for interpretation only
        "hindsight_median_setldel": c["setldel"].groupby(lab).median(),
        "hindsight_median_no_payment": c["no_payment"].groupby(lab).median(),
        "actual_future_paid_m": fut.groupby(lab).sum() / 1e6,
    })
    prof.index.name = "cluster"
    prof.insert(0, "portfolio", name)
    _, lab_nom = fit_kmeans_clusters(fn, k, columns=NOTIF_COLS_NOMINAL)
    prof["nominal_share_notif_periods_1_20"] = lab_nom[fn["notif_period"] <= 20].value_counts(normalize=True).sort_index()
    prof["nominal_share_notif_periods_21_40"] = lab_nom[fn["notif_period"] > 20].value_counts(normalize=True).sort_index()

    patterns = {}
    for g in sorted(lab.unique()):
        cl = chain_ladder(paid_triangle(p, V, lab.index[lab == g]))
        patterns[g] = 1 / np.r_[np.array([np.prod(cl["factors"][j:]) for j in range(V - 1)]), 1.0]
    return prof, patterns, lab, fn


def open_claims_analysis(name, p, V=40, k=4):
    """E2: cluster open claims on full valuation-date features; check whether clusters
    separate the subsequent development (hindsight used for evaluation only)."""
    fv = features_at_valuation(p, V)
    op = fv[fv["is_open"] == 1].copy()
    cols = OPEN_COLS
    if p.covariates is not None:
        cols += ["injury_severity", "legal_rep_no", "claimant_age_band"]
    sil = silhouette_by_k(op, cols, ks=range(2, 7))
    _, lab = fit_kmeans_clusters(op, k, columns=cols)
    fut = future_payments(p, V).loc[op.index]
    settle = p.claims.set_index("claim_no").loc[op.index, "settle_time"]
    t = pd.DataFrame({
        "n_open": lab.value_counts().sort_index(),
        "median_age_since_notification": op["age_since_notification"].groupby(lab).median(),
        "median_case_estimate": op["case_estimate"].groupby(lab).median(),
        "median_paid_to_date": op["paid_to_date"].groupby(lab).median(),
        "case_estimate_m": op["case_estimate"].groupby(lab).sum() / 1e6,
        "actual_future_m": fut.groupby(lab).sum() / 1e6,
        "median_quarters_to_settle": (settle - V).groupby(lab).median(),
    })
    t["actual_over_case_estimate"] = t["actual_future_m"] / t["case_estimate_m"]
    t.index.name = "cluster"
    t.insert(0, "portfolio", name)

    # How much of the variation in log future payments do the clusters explain,
    # compared with the case estimate alone?
    y = np.log1p(fut)
    r2_cluster = 1 - ((y - y.groupby(lab).transform("mean")) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    x = np.log1p(op["case_estimate"])
    beta = np.polyfit(x, y, 1)
    r2_ce = 1 - ((y - np.polyval(beta, x)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    # both: within-cluster regression on log case estimate
    resid = []
    for g in lab.unique():
        m = lab == g
        b = np.polyfit(x[m], y[m], 1)
        resid.append(y[m] - np.polyval(b, x[m]))
    r2_both = 1 - (pd.concat(resid) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return t, {"silhouette": sil.round(3).to_dict(), "r2_log_future_cluster_only": r2_cluster,
               "r2_log_future_case_estimate_only": r2_ce, "r2_log_future_cluster_plus_case_estimate": r2_both}


def main():
    key = {}
    backtests, profiles, open_tabs = [], [], []
    for name, (folder, suffix) in PORTFOLIOS.items():
        p = load_splice(folder, suffix)
        key[name] = {"validation": validate(p)}
        bt = run_backtest(name, p)
        backtests.append(bt)

        prof, patterns, lab, fn = cluster_profiles(name, p)
        profiles.append(prof)
        key[name]["stability_bootstrap_ari_notif_k3"] = float(np.round(bootstrap_ari(fn, NOTIF_COLS, 3).mean(), 3))
        key[name]["stability_bootstrap_ari_notif_k4"] = float(np.round(bootstrap_ari(fn, NOTIF_COLS, 4).mean(), 3))
        key[name]["drift_max_share_shift_nominal"] = float(
            (prof["nominal_share_notif_periods_21_40"] - prof["nominal_share_notif_periods_1_20"]).abs().max().round(3))
        key[name]["drift_max_share_shift_relative"] = float(
            (prof["share_notif_periods_21_40"] - prof["share_notif_periods_1_20"]).abs().max().round(3))

        fig, ax = plt.subplots(figsize=(6.5, 4))
        for g, pat in patterns.items():
            ax.plot(np.arange(len(pat)), 100 * pat, label=f"Cluster {g} (n={int(prof.loc[g, 'n_claims'])})")
        un = chain_ladder(paid_triangle(p, 40))
        ax.plot(np.arange(40), 100 / np.r_[[np.prod(un["factors"][j:]) for j in range(39)], 1.0], "k--", label="All claims")
        ax.set_xlabel("Quarters since notification")
        ax.set_ylabel("% of ultimate paid (CL pattern at V=40)")
        ax.set_title(f"Paid development pattern by cluster — {name}")
        ax.legend(frameon=False, fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGS / f"cl_pattern_by_cluster_{name}.png", dpi=150)
        plt.close(fig)

        t, info = open_claims_analysis(name, p)
        open_tabs.append(t)
        key[name]["open_claims_V40"] = {k: (float(v) if not isinstance(v, dict) else v) for k, v in info.items()}

    bt = pd.concat(backtests, ignore_index=True)
    bt.to_csv(TABLES / "backtest_rbns_cl.csv", index=False)
    pd.concat(profiles).to_csv(TABLES / "cluster_profiles_notification_V40.csv")
    pd.concat(open_tabs).to_csv(TABLES / "open_claims_clusters_V40.csv")

    # Summary: average over valuation dates, by method and k
    summ = (bt.groupby(["portfolio", "method", "k"])[["total_error_pct", "row_abs_error_pct"]]
            .agg(["mean", lambda s: s.abs().mean()]).round(1))
    summ.columns = ["total_err_mean", "total_err_mean_abs", "row_err_mean", "row_err_mean_abs"]
    summ = summ.drop(columns="row_err_mean_abs")
    summ.to_csv(TABLES / "backtest_summary.csv")
    v40 = bt[bt.V == 40][["portfolio", "method", "k", "estimate", "actual", "total_error_pct", "row_abs_error_pct"]]
    v40.round(1).to_csv(TABLES / "backtest_V40.csv", index=False)

    # Figure: total error over valuation dates for selected methods (k=3)
    for name in PORTFOLIOS:
        d = bt[bt.portfolio == name]
        fig, ax = plt.subplots(figsize=(9, 4.2))
        sel = [("Unsegmented CL", 1), ("K-means [notif]", 3), ("K-means [notif, nominal CE]", 3), ("Ward [notif]", 3),
               ("Bands of initial case estimate", 3), ("Random groups (placebo, mean)", 3), ("Case estimates", 0)]
        if name == "covariates":
            sel += [("K-means [notif+cov]", 3), ("Injury-severity groups (true covariate)", 3)]
        for m, k in sel:
            s = d[(d.method == m) & (d.k == k)].set_index("V")["total_error_pct"]
            ax.plot(s.index, s.values, marker="o", label=f"{m}" + (f" k={k}" if k > 1 else ""))
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xlabel("Valuation date (quarter)")
        ax.set_ylabel("RBNS reserve error vs actual (%)")
        ax.set_title(f"Backtest of RBNS reserve — {name}")
        ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(1.01, 0.5))
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGS / f"backtest_total_error_{name}.png", dpi=150)
        plt.close(fig)

    (TABLES / "key_numbers.json").write_text(json.dumps(key, indent=2, default=str))
    print(summ.to_string())
    print(v40.round(1).to_string())
    print(json.dumps(key, indent=2, default=str))


if __name__ == "__main__":
    main()
