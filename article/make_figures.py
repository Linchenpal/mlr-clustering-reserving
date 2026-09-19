"""
Regenerate the figures used in the article's Data section.

Run from anywhere:

    python article/make_figures.py

Inputs : data/raw/splice/complexity_5/claim_5.csv   (SPLICE, Complexity 5)
Outputs: article/graphics/fig_distributions.png
         article/graphics/fig_dependence.png
         article/graphics/fig_periods.png
         article/graphics/data_summary_stats.txt   (numbers quoted in the text)

The figures reproduce the analysis in notebooks/01_data_exploration.ipynb
(distributions, Spearman correlations, occurrence-period summaries) with a
print-oriented layout. Fig. 2(b) is an additional view (claim size vs
settlement delay); see the note in the article source.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw" / "splice" / "complexity_5" / "claim_5.csv"
OUT = Path(__file__).resolve().parent / "graphics"
OUT.mkdir(exist_ok=True)

# --- style: one hue, thin marks, recessive grid, Times-like serif -----------------
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, BLUE_DARK = "#2a78d6", "#184f95"
RED = "#e34948"
NEUTRAL = "#f0efec"

available = {f.name for f in font_manager.fontManager.ttflist}
serif = next(
    (f for f in ["Times New Roman", "TeX Gyre Termes", "STIXGeneral", "DejaVu Serif"] if f in available),
    "serif",
)
mpl.rcParams.update(
    {
        "font.family": serif,
        "font.size": 7.5,
        "axes.titlesize": 8,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "axes.edgecolor": "#b9b8b2",
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "axes.axisbelow": True,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "savefig.dpi": 300,
        "mathtext.fontset": "stix",
    }
)

# --- data ------------------------------------------------------------------------
claims = pd.read_csv(DATA, index_col=0)
FEATURES = ["claim_size", "notidel", "setldel", "no_payment"]
LABELS = {
    "claim_size": "Claim size",
    "notidel": "Notification delay",
    "setldel": "Settlement delay",
    "no_payment": "Number of payments",
}
XLAB_RAW = {
    "claim_size": "thousands of currency units",
    "notidel": "quarters",
    "setldel": "quarters",
    "no_payment": "payments",
}
XLAB_LOG = {
    "claim_size": r"$\log(1+x)$",
    "notidel": r"$\log(1+x)$",
    "setldel": r"$\log(1+x)$",
    "no_payment": r"$\log(1+x)$",
}


def skew(x):
    return float(pd.Series(x).skew())


# --------------------------------------------------------------------------------
# Figure 1 - marginal distributions, raw scale (top) versus log(1+x) scale (bottom)
# --------------------------------------------------------------------------------
fig, axes = plt.subplots(2, 4, figsize=(6.3, 2.75))
for j, col in enumerate(FEATURES):
    raw = claims[col].to_numpy(dtype=float)
    scale = 1e3 if col == "claim_size" else 1.0
    logged = np.log1p(raw)

    ax = axes[0, j]
    bins = np.arange(0.5, raw.max() + 1.5, 1) if col == "no_payment" else 40
    ax.hist(raw / scale, bins=bins, color=BLUE, edgecolor="white", linewidth=0.3)
    ax.set_title(LABELS[col], loc="left", fontweight="bold")
    ax.set_xlabel(XLAB_RAW[col])
    ax.text(0.97, 0.94, f"skew = {skew(raw):.2f}", transform=ax.transAxes, ha="right", va="top", color=INK)

    ax = axes[1, j]
    bins = 30 if col == "no_payment" else 40
    ax.hist(logged, bins=bins, color=BLUE, edgecolor="white", linewidth=0.3)
    ax.set_xlabel(XLAB_LOG[col])
    side = "right" if col in ("notidel", "no_payment") else "left"
    ax.text(0.97 if side == "right" else 0.03, 0.94, f"skew = {skew(logged):.2f}", transform=ax.transAxes, ha=side, va="top", color=INK)
    ax.set_xlabel(r"$\log(1+x)$")
    ax.margins(y=0.12)

axes[0, 0].set_ylabel("Number of claims")
axes[1, 0].set_ylabel("Number of claims")
for ax in axes.ravel():
    ax.tick_params(length=2)
fig.tight_layout(w_pad=0.6, h_pad=0.8)
fig.savefig(OUT / "fig_distributions.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Figure 2 - (a) Spearman correlations, (b) claim size vs settlement delay
# --------------------------------------------------------------------------------
rho = claims[FEATURES].corr(method="spearman")
names = ["Claim size", "Notification delay", "Settlement delay", "No. of payments"]

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.3, 2.3), gridspec_kw={"width_ratios": [1.1, 1.2]})

cmap_div = LinearSegmentedColormap.from_list("div", [BLUE_DARK, "#86b6ef", NEUTRAL, "#f2a29a", RED])
axa.grid(False)
im = axa.imshow(rho.values, cmap=cmap_div, norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1))
axa.set_xticks(range(4), names, fontsize=6.6, rotation=30, ha="right", rotation_mode="anchor")
axa.set_yticks(range(4), names, fontsize=6.6)
axa.tick_params(length=0)
for s in axa.spines.values():
    s.set_visible(False)
for i in range(4):
    for j in range(4):
        v = rho.values[i, j]
        axa.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if abs(v) > 0.6 else INK, fontsize=7.5)
axa.set_title("(a) Spearman rank correlation", loc="left", fontweight="bold")

# (b) hexbin, claim size against settlement delay (log scale)
x = np.log1p(claims["claim_size"])
y = np.log1p(claims["setldel"])
cmap_seq = LinearSegmentedColormap.from_list("seq", ["#e6effc", "#86b6ef", "#2a78d6", "#0d366b"])
axb.grid(False)
hb = axb.hexbin(x, y, gridsize=28, cmap=cmap_seq, mincnt=1, linewidths=0.2, edgecolors="white")
cb = fig.colorbar(hb, ax=axb, fraction=0.045, pad=0.02)
cb.set_label("claims per cell", color=INK_2)
cb.outline.set_visible(False)
cb.ax.tick_params(length=2)
axb.axvline(np.log(20000), color=RED, lw=1.0, ls=(0, (4, 3)))
axb.text(np.log(20000) - 0.1, y.max() * 0.985, "20,000", color=INK, ha="right", va="top")
axb.set_xlabel(r"claim size, $\log(1+x)$")
axb.set_ylabel(r"settlement delay, $\log(1+x)$")
axb.set_title("(b) Claim size vs settlement delay", loc="left", fontweight="bold")
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT / "fig_dependence.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Figure 3 - occurrence-period summaries
# --------------------------------------------------------------------------------
period = (
    claims.groupby("occurrence_period")
    .agg(
        frequency=("claim_no", "size"),
        med_size=("claim_size", "median"),
        med_setl=("setldel", "median"),
        mean_pay=("no_payment", "mean"),
    )
    .reset_index()
)
panels = [
    ("frequency", "Claim frequency", "claims"),
    ("med_size", "Median claim size", "thousands"),
    ("med_setl", "Median settlement delay", "quarters"),
    ("mean_pay", "Mean number of payments", "payments"),
]
fig, axes = plt.subplots(1, 4, figsize=(6.3, 1.45), sharex=True)
for ax, (col, title, unit) in zip(axes, panels):
    v = period[col] / (1e3 if col == "med_size" else 1)
    ax.plot(period["occurrence_period"], v, color=BLUE, lw=1.2, marker="o", ms=2.6, mec="white", mew=0.4)
    ax.axhline(v.mean(), color=INK_2, lw=0.6, ls=(0, (3, 3)))
    ax.set_title(title, loc="left", fontweight="bold", fontsize=7.3)
    ax.set_xlabel("occurrence period")
    ax.set_xticks([1, 10, 20, 30, 40])
    ax.tick_params(length=2)
fig.tight_layout(w_pad=0.5)
fig.savefig(OUT / "fig_periods.png")
plt.close(fig)

# --------------------------------------------------------------------------------
# Numbers quoted in the text (so every figure in the article is reproducible)
# --------------------------------------------------------------------------------
lines = []
desc = claims[FEATURES].describe(percentiles=[0.5, 0.95, 0.99]).T
lines.append("Descriptive statistics:\n" + desc.round(3).to_string())
lines.append("\nSkewness raw:\n" + claims[FEATURES].skew().round(2).to_string())
lines.append("\nSkewness log1p:\n" + np.log1p(claims[FEATURES]).skew().round(2).to_string())
lines.append("\nSpearman:\n" + rho.round(3).to_string())
lines.append("\nPearson:\n" + claims[FEATURES].corr().round(3).to_string())
srt = claims["claim_size"].sort_values(ascending=False)
lines.append(f"\nTop 10% of claims share of total claim size: {srt.head(int(0.10 * len(srt))).sum() / srt.sum():.3f}")
lines.append(f"Top 1% of claims share of total claim size: {srt.head(int(0.01 * len(srt))).sum() / srt.sum():.3f}")
lines.append(f"Max / median claim size: {srt.iloc[0] / srt.median():.1f}")
lines.append(f"Claims below 1,000: {(claims.claim_size < 1000).sum()}; below 100: {(claims.claim_size < 100).sum()}")
small = claims["claim_size"] < 20000
lines.append(f"\nShare of claims below 20,000: {small.mean():.3f}")
lines.append(claims.groupby(small).setldel.agg(["size", "median", "mean"]).round(2).to_string())
lines.append(f"\nPeriod frequency: min {period.frequency.min()}, max {period.frequency.max()}, mean {period.frequency.mean():.1f}")
rho_p = claims[["occurrence_period", "setldel"]].corr(method="spearman").iloc[0, 1]
lines.append(f"Spearman(occurrence_period, settlement delay) = {rho_p:.3f}")
(OUT / "data_summary_stats.txt").write_text("\n".join(lines))
print("\n".join(lines))
