"""Checks that valuation-date features do not look past V and that the triangle reconciles.

Run from the repo root:  python -m pytest tests -q
"""

import numpy as np
import pytest

from src.data.splice import load_splice
from src.features.valuation import LEAKY_COLUMNS, features_at_notification, features_at_valuation
from src.models.chain_ladder import paid_triangle


@pytest.fixture(scope="module")
def portfolio():
    return load_splice("complexity_5")


def test_no_leaky_columns(portfolio):
    for df in (features_at_valuation(portfolio, 40), features_at_notification(portfolio, 40)):
        assert not LEAKY_COLUMNS & set(df.columns)


def test_features_unchanged_by_future_data(portfolio):
    """Deleting every transaction after V must not change the features at V."""
    V = 30
    before = features_at_valuation(portfolio, V)
    cut = load_splice("complexity_5")
    cut.payments = cut.payments[cut.payments["payment_time"] <= V]
    cut.incurred = cut.incurred[cut.incurred["txn_time"] <= V]
    after = features_at_valuation(cut, V)
    assert np.allclose(before.values, after.values, equal_nan=True)


def test_triangle_latest_diagonal_equals_paid_to_date(portfolio):
    V = 40
    tri = paid_triangle(portfolio, V)
    latest = np.nansum([tri[i, V - 1 - i] for i in range(V)])
    assert np.isclose(latest, features_at_valuation(portfolio, V)["paid_to_date"].sum())


def test_open_flag_matches_settlement(portfolio):
    V = 40
    fv = features_at_valuation(portfolio, V)
    settle = portfolio.claims.set_index("claim_no").loc[fv.index, "settle_time"]
    assert ((settle > V).astype(int) == fv["is_open"]).all()


def test_oot_factors_use_no_data_after_V1(portfolio):
    """Factors fitted at V0 may use data up to V1 only: deleting later data must not change the estimate."""
    from src.models.case_estimate_factors import KMeansGrouper, run_oot
    cols = ["notidel", "age_since_notification", "initial_ce_rel", "paid_over_initial_ce", "ce_over_initial_ce"]
    V0, V1 = 24, 32
    full = run_oot(portfolio, V0, V1, KMeansGrouper(cols, 3))
    cut = load_splice("complexity_5")
    cut.payments = cut.payments[cut.payments["payment_time"] <= V1]
    cut.incurred = cut.incurred[cut.incurred["txn_time"] <= V1]
    trunc = run_oot(cut, V0, V1, KMeansGrouper(cols, 3))
    assert np.isclose(full["estimate"], trunc["estimate"])
    assert full["factors"] == trunc["factors"]


def test_glm_and_large_claims_use_no_data_after_V(portfolio):
    """Group-use estimators at V must not change when data after V is deleted."""
    from src.models.group_uses import glm_reserve, large_separately
    V = 32
    cut = load_splice("complexity_5")
    cut.payments = cut.payments[cut.payments["payment_time"] <= V]
    cut.incurred = cut.incurred[cut.incurred["txn_time"] <= V]
    assert np.isclose(glm_reserve(portfolio, V, speed_trend=True), glm_reserve(cut, V, speed_trend=True))
    ids = portfolio.claims["claim_no"].iloc[::7]
    assert np.allclose(large_separately(portfolio, V, ids), large_separately(cut, V, ids))


def test_covariate_labels_join_published_cov_portfolio():
    """Labels exported by scripts/export_splice_cov_labels.R cover every claim of the published _cov files."""
    from src.data.splice import validate
    p = load_splice("complexity_5", "_cov")
    assert p.covariates is not None
    assert len(p.covariates) == len(p.claims)
    assert (p.covariates["claim_no"].values == p.claims["claim_no"].values).all()
    v = validate(p)
    assert all(v[k] for k in ("payment_count_matches", "first_txn_at_notification",
                              "last_txn_at_settlement", "final_cumpaid_equals_inflated_payments"))
    # unrepresented claims occur only at injury severity 1 (test_covariates_obj design)
    cov = p.covariates
    assert set(cov.loc[cov["legal_rep"] == "N", "injury_severity"]) == {1}
