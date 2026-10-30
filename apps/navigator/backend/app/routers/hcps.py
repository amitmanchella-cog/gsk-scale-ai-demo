"""Territory HCP list for a rep, with filters and name search (S1, AC1)."""

from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_rules, get_store
from ..models import HcpListResponse, HcpView, RepSummary, Territory
from ..views import territory_hcps, to_records

router = APIRouter(tags=["hcps"])

SEGMENTS = ("A", "B", "C")


def apply_filters(
    df: pd.DataFrame,
    specialty: str | None = None,
    segment: str | None = None,
    min_days_since_last_visit: int | None = None,
    q: str | None = None,
) -> pd.DataFrame:
    """AND together the optional filters; never-visited rows (days NA) satisfy any ``min_days_since_last_visit``."""
    mask = pd.Series(True, index=df.index)
    if specialty:
        mask &= df["specialty"] == specialty
    if segment:
        mask &= df["segment"] == segment
    if min_days_since_last_visit is not None:
        days = df["days_since_last_visit"]
        mask &= days.isna() | (days >= min_days_since_last_visit).fillna(False)
    if q:
        mask &= df["hcp_name"].str.contains(q, case=False, regex=False)
    return df.loc[mask]


@router.get("/reps/{rep_id}/hcps", response_model=HcpListResponse)
def list_rep_hcps(
    rep_id: str,
    specialty: str | None = Query(None, description="Exact specialty, e.g. GP"),
    segment: str | None = Query(None, pattern="^[ABC]$", description="A, B or C"),
    min_days_since_last_visit: int | None = Query(None, ge=0, description="Never-visited HCPs match any value"),
    q: str | None = Query(None, description="Case-insensitive substring of hcp_name"),
    as_of: date | None = Query(None, description="Override the store's as-of date (YYYY-MM-DD)"),
) -> HcpListResponse:
    store = get_store()
    reps = store["reps"]
    rep_rows = reps.loc[reps["rep_id"] == rep_id]
    if rep_rows.empty:
        raise HTTPException(status_code=404, detail=f"unknown rep {rep_id!r}")
    rep = rep_rows.iloc[0]
    territories = store["territories"]
    territory = territories.loc[territories["territory_id"] == rep["territory_id"]].iloc[0]

    effective_as_of = as_of or store.as_of
    df = territory_hcps(store, rep["territory_id"], as_of=effective_as_of, rules=get_rules())
    df = apply_filters(df, specialty, segment, min_days_since_last_visit, q)
    hcps = [HcpView(**record) for record in to_records(df)]
    return HcpListResponse(
        rep=RepSummary(rep_id=rep["rep_id"], rep_name=rep["rep_name"], territory_id=rep["territory_id"]),
        territory=Territory(
            territory_id=territory["territory_id"],
            territory_name=territory["territory_name"],
            region=territory["region"],
        ),
        as_of=effective_as_of,
        count=len(hcps),
        hcps=hcps,
    )
