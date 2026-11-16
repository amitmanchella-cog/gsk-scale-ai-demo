"""PySpark transform tests on a small synthetic fixture (local SparkSession, no network)."""

from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

import pytest
from pyspark.sql import DataFrame, Row, SparkSession

from pda_data import DATASET_VERSION
from pda_data.job import assert_no_person_level_columns, run
from pda_data.schema import RECRUITING_COLUMNS, TRIAL_FEATURE_COLUMNS
from pda_data.transform import build_recruiting_trials, build_trial_features, deduplicate, flatten

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def features(raw: DataFrame) -> dict[str, Row]:
    return {row["nct_id"]: row for row in build_trial_features(raw).collect()}


def test_one_row_per_trial_and_cleaning_rules(features: dict[str, Row]) -> None:
    # 05 no enrollment, 06 no completion date, 07 negative duration, 08 phase 1, 10 observational,
    # 11/12 recruiting -> all dropped; the duplicate of 02 collapses to one row.
    assert sorted(features) == ["SYN00000001", "SYN00000002", "SYN00000003", "SYN00000004", "SYN00000009"]


def test_output_columns_match_contract(raw: DataFrame) -> None:
    assert build_trial_features(raw).columns == TRIAL_FEATURE_COLUMNS


def test_duplicate_resolves_to_indication_in_conditions(raw: DataFrame, features: dict[str, Row]) -> None:
    assert flatten(raw).filter("nct_id = 'SYN00000002'").count() == 2
    assert deduplicate(flatten(raw)).filter("nct_id = 'SYN00000002'").count() == 1
    assert features["SYN00000002"]["indication"] == "asthma"


def test_enrollment_sites_duration_and_accrual_rate(features: dict[str, Row]) -> None:
    row = features["SYN00000001"]
    assert row["enrollment"] == 400
    assert row["site_count"] == 20
    assert row["countries"] == ["Germany", "United States"]
    assert row["country_count"] == 2
    assert row["start_date"] == dt.date(2018, 1, 15)
    assert row["duration_months"] == pytest.approx(365 / 30.4375, abs=0.01)
    assert row["accrual_rate_per_site_month"] == pytest.approx(400 / (20 * row["duration_months"]), abs=1e-3)


def test_month_only_dates_map_to_first_of_month(features: dict[str, Row]) -> None:
    row = features["SYN00000002"]
    assert row["start_date"] == dt.date(2019, 3, 1)
    assert row["primary_completion_date"] == dt.date(2020, 3, 1)


def test_missing_sites_keep_row_with_null_rate(features: dict[str, Row]) -> None:
    row = features["SYN00000009"]
    assert row["site_count"] is None
    assert row["accrual_rate_per_site_month"] is None
    assert row["country_count"] == 0


def test_phase_normalisation(features: dict[str, Row]) -> None:
    assert (features["SYN00000001"]["phase"], features["SYN00000001"]["phase_group"]) == ("PHASE3", 3)
    assert (features["SYN00000003"]["phase"], features["SYN00000003"]["phase_group"]) == ("PHASE2/PHASE3", 3)
    assert (features["SYN00000004"]["phase"], features["SYN00000004"]["phase_group"]) == ("PHASE1/PHASE2", 2)


def test_eligibility_features(features: dict[str, Row]) -> None:
    t2d = features["SYN00000001"]
    assert (t2d["n_inclusion"], t2d["n_exclusion"]) == (3, 3)
    assert (t2d["min_age_years"], t2d["max_age_years"]) == (18.0, 75.0)
    assert (t2d["hba1c_min"], t2d["hba1c_max"]) == (7.0, 10.5)
    assert (t2d["bmi_min"], t2d["bmi_max"]) == (None, 40.0)
    assert t2d["egfr_min"] == 45.0
    assert {"hba1c", "bmi", "renal", "pregnancy", "cardiovascular"} <= set(t2d["criteria_categories"])
    asthma = features["SYN00000002"]
    assert (asthma["fev1_pct_min"], asthma["fev1_pct_max"]) == (40.0, 80.0)
    assert asthma["pack_years_max"] == 10.0
    assert features["SYN00000009"]["min_age_years"] == 0.5
    assert features["SYN00000009"]["max_age_years"] is None


def test_termination_reason(features: dict[str, Row]) -> None:
    low = features["SYN00000003"]
    assert (low["stop_category"], low["low_accrual_terminated"]) == ("low_accrual", True)
    business = features["SYN00000004"]
    assert (business["stop_category"], business["low_accrual_terminated"]) == ("business", False)
    completed = features["SYN00000001"]
    assert (completed["stop_category"], completed["low_accrual_terminated"]) == ("none", False)


def test_recruiting_trials_one_row_per_trial_country(raw: DataFrame) -> None:
    df = build_recruiting_trials(raw)
    assert df.columns == RECRUITING_COLUMNS
    rows = {(r["nct_id"], r["country"]): r["sites_in_country"] for r in df.collect()}
    assert rows == {
        ("SYN00000011", "France"): 2,
        ("SYN00000011", "Spain"): 1,
        ("SYN00000012", "United States"): 3,
    }


def test_person_level_guard(spark: SparkSession) -> None:
    ok = spark.createDataFrame([("SYN1", "x")], ["nct_id", "title"])
    assert_no_person_level_columns(ok)
    bad = spark.createDataFrame([("SYN1", "a@b.c")], ["nct_id", "contact_email"])
    with pytest.raises(ValueError, match="person-level"):
        assert_no_person_level_columns(bad)


def test_job_writes_versioned_parquet(spark: SparkSession, tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    lines = (FIXTURES / "studies.jsonl").read_text()
    for name in ("benchmark_studies", "recruiting_studies"):
        with gzip.open(raw_dir / f"{name}.jsonl.gz", "wt") as fh:
            fh.write(lines)
    (raw_dir / "MANIFEST.json").write_text(json.dumps({"source": "fixture", "fetched_at": "2026-01-01T00:00:00Z"}))

    manifest = run(spark, raw_dir, tmp_path / "out")

    version_dir = tmp_path / "out" / f"v{DATASET_VERSION}"
    assert manifest["tables"] == {"trial_features": {"rows": 5}, "recruiting_trials": {"rows": 3}}
    assert json.loads((version_dir / "_MANIFEST.json").read_text())["source"]["api"] == "fixture"
    written = spark.read.parquet(str(version_dir / "trial_features"))
    assert written.count() == 5
    assert written.columns == TRIAL_FEATURE_COLUMNS
