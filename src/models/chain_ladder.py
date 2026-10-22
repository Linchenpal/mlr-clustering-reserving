"""Paid Chain Ladder on notification-period triangles, optionally by segment.

Rows are *notification* periods rather than occurrence periods. A notification
cohort contains only reported claims, so the projection estimates the RBNS
reserve and can be compared with the actual future payments of the claims
reported by the valuation date. IBNR (claims not yet reported) is a separate
problem and is excluded here.

Development index ``j = payment_period - notif_period`` (0 = paid in the
notification quarter). A cell is observed at valuation date ``V`` (an integer
quarter) when ``notif_period + j <= V``. No tail factor is applied.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.splice import SplicePortfolio


def paid_triangle(p: SplicePortfolio, V: int, claim_ids=None) -> np.ndarray:
    """Cumulative inflated paid, rows = notification periods 1..V, cols = dev 0..V-1.

    Unobserved cells are NaN. ``claim_ids`` restricts to a segment.
    """
    c = p.claims[p.claims["notif_time"] <= V]
    if claim_ids is not None:
        c = c[c["claim_no"].isin(claim_ids)]
    pay = p.payments.merge(c[["claim_no", "notif_period"]], on="claim_no")
    pay = pay[pay["payment_time"] <= V]
    pay["dev"] = pay["payment_period"] - pay["notif_period"]
    inc = np.zeros((V, V))
    np.add.at(inc, (pay["notif_period"].values - 1, pay["dev"].values), pay["payment_inflated"].values)
    cum = inc.cumsum(axis=1)
    r, j = np.indices((V, V))
    cum[(r + 1) + j > V] = np.nan
    return cum


MIN_ROWS = 5


def chain_ladder(tri: np.ndarray, min_rows: int = MIN_ROWS) -> dict:
    """Volume-weighted development factors and RBNS reserves by row.

    Factors estimated from fewer than ``min_rows`` rows are set to 1. Without
    this rule a single late payment in the oldest row can drive the whole
    reserve (e.g. f_34 = 1.43 from one row at V=36 inflated every row by 43%).
    The same rule is applied to every segment, so comparisons stay like for like.
    """
    n = tri.shape[0]
    f = np.ones(n - 1)
    for j in range(n - 1):
        rows = ~np.isnan(tri[:, j + 1])
        den = tri[rows, j].sum()
        if rows.sum() >= min_rows and den > 0:
            f[j] = tri[rows, j + 1].sum() / den
    latest = np.array([tri[i, n - 1 - i] for i in range(n)])
    cdf = np.array([np.prod(f[n - 1 - i:]) for i in range(n)])
    ult = latest * cdf
    return {"factors": f, "latest": latest, "cdf": cdf, "ultimate": ult, "reserve": ult - latest}


def segmented_reserve(p: SplicePortfolio, V: int, labels: pd.Series | None = None,
                      min_rows: int = MIN_ROWS) -> np.ndarray:
    """RBNS reserve by notification row; summed over segments if ``labels`` is given.

    ``labels`` is indexed by claim_no (claims reported by V).
    """
    if labels is None:
        return chain_ladder(paid_triangle(p, V), min_rows)["reserve"]
    total = np.zeros(V)
    for g in pd.unique(labels):
        ids = labels.index[labels == g]
        total += chain_ladder(paid_triangle(p, V, ids), min_rows)["reserve"]
    return total


def actual_future_by_row(p: SplicePortfolio, V: int) -> np.ndarray:
    c = p.claims[p.claims["notif_time"] <= V]
    pay = p.payments.merge(c[["claim_no", "notif_period"]], on="claim_no")
    fut = pay[pay["payment_time"] > V].groupby("notif_period")["payment_inflated"].sum()
    return fut.reindex(range(1, V + 1), fill_value=0.0).values


def reserve_errors(est: np.ndarray, act: np.ndarray) -> dict:
    """Total error and an aggregate row-level error, both relative to actual."""
    return {
        "estimate": est.sum(),
        "actual": act.sum(),
        "total_error_pct": 100 * (est.sum() - act.sum()) / act.sum(),
        "row_abs_error_pct": 100 * np.abs(est - act).sum() / act.sum(),
    }
