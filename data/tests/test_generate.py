from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1]
TABLES = ["territories", "reps", "hcps", "visits", "follow_ups", "weekly_sales"]


@pytest.mark.parametrize("name", TABLES)
def test_table_exists_and_non_empty(name):
    df = pd.read_parquet(DATA / f"{name}.parquet")
    assert len(df) > 0


def test_total_rows_about_10k():
    total = sum(len(pd.read_parquet(DATA / f"{n}.parquet")) for n in TABLES)
    assert 9000 <= total <= 11000, total


def test_referential_integrity():
    terr = set(pd.read_parquet(DATA / "territories.parquet").territory_id)
    hcps = pd.read_parquet(DATA / "hcps.parquet")
    visits = pd.read_parquet(DATA / "visits.parquet")
    reps = pd.read_parquet(DATA / "reps.parquet")
    assert set(hcps.territory_id) <= terr
    assert set(visits.hcp_id) <= set(hcps.hcp_id)
    assert set(visits.rep_id) <= set(reps.rep_id)
    assert hcps.hcp_id.is_unique and visits.visit_id.is_unique


def test_generator_is_deterministic(tmp_path):
    import sys

    sys.path.insert(0, str(DATA))
    from generate import generate

    a = generate(tmp_path / "a")["visits"]
    b = generate(tmp_path / "b")["visits"]
    pd.testing.assert_frame_equal(a, b)
