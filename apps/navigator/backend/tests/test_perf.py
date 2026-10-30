"""S5.3 / NFR-3: ``GET /reps/{rep_id}/hcps`` answers in < 1 s for a territory of 300 HCPs (p95 of 5 calls)."""

import time
from datetime import date, timedelta

import pandas as pd
from navigator_app.data import TABLES, load_tables
from navigator_app.deps import get_store, set_store

TERRITORY = "T900"
REP = "R900"
HCP_COUNT = 300
SPECIALTIES = ("Cardiology", "Endocrinology", "Pulmonology", "Oncology", "GP", "Neurology")


def write_synthetic_territory(data_dir, as_of: date, hcp_count: int = HCP_COUNT) -> None:
    """Write the six curated tables for one invented territory with ``hcp_count`` HCPs (same schema as data/)."""
    hcps = pd.DataFrame(
        {
            "hcp_id": [f"P{i:05d}" for i in range(hcp_count)],
            "hcp_name": [f"Dr Perf {i:03d}" for i in range(hcp_count)],
            "specialty": [SPECIALTIES[i % len(SPECIALTIES)] for i in range(hcp_count)],
            "segment": ["ABC"[i % 3] for i in range(hcp_count)],
            "territory_id": TERRITORY,
        }
    )
    visited = hcps.iloc[: int(hcp_count * 0.9)]
    visits = pd.DataFrame(
        {
            "visit_id": [f"V{i:06d}" for i in range(len(visited) * 3)],
            "hcp_id": visited["hcp_id"].tolist() * 3,
            "rep_id": REP,
            "territory_id": TERRITORY,
            "visit_date": [as_of - timedelta(days=(i * 7) % 180 + 1) for i in range(len(visited) * 3)],
            "channel": "f2f",
            "duration_min": 30,
            "product": "Zentrava",
        }
    )
    follow_ups = pd.DataFrame(
        {
            "follow_up_id": [f"F{i:05d}" for i in range(hcp_count)],
            "visit_id": visits["visit_id"].iloc[:hcp_count].tolist(),
            "hcp_id": hcps["hcp_id"],
            "rep_id": REP,
            "due_date": as_of + timedelta(days=7),
            "status": ["open" if i % 2 else "done" for i in range(hcp_count)],
            "note": "Send samples",
        }
    )
    reps = pd.DataFrame(
        {"rep_id": [REP], "rep_name": ["Perf Rep"], "territory_id": [TERRITORY], "hire_date": [date(2020, 1, 1)]}
    )
    territories = pd.DataFrame({"territory_id": [TERRITORY], "territory_name": ["Perf-01"], "region": ["North"]})
    weekly_sales = pd.DataFrame(
        {"territory_id": [TERRITORY], "week": [as_of], "product": ["Zentrava"], "units": [1], "revenue_gbp": [1.0]}
    )
    tables = dict(zip(TABLES, (hcps, visits, follow_ups, reps, territories, weekly_sales)))
    for name, frame in tables.items():
        frame.to_parquet(data_dir / f"{name}.parquet", engine="pyarrow", index=False)


def test_300_hcps_under_1s(client, tmp_path, record_property):
    as_of = date(2025, 9, 29)
    write_synthetic_territory(tmp_path, as_of)
    previous = get_store()
    set_store(load_tables(tmp_path, as_of=as_of))
    try:
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            r = client.get(f"/reps/{REP}/hcps")
            timings.append(time.perf_counter() - start)
            assert r.status_code == 200
            assert r.json()["count"] == HCP_COUNT
    finally:
        set_store(previous)

    p95 = sorted(timings)[int(round(0.95 * (len(timings) - 1)))]
    record_property("p95_seconds", round(p95, 4))
    record_property("max_seconds", round(max(timings), 4))
    print(f"\n300-HCP /reps/{REP}/hcps timings: {[round(t, 4) for t in timings]} s, p95={p95:.4f}s")
    assert p95 < 1.0, f"p95 {p95:.3f}s >= 1 s (timings: {timings})"
    assert client.get("/reps/R001/hcps").json()["count"] == 64
