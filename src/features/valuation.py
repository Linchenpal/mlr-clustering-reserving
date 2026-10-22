"""Claim features that respect information availability.

Two feature sets are provided:

``features_at_notification``
    Known at the moment a claim is reported, for every reported claim.
    Because they are measured at the same development age for every cohort,
    a cluster label built from them means the same thing in old and recent
    notification periods, so it can be used to segment a triangle.

``features_at_valuation``
    Everything observable at a calendar valuation date ``V`` (Lina's list):
    claim age, payments and case-estimate history cut off at ``V``.
    Useful for open-claim analysis at ``V``; *not* suitable for segmenting a
    triangle, because the same feature means different things for a claim
    reported 2 quarters ago and one reported 30 quarters ago.

No function here uses ``claim_size``, ``setldel`` or ``no_payment``, and no
"proportion paid" is formed with the ultimate as denominator.
``future_payments`` is the only function that looks beyond ``V`` and is meant
for evaluation only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.splice import SplicePortfolio

LEAKY_COLUMNS = {"claim_size", "setldel", "no_payment", "settle_time"}


def _add_covariates(df: pd.DataFrame, p: SplicePortfolio) -> pd.DataFrame:
    if p.covariates is None:
        return df
    cov = p.covariates.set_index("claim_no")
    age_order = {"0-15": 0, "15-30": 1, "30-50": 2, "50-65": 3, "over 65": 4}
    out = df.join(cov[["injury_severity"]], how="left")
    out["legal_rep_no"] = (cov["legal_rep"] == "N").astype(int).reindex(out.index)
    out["claimant_age_band"] = cov["claimant_age"].map(age_order).reindex(out.index)
    return out


def reported_by(p: SplicePortfolio, V: float) -> pd.Index:
    c = p.claims
    return pd.Index(c.loc[c["notif_time"] <= V, "claim_no"])


def features_at_notification(p: SplicePortfolio, V: float | None = None) -> pd.DataFrame:
    """One row per claim reported by ``V`` (all claims if ``V`` is None)."""
    c = p.claims.set_index("claim_no")
    if V is not None:
        c = c[c["notif_time"] <= V]
    first = p.incurred.groupby("claim_no").first()  # the 'Ma' transaction at notification
    out = pd.DataFrame(index=c.index)
    out["notif_period"] = c["notif_period"]
    out["occurrence_period"] = c["occurrence_period"]
    out["notidel"] = c["notidel"]
    out["initial_case_estimate"] = first["OCL"].reindex(c.index)
    out["initial_ce_rel"] = relative_to_period(out["initial_case_estimate"], out["notif_period"])
    return _add_covariates(out, p)


def relative_to_period(amount: pd.Series, period: pd.Series) -> pd.Series:
    """Amount divided by the median amount of claims notified in the same period.

    Removes the drift caused by inflation (the nominal initial case estimate
    roughly doubles between notification periods 1-10 and 31-40), using only
    claims already notified, so it is available at the valuation date. It also
    removes any genuine change in severity mix between periods, which is a
    deliberate trade-off.
    """
    return amount / amount.groupby(period).transform("median")


def features_at_valuation(p: SplicePortfolio, V: float) -> pd.DataFrame:
    """One row per claim reported by ``V``, using only transactions at or before ``V``."""
    c = p.claims.set_index("claim_no")
    c = c[c["notif_time"] <= V]
    inc = p.incurred[(p.incurred["txn_time"] <= V) & p.incurred["claim_no"].isin(c.index)]
    pay = p.payments[(p.payments["payment_time"] <= V) & p.payments["claim_no"].isin(c.index)]

    g_inc = inc.groupby("claim_no")
    g_pay = pay.groupby("claim_no")
    last_inc = g_inc.last()
    # Case-estimate revisions: transactions of type Ma/Mi/PMa/PMi, excluding the
    # initial estimate set at notification (the first transaction of each claim).
    is_first = ~inc.duplicated("claim_no")
    rev = inc[inc["txn_type"].str.contains("M") & ~is_first]
    log_mult = np.log(rev["multiplier"].clip(lower=1e-9))

    out = pd.DataFrame(index=c.index)
    out["notif_period"] = c["notif_period"]
    out["notidel"] = c["notidel"]
    out["age_since_notification"] = V - c["notif_time"]
    out["paid_to_date"] = g_pay["payment_inflated"].sum().reindex(c.index, fill_value=0.0)
    out["n_payments_to_date"] = g_pay.size().reindex(c.index, fill_value=0)
    last_event = g_pay["payment_time"].max().reindex(c.index).fillna(c["notif_time"])
    out["time_since_last_payment"] = V - last_event
    out["case_estimate"] = last_inc["OCL"].reindex(c.index)
    out["incurred_to_date"] = last_inc["incurred"].reindex(c.index)
    out["initial_case_estimate"] = g_inc["OCL"].first().reindex(c.index)
    out["n_revisions_to_date"] = rev.groupby("claim_no").size().reindex(c.index, fill_value=0)
    out["max_abs_log_revision"] = log_mult.abs().groupby(rev["claim_no"]).max().reindex(c.index, fill_value=0.0)
    out["is_open"] = (out["case_estimate"] > 0).astype(int)
    # Scale-free versions of the monetary features (see relative_to_period)
    out["initial_ce_rel"] = relative_to_period(out["initial_case_estimate"], out["notif_period"])
    out["paid_over_initial_ce"] = out["paid_to_date"] / out["initial_case_estimate"]
    out["ce_over_initial_ce"] = out["case_estimate"] / out["initial_case_estimate"]
    assert not LEAKY_COLUMNS & set(out.columns)
    return _add_covariates(out, p)


def future_payments(p: SplicePortfolio, V: float) -> pd.Series:
    """Inflated payments after ``V`` per claim reported by ``V``. Evaluation only."""
    ids = reported_by(p, V)
    pay = p.payments
    fut = pay[(pay["payment_time"] > V) & pay["claim_no"].isin(ids)]
    return fut.groupby("claim_no")["payment_inflated"].sum().reindex(ids, fill_value=0.0)
