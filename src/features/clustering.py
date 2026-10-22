"""Clustering helpers used ahead of reserving.

All functions take a feature DataFrame (one row per claim, indexed by
claim_no), apply the transformation chosen in Phase 1 (log1p on skewed
amounts and delays, then standardisation) and return labels as a Series
indexed by claim_no, so labels can be passed directly to the reserving code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

# Columns that are skewed and non-negative: transformed with log1p before scaling
LOG_COLUMNS = {
    "notidel", "initial_case_estimate", "case_estimate", "paid_to_date",
    "incurred_to_date", "n_payments_to_date", "n_revisions_to_date",
    "time_since_last_payment", "age_since_notification",
    "initial_ce_rel", "paid_over_initial_ce", "ce_over_initial_ce",
}


def prepare(df: pd.DataFrame, columns: list[str]) -> np.ndarray:
    X = df[columns].astype(float).copy()
    for c in columns:
        if c in LOG_COLUMNS:
            X[c] = np.log1p(X[c])
    return StandardScaler().fit_transform(X.values)


def fit_kmeans_clusters(df: pd.DataFrame, n_clusters: int = 4, random_state: int = 42,
                        columns: list[str] | None = None):
    """K-means on prepared features. Returns (model, labels Series)."""
    columns = columns or list(df.columns)
    X = prepare(df, columns)
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    labels = model.fit_predict(X)
    return model, relabel_by(df, pd.Series(labels, index=df.index), columns[-1] if columns else None)


def fit_ward_clusters(df: pd.DataFrame, n_clusters: int = 4, columns: list[str] | None = None):
    """Agglomerative clustering with Ward linkage. Returns (model, labels Series)."""
    columns = columns or list(df.columns)
    X = prepare(df, columns)
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
    labels = model.fit_predict(X)
    return model, relabel_by(df, pd.Series(labels, index=df.index), columns[-1] if columns else None)


def relabel_by(df: pd.DataFrame, labels: pd.Series, col: str | None) -> pd.Series:
    """Renumber clusters 0..k-1 in increasing order of the median of ``col`` (for readability)."""
    if col is None or col not in df:
        return labels
    order = df[col].groupby(labels).median().sort_values().index
    return labels.map({old: new for new, old in enumerate(order)})


def silhouette_by_k(df: pd.DataFrame, columns: list[str], ks=range(2, 7), random_state: int = 42,
                    sample_size: int = 2000) -> pd.Series:
    X = prepare(df, columns)
    out = {}
    for k in ks:
        lab = KMeans(n_clusters=k, random_state=random_state, n_init=20).fit_predict(X)
        out[k] = silhouette_score(X, lab, sample_size=min(sample_size, len(X)), random_state=random_state)
    return pd.Series(out, name="silhouette")


def bootstrap_ari(df: pd.DataFrame, columns: list[str], k: int, n_boot: int = 30, seed: int = 0) -> np.ndarray:
    """Stability: refit K-means on bootstrap samples, compare labels of all claims with the full fit."""
    X = prepare(df, columns)
    ref = KMeans(n_clusters=k, random_state=42, n_init=20).fit(X)
    rng = np.random.default_rng(seed)
    aris = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(X), len(X))
        m = KMeans(n_clusters=k, random_state=int(rng.integers(1e6)), n_init=10).fit(X[idx])
        aris.append(adjusted_rand_score(ref.labels_, m.predict(X)))
    return np.array(aris)


def quantile_bands(s: pd.Series, k: int) -> pd.Series:
    """Rule-based actuarial alternative: k equal-count bands of one variable."""
    return pd.Series(pd.qcut(s.rank(method="first"), k, labels=False), index=s.index)


def internal_diagnostics(X: np.ndarray, labels) -> dict:
    """Silhouette (higher better), Calinski-Harabasz (higher), Davies-Bouldin (lower)."""
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score
    labels = np.asarray(labels)
    return {
        "silhouette": silhouette_score(X, labels),
        "calinski_harabasz": calinski_harabasz_score(X, labels),
        "davies_bouldin": davies_bouldin_score(X, labels),
        "smallest_cluster": int(np.bincount(labels).min()),
    }


def bootstrap_stability(X: np.ndarray, k: int, method: str = "kmeans", n_boot: int = 30, seed: int = 0) -> np.ndarray:
    """ARI between the full-data partition and partitions refitted on bootstrap samples.

    The comparison is made on the resampled claims themselves (full-data label
    of each drawn claim vs its label in the bootstrap fit), so no assignment
    rule for unseen points is needed and K-means and Ward are treated alike.
    """
    def fit(Z):
        if method == "kmeans":
            return KMeans(n_clusters=k, n_init=10, random_state=int(rng.integers(1e6))).fit_predict(Z)
        return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z)

    rng = np.random.default_rng(seed)
    ref = fit(X)
    out = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(X), len(X))
        out.append(adjusted_rand_score(ref[idx], fit(X[idx])))
    return np.array(out)
