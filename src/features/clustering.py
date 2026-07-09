"""
Clustering as a feature-engineering step ahead of reserving.

Placeholder module — implement clustering approaches here (e.g. K-means on
claim/portfolio development characteristics) so they can be reused from
notebooks and from src/models/.
"""

from __future__ import annotations

import pandas as pd


def fit_kmeans_clusters(df: pd.DataFrame, n_clusters: int = 4, random_state: int = 42):
    """Fit K-means and return cluster labels.

    Placeholder signature — flesh out with real feature columns once the
    dataset is confirmed.
    """
    from sklearn.cluster import KMeans

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init="auto")
    labels = model.fit_predict(df)
    return model, labels
