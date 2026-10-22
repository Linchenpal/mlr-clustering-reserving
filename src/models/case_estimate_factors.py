"""Out-of-time test: segment-specific case-estimate adjustment factors for open claims.

At an earlier valuation date V0 we group the open claims and, using only data
available by a later date V1 = V0 + h, measure how their case estimates at V0
developed:

    emerged_i = paid_i(V0, V1] + OCL_i(V1)          (observable at V1)
    factor_g  = sum_{i in g} emerged_i / sum_{i in g} OCL_i(V0)

At V1 the open claims are assigned to the groups with the V0 rule (same
scaler, same centroids, same band edges) and the RBNS reserve is estimated as
sum_g factor_g * OCL(V1) over the claims in each group. The actual run-off
after V1 is used only to score the estimate.

The emerged amount still contains OCL(V1) for claims that are open at V1, so
the factor understates full development when case estimates are themselves
short. This bias is common to every grouping, including the single global
factor, so comparisons between groupings are like for like.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.data.splice import SplicePortfolio
from src.features.clustering import LOG_COLUMNS
from src.features.valuation import features_at_valuation, future_payments


def _transform(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = df[cols].astype(float).copy()
    for c in cols:
        if c in LOG_COLUMNS:
            X[c] = np.log1p(X[c])
    return X.values


class KMeansGrouper:
    """K-means fitted at V0 and applied unchanged at V1."""

    def __init__(self, cols: list[str], k: int, seed: int = 42):
        self.cols, self.k, self.seed = cols, k, seed

    def fit(self, df: pd.DataFrame) -> pd.Series:
        Z = _transform(df, self.cols)
        self.scaler = StandardScaler().fit(Z)
        self.km = KMeans(self.k, n_init=20, random_state=self.seed).fit(self.scaler.transform(Z))
        return pd.Series(self.km.labels_, index=df.index)

    def assign(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(self.km.predict(self.scaler.transform(_transform(df, self.cols))), index=df.index)


class BandGrouper:
    """Rule-based comparator: equal-count bands of one feature, edges fixed at V0."""

    def __init__(self, col: str, k: int):
        self.col, self.k = col, k

    def fit(self, df: pd.DataFrame) -> pd.Series:
        self.edges = np.quantile(df[self.col], np.linspace(0, 1, self.k + 1)[1:-1])
        return self.assign(df)

    def assign(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(np.searchsorted(self.edges, df[self.col].values, side="right"), index=df.index)


class SingleGroup:
    def fit(self, df):
        return pd.Series(0, index=df.index)

    def assign(self, df):
        return pd.Series(0, index=df.index)


def emerged_since(p: SplicePortfolio, ids: pd.Index, V0: float, V1: float) -> pd.Series:
    pay = p.payments
    window = pay[(pay["payment_time"] > V0) & (pay["payment_time"] <= V1) & pay["claim_no"].isin(ids)]
    paid = window.groupby("claim_no")["payment_inflated"].sum().reindex(ids, fill_value=0.0)
    inc = p.incurred[(p.incurred["txn_time"] <= V1) & p.incurred["claim_no"].isin(ids)]
    ocl_v1 = inc.groupby("claim_no")["OCL"].last().reindex(ids)
    return paid + ocl_v1


def run_oot(p: SplicePortfolio, V0: int, V1: int, grouper) -> dict:
    f0 = features_at_valuation(p, V0)
    open0 = f0[f0["is_open"] == 1]
    g0 = grouper.fit(open0)
    emerged = emerged_since(p, open0.index, V0, V1)
    factor = emerged.groupby(g0).sum() / open0["case_estimate"].groupby(g0).sum()

    f1 = features_at_valuation(p, V1)
    open1 = f1[f1["is_open"] == 1]
    g1 = grouper.assign(open1)
    est_claim = open1["case_estimate"] * g1.map(factor).fillna(1.0)
    actual_claim = future_payments(p, V1).loc[open1.index]
    est, act = est_claim.sum(), actual_claim.sum()
    # claim-level accuracy (log scale), to see whether groups help individual claims
    log_err = np.abs(np.log1p(est_claim) - np.log1p(actual_claim))
    return {
        "V0": V0, "V1": V1, "n_open_V0": len(open0), "n_open_V1": len(open1),
        "estimate": est, "actual": act, "total_error_pct": 100 * (est - act) / act,
        "median_abs_log_error": float(log_err.median()),
        "factors": factor.round(3).to_dict(),
        "groups_V1": g1.value_counts().sort_index().to_dict(),
    }
