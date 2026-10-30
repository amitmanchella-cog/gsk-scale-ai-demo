"""territory_hcps / hcp_view on the repo parquet data and on a small synthetic fixture."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from navigator_app.data import load_tables
from navigator_app.scoring import ScoringRules
from navigator_app.views import VIEW_COLUMNS, hcp_view, territory_hcps, to_records

CHLOE_XU_REASON = "Segment A (+40), 60 days since last visit (+40, capped), 1 open follow-up (+20)"


@pytest.fixture(scope="module")
def store():
    return load_tables()


@pytest.fixture(scope="module")
def t001(store):
    return territory_hcps(store, "T001")


def test_t001_has_64_rows_with_view_columns(store, t001):
    assert list(t001.columns) == VIEW_COLUMNS
    assert len(t001) == 64
    assert t001["hcp_id"].is_unique
    assert (t001["territory_id"] == "T001").all()
    assert (t001["segment"] == "A").sum() == 15
    assert store.as_of == date(2025, 9, 29)


def test_sorted_by_score_desc_then_name_asc(t001):
    keys = list(zip(-t001["score"], t001["hcp_name"]))
    assert keys == sorted(keys)
    assert t001["score"].iloc[0] == 100
    assert t001["score"].iloc[-1] == 0


def test_never_visited_rows(t001):
    never = t001[t001["days_since_last_visit"].isna()]
    assert len(never) == 4
    for record in to_records(never):
        assert record["days_since_last_visit"] is None
        assert record["last_visit_date"] is None
        assert "never visited (+40, capped)" in record["reason"]
        assert record["factors"][1]["points"] == 40


def test_recent_visit_scores_zero_on_repo_data(store):
    row = hcp_view(store, "H00011")
    assert row["hcp_name"] == "Dr Rhea Okafor"
    assert row["territory_id"] == "T001"
    assert row["days_since_last_visit"] == 5
    assert row["score"] == 0
    assert row["reason"] == "Visited 5 days ago (within 7 days)"


def test_hcp_view_dr_chloe_xu(store):
    row = hcp_view(store, "H00052")
    assert row["hcp_name"] == "Dr Chloe Xu"
    assert row["specialty"] == "Pulmonology"
    assert row["segment"] == "A"
    assert row["last_visit_date"] == date(2025, 7, 31)
    assert row["days_since_last_visit"] == 60
    assert row["open_follow_ups"] == 1
    assert row["score"] == 100
    assert row["reason"] == CHLOE_XU_REASON
    assert row["factors"] == [
        {"name": "segment", "points": 40, "detail": "Segment A"},
        {"name": "days_since_last_visit", "points": 40, "detail": "60 days since last visit (capped)"},
        {"name": "open_follow_up", "points": 20, "detail": "1 open follow-up"},
    ]
    assert row["territory_id"] == store["hcps"].set_index("hcp_id").loc["H00052", "territory_id"]


def test_hcp_view_unknown_hcp(store):
    assert hcp_view(store, "H99999") is None


def test_open_follow_up_counts_match_source(store, t001):
    follow_ups = store["follow_ups"]
    expected = follow_ups[follow_ups["status"] == "open"].groupby("hcp_id").size()
    for hcp_id, count in zip(t001["hcp_id"], t001["open_follow_ups"]):
        assert count == int(expected.get(hcp_id, 0))


def test_as_of_and_rules_parameters(store):
    earlier = territory_hcps(store, "T001", as_of=date(2025, 8, 1))
    row = to_records(earlier[earlier["hcp_id"] == "H00011"])[0]
    assert row["days_since_last_visit"] is None  # H00011's visits all fall after 2025-08-01, so none count
    assert (earlier["days_since_last_visit"].dropna() >= 0).all()
    custom = territory_hcps(store, "T001", rules=ScoringRules(segment_weights={"A": 0, "B": 0, "C": 0}))
    assert custom["score"].max() == 60  # 40 cap + 20 bonus, no segment points


def test_to_records_is_json_safe(t001):
    records = to_records(t001.head(3))
    assert len(records) == 3
    assert all(type(record["score"]) is int and type(record["open_follow_ups"]) is int for record in records)
    assert all(isinstance(record["factors"], list) for record in records)


def _write_fixture(directory: Path) -> None:
    pd.DataFrame(
        {
            "hcp_id": ["H1", "H2", "H3", "H4", "H5", "H6"],
            "hcp_name": ["Dr One", "Dr Two", "Dr Three", "Dr Four", "Dr Five", "Dr Six"],
            "specialty": ["GP"] * 6,
            "segment": ["A", "B", "C", "A", "B", "C"],
            "territory_id": ["TX", "TX", "TX", "TX", "TX", "TY"],
        }
    ).to_parquet(directory / "hcps.parquet")
    pd.DataFrame(
        {
            "visit_id": ["V1", "V2", "V3", "V4", "V5"],
            "hcp_id": ["H1", "H1", "H2", "H4", "H4"],
            "rep_id": ["R1"] * 5,
            "territory_id": ["TX"] * 5,
            "visit_date": [date(2025, 1, 1), date(2025, 2, 14), date(2025, 2, 27), date(2025, 1, 20), date(2025, 3, 5)],
            "channel": ["phone"] * 5,
            "duration_min": [30] * 5,
            "product": ["P"] * 5,
        }
    ).to_parquet(directory / "visits.parquet")
    pd.DataFrame(
        {
            "follow_up_id": ["F1", "F2", "F3", "F4"],
            "visit_id": ["V1", "V2", "V3", "V5"],
            "hcp_id": ["H1", "H1", "H2", "H4"],
            "rep_id": ["R1"] * 4,
            "due_date": [date(2025, 3, 1)] * 4,
            "status": ["open", "open", "done", "open"],
            "note": ["n"] * 4,
        }
    ).to_parquet(directory / "follow_ups.parquet")
    reps = {"rep_id": ["R1"], "rep_name": ["Rep"], "territory_id": ["TX"], "hire_date": [date(2024, 1, 1)]}
    pd.DataFrame(reps).to_parquet(directory / "reps.parquet")
    pd.DataFrame({"territory_id": ["TX", "TY"], "territory_name": ["X", "Y"], "region": ["N", "N"]}).to_parquet(
        directory / "territories.parquet"
    )
    pd.DataFrame({"territory_id": ["TX"], "week": [1], "sales": [1.0]}).to_parquet(directory / "weekly_sales.parquet")


def test_joins_on_small_fixture(tmp_path):
    _write_fixture(tmp_path)
    store = load_tables(tmp_path, as_of=date(2025, 3, 1))
    df = territory_hcps(store, "TX")
    assert list(df["hcp_id"]) == ["H4", "H1", "H5", "H3", "H2"]  # TY's H6 excluded; sorted by score desc
    by_id = {record["hcp_id"]: record for record in to_records(df)}
    assert by_id["H1"]["last_visit_date"] == date(2025, 2, 14)  # max of two visits
    assert by_id["H1"]["days_since_last_visit"] == 15
    assert by_id["H1"]["open_follow_ups"] == 2  # two open follow-ups count once (+20)
    assert by_id["H1"]["score"] == 40 + 15 + 20
    assert by_id["H2"]["open_follow_ups"] == 0  # a "done" follow-up is not counted
    assert by_id["H2"]["score"] == 0  # visited 2 days before as_of
    assert by_id["H3"]["days_since_last_visit"] is None
    assert by_id["H3"]["score"] == 10 + 40
    assert by_id["H4"]["last_visit_date"] == date(2025, 1, 20)  # the 2025-03-05 visit is after as_of
    assert by_id["H4"]["score"] == 40 + 40 + 20
    assert by_id["H5"]["score"] == 25 + 40


def test_default_rules_come_from_deps(store):
    """Without an explicit ``rules`` argument the view uses the rules in effect (``deps.get_rules``)."""
    from navigator_app.deps import set_rules

    set_rules(ScoringRules(segment_weights={"A": 50, "B": 25, "C": 10}))
    try:
        row = to_records(territory_hcps(store, "T001").pipe(lambda df: df[df["hcp_id"] == "H00733"]))[0]
    finally:
        set_rules(None)
    assert row["factors"][0] == {"name": "segment", "points": 50, "detail": "Segment A"}
