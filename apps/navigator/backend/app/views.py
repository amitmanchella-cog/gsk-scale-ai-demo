"""Enriched HCP view shared by the HCP list (S1) and the plan builder (S3).

``territory_hcps`` joins ``hcps`` with the latest visit per HCP and the count of open follow-ups, then applies
``score_hcp`` row-wise. All joins are vectorised; 300 HCPs take well under a second.
"""

from datetime import date

import pandas as pd

from .data import DataStore
from .scoring import ScoringRules, score_hcp

VIEW_COLUMNS = [
    "hcp_id",
    "hcp_name",
    "specialty",
    "segment",
    "territory_id",
    "last_visit_date",
    "days_since_last_visit",
    "open_follow_ups",
    "score",
    "reason",
    "factors",
]


def _last_visit_by_hcp(visits: pd.DataFrame, as_of: date) -> pd.Series:
    visit_dates = pd.to_datetime(visits["visit_date"])
    on_or_before = visits.loc[visit_dates <= pd.Timestamp(as_of), ["hcp_id"]].assign(visit_date=visit_dates)
    return on_or_before.groupby("hcp_id")["visit_date"].max()


def _open_follow_ups_by_hcp(follow_ups: pd.DataFrame) -> pd.Series:
    return follow_ups.loc[follow_ups["status"] == "open"].groupby("hcp_id").size()


def territory_hcps(
    store: DataStore,
    territory_id: str,
    as_of: date | None = None,
    rules: ScoringRules | None = None,
) -> pd.DataFrame:
    """One row per HCP in ``territory_id`` with :data:`VIEW_COLUMNS`, sorted by score desc then hcp_name asc."""
    as_of = as_of or store.as_of
    rules = rules or ScoringRules()
    hcps = store["hcps"]
    df = hcps.loc[hcps["territory_id"] == territory_id, ["hcp_id", "hcp_name", "specialty", "segment", "territory_id"]]
    df = df.copy()

    last_visit = _last_visit_by_hcp(store["visits"], as_of)
    df["last_visit_ts"] = df["hcp_id"].map(last_visit)
    df["last_visit_date"] = df["last_visit_ts"].dt.date.astype(object).where(df["last_visit_ts"].notna(), None)
    df["days_since_last_visit"] = (pd.Timestamp(as_of) - df["last_visit_ts"]).dt.days.astype("Int64")
    df["open_follow_ups"] = df["hcp_id"].map(_open_follow_ups_by_hcp(store["follow_ups"])).fillna(0).astype(int)

    results = [
        score_hcp(segment, None if pd.isna(days) else int(days), int(open_count), rules)
        for segment, days, open_count in zip(df["segment"], df["days_since_last_visit"], df["open_follow_ups"])
    ]
    df["score"] = [result.score for result in results]
    df["reason"] = [result.reason for result in results]
    df["factors"] = [[vars(factor) for factor in result.factors] for result in results]

    df = df.sort_values(["score", "hcp_name"], ascending=[False, True], kind="mergesort")
    return df[VIEW_COLUMNS].reset_index(drop=True)


def to_records(df: pd.DataFrame) -> list[dict]:
    """View rows as JSON-safe dicts (``None`` instead of ``NA``, plain ``int`` instead of numpy ints)."""
    records = []
    for row in df.itertuples(index=False):
        record = row._asdict()
        days = record["days_since_last_visit"]
        record["days_since_last_visit"] = None if pd.isna(days) else int(days)
        record["open_follow_ups"] = int(record["open_follow_ups"])
        record["score"] = int(record["score"])
        records.append(record)
    return records


def hcp_view(
    store: DataStore,
    hcp_id: str,
    as_of: date | None = None,
    rules: ScoringRules | None = None,
) -> dict | None:
    """Single enriched HCP row as a dict, or ``None`` when the HCP does not exist."""
    hcps = store["hcps"]
    match = hcps.loc[hcps["hcp_id"] == hcp_id, "territory_id"]
    if match.empty:
        return None
    df = territory_hcps(store, match.iloc[0], as_of=as_of, rules=rules)
    return to_records(df.loc[df["hcp_id"] == hcp_id])[0]
