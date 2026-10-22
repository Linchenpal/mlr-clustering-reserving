"""Other uses of claim groups in reserving (beyond splitting a chain-ladder triangle).

Use 3 - monitoring: group mix and observable settlement speed by notification
        cohort, to tell a change in mix from a change affecting every group.
Use 4 - large claims separately: chain ladder on the other claims, the large
        group reserved as case estimate x a factor fitted out of time.
Use 5 - groups inside a model with a calendar-period trend: a Poisson GLM for
        incremental paid per notified claim, with development effects, a
        calendar trend and (optionally) a trend in the speed of development,
        estimated with or without group-specific development patterns.

Everything uses only data available at the valuation date V. Actual payments
after V are used only to score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.data.splice import SplicePortfolio
from src.features.valuation import features_at_valuation
from src.models.case_estimate_factors import SingleGroup, emerged_since
from src.models.chain_ladder import MIN_ROWS, chain_ladder, paid_triangle


# ------------------------------------------------------------------ use 3
def cohort_monitor(p: SplicePortfolio, V: int, labels: pd.Series, horizon: int = 8) -> pd.DataFrame:
    """By notification period and group: number of claims, and share of claims
    settled within ``horizon`` quarters of notification (observable at V only
    for cohorts with notif_period <= V - horizon)."""
    c = p.claims.set_index("claim_no").loc[labels.index]
    closed = (c["settle_time"] <= np.minimum(c["notif_time"] + horizon, V)).astype(float)
    obs = c["notif_period"] <= V - horizon
    df = pd.DataFrame({"period": c["notif_period"], "group": labels, "closed": closed.where(obs)})
    return df.groupby(["period", "group"]).agg(n=("closed", "size"), share_closed=("closed", "mean")).reset_index()


def trend(series_by_period: pd.Series, with_p: bool = False):
    """Spearman rank correlation with the period (a simple, robust trend measure)."""
    from scipy.stats import spearmanr
    s = series_by_period.dropna()
    if len(s) <= 3:
        return (np.nan, np.nan) if with_p else np.nan
    rho, pval = spearmanr(s.index, s.values)
    return (float(rho), float(pval)) if with_p else float(rho)


# ------------------------------------------------------------------ use 4
def large_separately(p: SplicePortfolio, V: int, large_ids: pd.Index, h: int = 8) -> np.ndarray:
    """RBNS total: CL on non-large claims + factor x case estimate on open large claims.

    The factor is fitted at V - h on the open large claims of that date, with data up to V.
    Returns [total, cl_part, large_part].
    """
    rest = p.claims.loc[(p.claims["notif_time"] <= V) & ~p.claims["claim_no"].isin(large_ids), "claim_no"]
    cl_part = chain_ladder(paid_triangle(p, V, rest))["reserve"].sum()
    V0 = V - h
    f0 = features_at_valuation(p, V0)
    o0 = f0[(f0["is_open"] == 1) & f0.index.isin(large_ids)]
    lam = emerged_since(p, o0.index, V0, V).sum() / o0["case_estimate"].sum() if len(o0) else 1.0
    f1 = features_at_valuation(p, V)
    o1 = f1[(f1["is_open"] == 1) & f1.index.isin(large_ids)]
    large_part = lam * o1["case_estimate"].sum()
    return np.array([cl_part + large_part, cl_part, large_part])


# ------------------------------------------------------------------ use 5
def _cells(p: SplicePortfolio, V: int, labels: pd.Series | None):
    """Incremental paid and exposure by (notification period, dev, group)."""
    c = p.claims[p.claims["notif_time"] <= V][["claim_no", "notif_period"]].copy()
    c["group"] = 0 if labels is None else c["claim_no"].map(labels).values
    pay = p.payments.merge(c, on="claim_no")
    pay = pay[pay["payment_time"] <= V]
    pay["dev"] = pay["payment_period"] - pay["notif_period"]
    groups = sorted(c["group"].unique())
    expo = c.groupby(["notif_period", "group"]).size()
    rows = []
    for g in groups:
        for r in range(1, V + 1):
            n = expo.get((r, g), 0)
            if n == 0:
                continue
            for j in range(0, V):
                rows.append((r, j, g, n, r + j <= V))
    cells = pd.DataFrame(rows, columns=["r", "j", "g", "n", "observed"])
    inc = pay.groupby(["notif_period", "dev", "group"])["payment_inflated"].sum()
    cells["y"] = [inc.get((r, j, g), 0.0) for r, j, g in zip(cells.r, cells.j, cells.g)]
    return cells


def glm_reserve(p: SplicePortfolio, V: int, labels: pd.Series | None = None,
                calendar_trend: bool = True, speed_trend: bool = False, min_rows: int = MIN_ROWS) -> float:
    """Quasi-Poisson GLM on incremental paid per notified claim.

    log E[X_{r,j,g}] = log n_{r,g} + a_{j,g} + gamma * (r + j) [+ beta * r * log(1 + j)]

    Development effects a_{j,g} are group-specific when labels are given, the
    trends are common. Like the chain ladder here, only development ages with
    at least ``min_rows`` observed cohorts are fitted and projected (no tail).
    """
    cells = _cells(p, V, labels)
    jmax = V - min_rows
    cells = cells[cells["j"] <= jmax]
    dev = pd.get_dummies(cells["j"].astype(str) + "_" + cells["g"].astype(str), prefix="a", dtype=float)
    X = dev
    if calendar_trend:
        X = X.assign(calendar=(cells["r"] + cells["j"]).values / V)
    if speed_trend:
        X = X.assign(speed=(cells["r"].values / V) * np.log1p(cells["j"].values))
    obs = cells["observed"].values
    # drop development/group columns that never appear among observed cells
    keep = X.columns[(X[obs].abs().sum(axis=0) > 0).values]
    X = X[keep]
    model = sm.GLM(cells.loc[obs, "y"].values, X[obs].values, family=sm.families.Poisson(),
                   offset=np.log(cells.loc[obs, "n"].values))
    res = model.fit(maxiter=200)
    fut = ~obs
    mu = np.exp(X[fut].values @ res.params + np.log(cells.loc[fut, "n"].values))
    return float(mu.sum())
