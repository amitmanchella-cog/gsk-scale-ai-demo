import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pyspark.sql import SparkSession  # noqa: E402


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.appName("territory_kpis_tests")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture
def make_df(spark):
    """Build a DataFrame from a list of dicts with an explicit DDL schema (keeps types deterministic)."""

    def _make(rows, schema: str):
        return spark.createDataFrame([tuple(r[c.split()[0]] for c in schema.split(", ")) for r in rows], schema)

    return _make


MONDAY = date(2025, 9, 1)
TUESDAY = date(2025, 9, 2)
SUNDAY = date(2025, 9, 7)
NEXT_MONDAY = date(2025, 9, 8)


def visit(visit_id, territory_id="T001", hcp_id="H1", channel="face_to_face", visit_date=MONDAY, duration=20):
    return {
        "visit_id": visit_id,
        "hcp_id": hcp_id,
        "rep_id": "R1",
        "territory_id": territory_id,
        "visit_date": visit_date,
        "channel": channel,
        "duration_min": duration,
    }


VISIT_SCHEMA = (
    "visit_id string, hcp_id string, rep_id string, territory_id string, visit_date date, "
    "channel string, duration_min long"
)
FOLLOW_UP_SCHEMA = "follow_up_id string, rep_id string, due_date date, status string"
REP_SCHEMA = "rep_id string, territory_id string"
SALES_SCHEMA = "territory_id string, week date, product string, units long, revenue_gbp double"
TERRITORY_SCHEMA = "territory_id string, region string"
