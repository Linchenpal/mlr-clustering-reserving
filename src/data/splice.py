"""Load a SPLICE portfolio (claims, payments, incurred, optional covariates).

Time is measured in quarters. A claim occurs at ``occurrence_time``, is
notified at ``occurrence_time + notidel`` and settles at
``occurrence_time + notidel + setldel`` (the time of its final payment).

Monetary conventions (important for reserving):

* ``claim_size`` in the claim table is in constant (time-0) money.
* ``payment_inflated`` is the cash actually paid, including base and
  superimposed inflation. ``cumpaid`` in the incurred table is the running sum
  of ``payment_inflated``. All reserving quantities in this project therefore
  use ``payment_inflated``. In Complexity 5 total inflated payments are 1.83
  times total claim size (3.7 times on average per claim, because small claims
  carry the most superimposed inflation).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SPLICE_DIR = REPO_ROOT / "data" / "raw" / "splice"


@dataclass
class SplicePortfolio:
    claims: pd.DataFrame
    payments: pd.DataFrame
    incurred: pd.DataFrame
    covariates: Optional[pd.DataFrame] = None
    name: str = ""


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])


def load_splice(folder: str = "complexity_5", suffix: str = "", complexity: int = 5) -> SplicePortfolio:
    """Load one portfolio.

    Examples
    --------
    >>> load_splice("complexity_5")                      # standard portfolio
    >>> load_splice("complexity_5_cov_regen", "_cov")    # regenerated, with covariates
    """
    d = SPLICE_DIR / folder
    claims = _read(d / f"claim_{complexity}{suffix}.csv")
    payments = _read(d / f"payment_{complexity}{suffix}.csv")
    incurred = _read(d / f"incurred_{complexity}{suffix}.csv")

    claims["notif_time"] = claims["occurrence_time"] + claims["notidel"]
    claims["settle_time"] = claims["notif_time"] + claims["setldel"]
    claims["notif_period"] = np.ceil(claims["notif_time"]).astype(int)

    cov = None
    cov_path = d / f"covariates_{complexity}{suffix}.csv"
    if cov_path.exists():
        cov = pd.read_csv(cov_path)
        cov["injury_severity"] = cov["injury_severity"].astype(int)
    return SplicePortfolio(claims, payments, incurred, cov, name=f"{folder}{suffix}")


def validate(p: SplicePortfolio) -> dict:
    """Relational checks used in Phase 1, extended to the incurred table."""
    c = p.claims.set_index("claim_no")
    n_pay = p.payments.groupby("claim_no").size().reindex(c.index, fill_value=0)
    first = p.incurred.groupby("claim_no").first()
    last = p.incurred.groupby("claim_no").last()
    paid = p.payments.groupby("claim_no")["payment_inflated"].sum()
    return {
        "n_claims": len(c),
        "payment_count_matches": bool((n_pay == c["no_payment"]).all()),
        "first_txn_at_notification": bool(np.allclose(first["txn_time"], c["notif_time"])),
        "last_txn_at_settlement": bool(np.allclose(last["txn_time"], c["settle_time"])),
        "final_cumpaid_equals_inflated_payments": bool(np.allclose(last["cumpaid"], paid)),
        "covariates_present": p.covariates is not None,
    }
