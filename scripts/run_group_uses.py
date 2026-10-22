"""Uses of claim groups beyond triangle splitting, on SPLICE Complexities 1-5.

For each scenario and valuation date V = 24, 28, ..., 40 (standard portfolios):

  Experiment 1  paid CL: unsegmented, K-means notification clusters (k=3), random groups
  Experiment 2  case-estimate factors fitted at V-8 (single, bands, K-means open-claim clusters)
  Use 4         large claims separately (cluster or rule), CL on the rest
  Use 5         Poisson GLM with calendar trend, with and without a speed-of-development
                trend, with and without group-specific development patterns
  Use 3         monitoring table: group mix and share settled within 8 quarters, by cohort

Run from the repo root:
    python scripts/run_group_uses.py
Outputs: reports/tables/group_uses_*.csv, reports/figures/group_uses_*.png
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
from src.features.clustering import fit_kmeans_clusters  # noqa: E402
from src.features.valuation import features_at_notification, features_at_valuation  # noqa: E402
from src.models.case_estimate_factors import BandGrouper, KMeansGrouper, SingleGroup, run_oot  # noqa: E402
from src.models.chain_ladder import actual_future_by_row, segmented_reserve  # noqa: E402
from src.models.group_uses import cohort_monitor, glm_reserve, large_separately, trend  # noqa: E402

TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "reports" / "figures"
VALUATION_DATES = [24, 28, 32, 36, 40]
NOTIF_COLS = ["notidel", "initial_ce_rel"]
OPEN_COLS = ["notidel", "age_since_notification", "initial_ce_rel", "paid_over_initial_ce",
             "ce_over_initial_ce", "n_payments_to_date", "time_since_last_payment",
             "n_revisions_to_date", "max_abs_log_revision"]
N_PLACEBO = 10
SCENARIOS = {
    1: "simple, homogeneous, no inflation",
    2: "size-dependent delays, 2% p.a. inflation",
    3: "settlement speeds up over time",
    4: "inflation shock at time 30",
    5: "full complexity (as in the main study)",
}


def pct(est, act):
    return 100 * (est - act) / act


def run_scenario(k: int) -> tuple[list[dict], pd.DataFrame]:
    p = load_splice(f"complexity_{k}", "", k)
    rows = []
    for V in VALUATION_DATES:
        act = actual_future_by_row(p, V).sum()
        fn = features_at_notification(p, V)
        _, lab = fit_kmeans_clusters(fn, 3, columns=NOTIF_COLS)  # cluster 2 = largest initial estimates

        def add(method, est):
            rows.append({"scenario": k, "V": V, "method": method, "estimate": est, "actual": act,
                         "error_pct": pct(est, act)})

        # Experiment 1
        add("E1 paid CL, unsegmented", segmented_reserve(p, V).sum())
        add("E1 paid CL by clusters (k=3)", segmented_reserve(p, V, lab).sum())
        rng = np.random.default_rng(V * 10 + k)
        add("E1 paid CL by random groups (mean)", np.mean([
            segmented_reserve(p, V, pd.Series(rng.permutation(lab.values), index=lab.index)).sum()
            for _ in range(N_PLACEBO)]))
        # Experiment 2
        add("E2 raw case estimates", features_at_valuation(p, V)["case_estimate"].sum())
        add("E2 case-estimate factor, single", run_oot(p, V - 8, V, SingleGroup())["estimate"])
        add("E2 case-estimate factors, bands", run_oot(p, V - 8, V, BandGrouper("ce_over_initial_ce", 4))["estimate"])
        add("E2 case-estimate factors, clusters (k=4)", run_oot(p, V - 8, V, KMeansGrouper(OPEN_COLS, 4))["estimate"])
        # Use 4: large claims separately
        large_c = lab.index[lab == lab.max()]
        add("U4 large claims apart (cluster)", large_separately(p, V, large_c)[0])
        thr = fn["initial_ce_rel"].quantile(1 - len(large_c) / len(fn))
        add("U4 large claims apart (rule, same size)", large_separately(p, V, fn.index[fn["initial_ce_rel"] >= thr])[0])
        # Use 5: GLM
        add("U5 GLM, no calendar trend", glm_reserve(p, V, calendar_trend=False))
        add("U5 GLM, calendar trend", glm_reserve(p, V))
        add("U5 GLM, calendar + speed trend", glm_reserve(p, V, speed_trend=True))
        add("U5 GLM, calendar trend, by clusters", glm_reserve(p, V, lab))
        add("U5 GLM, calendar + speed trend, by clusters", glm_reserve(p, V, lab, speed_trend=True))

    # Use 3: monitoring at V = 40
    V = 40
    fn = features_at_notification(p, V)
    _, lab = fit_kmeans_clusters(fn, 3, columns=NOTIF_COLS)
    mon = cohort_monitor(p, V, lab)
    mon.insert(0, "scenario", k)
    return rows, mon


def main():
    rows, mons = [], []
    for k in SCENARIOS:
        r, m = run_scenario(k)
        rows += r
        mons.append(m)
        print(f"scenario {k} done")
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "group_uses_backtest.csv", index=False)
    summ = df.pivot_table(index="method", columns="scenario", values="error_pct", aggfunc=lambda s: s.abs().mean())
    summ.columns = [f"C{c} mean |err|" for c in summ.columns]
    summ["mean over scenarios"] = summ.mean(axis=1)
    summ = summ.round(1)
    summ.to_csv(TABLES / "group_uses_summary.csv")
    print(summ.to_string())

    mon = pd.concat(mons, ignore_index=True)
    mon.to_csv(TABLES / "group_uses_monitor.csv", index=False)
    # Trend summary: does the mix move, and does settlement speed move, within each group?
    out = []
    for k, d in mon.groupby("scenario"):
        tot = d.groupby("period")["n"].transform("sum")
        d = d.assign(share=d["n"] / tot)
        for g, dg in d.groupby("group"):
            dg = dg.set_index("period")
            rs, ps = trend(dg["share"], with_p=True)
            rv, pv = trend(dg["share_closed"], with_p=True)
            out.append({"scenario": k, "group": g, "mean share": dg["share"].mean(),
                        "trend in share (Spearman)": rs, "p-value share": ps,
                        "share settled within 8q, periods 1-10": dg.loc[dg.index <= 10, "share_closed"].mean(),
                        "share settled within 8q, periods 23-32": dg.loc[(dg.index >= 23) & (dg.index <= 32), "share_closed"].mean(),
                        "trend in speed (Spearman)": rv, "p-value speed": pv})
    tr = pd.DataFrame(out).round(3)
    tr.to_csv(TABLES / "group_uses_monitor_trends.csv", index=False)
    print(tr.to_string())

    # Figure: share settled within 8 quarters, by group, scenarios 1, 3, 5
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
    names = {0: "small initial estimate", 1: "medium", 2: "large"}
    for ax, k in zip(axes, (1, 3, 5)):
        d = mon[mon.scenario == k]
        for g, dg in d.groupby("group"):
            dg = dg.dropna(subset=["share_closed"])
            ax.plot(dg["period"], dg["share_closed"].rolling(4, min_periods=1).mean(), label=f"cluster {g} ({names.get(g, g)})")
        ax.set_title(f"Complexity {k}: {SCENARIOS[k]}", fontsize=9)
        ax.set_xlabel("notification period"); ax.grid(alpha=0.3)
    axes[0].set_ylabel("share settled within 8 quarters\n(4-period moving average)")
    axes[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "group_uses_monitor_speed.png", dpi=150)
    plt.close(fig)

    # Figure: mean |error| by scenario for the main methods
    sel = ["E1 paid CL, unsegmented", "E1 paid CL by clusters (k=3)", "E2 case-estimate factor, single",
           "E2 case-estimate factors, clusters (k=4)", "U4 large claims apart (cluster)",
           "U5 GLM, calendar + speed trend", "U5 GLM, calendar + speed trend, by clusters"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    w = 0.12
    for i, m in enumerate(sel):
        vals = [summ.loc[m, f"C{k} mean |err|"] for k in SCENARIOS]
        ax.bar(np.arange(5) + (i - 3) * w, vals, width=w, label=m)
    ax.set_xticks(range(5), [f"C{k}" for k in SCENARIOS])
    ax.set_ylabel("mean |RBNS error| (%), V = 24..40")
    ax.legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "group_uses_by_scenario.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
