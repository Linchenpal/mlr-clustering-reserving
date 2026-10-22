"""
Regenerate the figures used in the article's Results section.

Run from anywhere, after the analysis has been run:

    python notebooks/02 ...            (writes reports/tables/phase2_*.csv)
    python scripts/run_valuation_experiment.py
    python scripts/run_open_claims_oot.py
    python article/make_figures_results.py

Inputs : reports/tables/phase2_diagnostics.csv, phase2_stability.csv,
         backtest_rbns_cl.csv, oot_open_claims.csv
Outputs: article/graphics/fig_expost.png
         article/graphics/fig_backtest.png
         article/graphics/fig_oot.png

Same print style as article/make_figures.py.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "reports" / "tables"
OUT = Path(__file__).resolve().parent / "graphics"
OUT.mkdir(exist_ok=True)

# --- style (as in make_figures.py) ---------------------------------------------
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, BLUE_DARK, RED = "#2a78d6", "#184f95", "#e34948"
GREY, ORANGE, GREEN = "#8a8984", "#d9822b", "#3a9a5b"
available = {f.name for f in font_manager.fontManager.ttflist}
serif = next((f for f in ["Times New Roman", "TeX Gyre Termes", "STIXGeneral", "DejaVu Serif"] if f in available), "serif")
mpl.rcParams.update({
    "font.family": serif, "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.6,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": "#b9b8b2", "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.03, "savefig.dpi": 300,
    "mathtext.fontset": "stix",
})
LINE = dict(lw=1.1, marker="o", ms=2.6, mec="white", mew=0.4)

# --------------------------------------------------------------------------------
# Figure 4 - ex-post clustering: (a) silhouette by k, (b) bootstrap stability by k
# --------------------------------------------------------------------------------
diag = pd.read_csv(TAB / "phase2_diagnostics.csv")
stab = pd.read_csv(TAB / "phase2_stability.csv")
fig, (a, b) = plt.subplots(1, 2, figsize=(6.3, 2.0))
for name, col in (("K-means", BLUE), ("Ward", RED)):
    d = diag[diag.method == name]
    a.plot(d.k, d.silhouette, color=col, label=name, **LINE)
    s = stab[stab.method == name.lower().replace("-", "")]
    b.plot(s.k, s["mean ARI"], color=col, label=name, **LINE)
a.set_title("(a) Silhouette (higher is better)", loc="left", fontweight="bold")
a.set_xlabel("number of clusters $k$")
b.set_title("(b) Bootstrap stability (mean ARI)", loc="left", fontweight="bold")
b.set_xlabel("number of clusters $k$"); b.set_ylim(0, 1.02); b.set_xticks([2, 3, 4, 5])
a.legend(frameon=False)
fig.tight_layout(w_pad=1.5)
fig.savefig(OUT / "fig_expost.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Figure 5 - backtest of segmented chain ladder (RBNS), by portfolio
# --------------------------------------------------------------------------------
bt = pd.read_csv(TAB / "backtest_rbns_cl.csv")


def series(d, method, k):
    return d[(d.method == method) & (d.k == k)].set_index("V")


fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.35), sharey=True)
for ax, pf, title in zip(axes, ("standard", "covariates"), ("(a) Standard portfolio", "(b) Covariate portfolio")):
    d = bt[bt.portfolio == pf]
    pl = series(d, "Random groups (placebo, mean)", 3)
    ax.fill_between(pl.index, pl.placebo_total_err_p5, pl.placebo_total_err_p95, color=GREY, alpha=0.25, lw=0,
                    label="Random groups, 5th–95th pct.")
    ax.plot(series(d, "Unsegmented CL", 1).total_error_pct, color=INK, label="Unsegmented CL", **LINE)
    ax.plot(series(d, "K-means [notif]", 3).total_error_pct, color=BLUE, label="K-means, notification features", **LINE)
    ax.plot(series(d, "Bands of initial case estimate", 3).total_error_pct, color=ORANGE, label="Bands of initial case estimate", **LINE)
    if pf == "covariates":
        ax.plot(series(d, "K-means [notif+cov]", 3).total_error_pct, color=GREEN, label="K-means, + covariates", **LINE)
    ax.plot(series(d, "Case estimates", 0).total_error_pct, color=RED, ls=(0, (3, 2)), label="Case estimates", **LINE)
    ax.axhline(0, color=INK_2, lw=0.6)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("valuation date (quarter)"); ax.set_xticks([20, 24, 28, 32, 36, 40])
axes[0].set_ylabel("RBNS reserve error (%)")
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, frameon=False, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.12))
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT / "fig_backtest.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Figure 6 - out-of-time test of case-estimate factors for open claims
# --------------------------------------------------------------------------------
oot = pd.read_csv(TAB / "oot_open_claims.csv")
fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.35), sharey=True)
for ax, pf, title in zip(axes, ("standard", "covariates"), ("(a) Standard portfolio", "(b) Covariate portfolio")):
    d = oot[oot.portfolio == pf]

    def s(m):
        return d[d.method == m].set_index("V1").total_error_pct

    ax.plot(s("Raw case estimates"), color=RED, ls=(0, (3, 2)), label="Raw case estimates", **LINE)
    ax.plot(s("Unsegmented paid CL (all reported claims)"), color=INK, label="Unsegmented paid CL", **LINE)
    ax.plot(s("Single factor (no groups)"), color=GREY, label="Single factor", **LINE)
    ax.plot(s("Bands of case estimate / initial (k=4)"), color=ORANGE, label="Bands of case est. / initial est.", **LINE)
    ax.plot(s("K-means open-claim clusters (k=4)"), color=BLUE, label="K-means open-claim clusters", **LINE)
    if pf == "covariates":
        ax.plot(s("K-means open-claim clusters + covariates (k=4)"), color=GREEN, label="K-means, + covariates", **LINE)
    ax.axhline(0, color=INK_2, lw=0.6)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel(r"application date $\tau_1$ (factors fitted at $\tau_1-8$)"); ax.set_xticks([24, 28, 32, 36, 40])
axes[0].set_ylabel("RBNS reserve error (%)")
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, frameon=False, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.12))
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT / "fig_oot.png")
plt.close(fig)
print("written:", [p.name for p in OUT.glob("fig_*.png")])

# --------------------------------------------------------------------------------
# Figure 7 - mean absolute RBNS error by method across SPLICE scenarios 1-5
# --------------------------------------------------------------------------------
summ = pd.read_csv(TAB / "group_uses_summary.csv", index_col=0)
sel = [
    ("E1 paid CL, unsegmented", "Paid CL, unsegmented", INK),
    ("E1 paid CL by clusters (k=3)", "Paid CL by clusters", BLUE),
    ("E2 case-estimate factor, single", "Case-estimate factor, single", GREY),
    ("E2 case-estimate factors, clusters (k=4)", "Case-estimate factors by clusters", BLUE_DARK),
    ("U4 large claims apart (cluster)", "Large claims apart", ORANGE),
    ("U5 GLM, calendar + speed trend", "GLM, calendar + speed trend", "#b9b8b2"),
    ("U5 GLM, calendar + speed trend, by clusters", "GLM, trends, by clusters", GREEN),
]
fig, ax = plt.subplots(figsize=(6.3, 2.4))
w = 0.11
for i, (m, lab, col) in enumerate(sel):
    vals = [summ.loc[m, f"C{k} mean |err|"] for k in range(1, 6)]
    ax.bar([k + (i - 3) * w for k in range(5)], vals, width=w, color=col, label=lab, linewidth=0)
ax.set_xticks(range(5), [f"Complexity {k}" for k in range(1, 6)])
ax.set_ylabel("mean |RBNS error| (%)")
ax.tick_params(axis="x", length=0)
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.42))
fig.tight_layout()
fig.savefig(OUT / "fig_scenarios.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Figure 8 - monitoring: share settled within 8 quarters, by cluster, C1 / C3 / C5
# --------------------------------------------------------------------------------
mon = pd.read_csv(TAB / "group_uses_monitor.csv")
names = {0: "small initial estimate", 1: "medium", 2: "large"}
cols = {0: BLUE, 1: ORANGE, 2: RED}
fig, axes = plt.subplots(1, 3, figsize=(6.3, 1.9), sharey=True)
for ax, (k, t) in zip(axes, ((1, "(a) Complexity 1"), (3, "(b) Complexity 3"), (5, "(c) Complexity 5"))):
    d = mon[mon.scenario == k]
    for g, dg in d.groupby("group"):
        dg = dg.dropna(subset=["share_closed"])
        ax.plot(dg["period"], dg["share_closed"].rolling(4, min_periods=1).mean(), color=cols[g], lw=1.1, label=names[g])
    ax.set_title(t, loc="left", fontweight="bold")
    ax.set_xlabel("notification period"); ax.set_xticks([1, 10, 20, 30])
axes[0].set_ylabel("settled within 8 quarters")
axes[0].legend(frameon=False, fontsize=6.2)
fig.tight_layout(w_pad=0.8)
fig.savefig(OUT / "fig_monitor.png")
plt.close(fig)
print("written scenario figures")
