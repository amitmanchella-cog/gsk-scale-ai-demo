from datetime import date

import pytest

from pipelines.territory_kpis.quality import (
    DataQualityError,
    check_no_null_keys,
    check_row_count,
    check_schema,
    check_unique_keys,
    run_quality_checks,
)
from pipelines.territory_kpis.transform import OUTPUT_COLUMNS

KPI_SCHEMA = (
    "territory_id string, region string, week date, visits long, unique_hcps long, f2f_visits long, "
    "f2f_share double, avg_duration_min double, open_follow_ups long, rep_count long, visits_per_rep double, "
    "units long, revenue_gbp double, revenue_per_visit double"
)


def kpi_row(territory_id="T001", week=date(2025, 9, 1)):
    return (territory_id, "North", week, 4, 3, 2, 0.5, 20.0, 1, 2, 2.0, 10, 100.0, 25.0)


@pytest.fixture
def good_df(spark):
    return spark.createDataFrame([kpi_row(), kpi_row(week=date(2025, 9, 8)), kpi_row("T002")], KPI_SCHEMA)


def test_schema_passes(good_df):
    assert check_schema(good_df).passed


def test_schema_fails_on_missing_column_and_wrong_type(good_df):
    result = check_schema(good_df.drop("region").withColumn("visits", good_df["visits"].cast("string")))
    assert not result.passed
    assert "region" in result.details and "visits is string" in result.details


def test_no_null_keys_passes(good_df):
    assert check_no_null_keys(good_df).passed


def test_no_null_keys_fails(spark, good_df):
    with_null = good_df.union(spark.createDataFrame([(None, "North", date(2025, 9, 1)) + kpi_row()[3:]], KPI_SCHEMA))
    result = check_no_null_keys(with_null)
    assert not result.passed
    assert "territory_id" in result.details


def test_unique_keys_passes(good_df):
    assert check_unique_keys(good_df).passed


def test_unique_keys_fails_on_duplicate(good_df):
    result = check_unique_keys(good_df.union(good_df.limit(1)))
    assert not result.passed
    assert result.details.startswith("1 duplicated")


def test_row_count_passes_within_range(good_df):
    assert check_row_count(good_df, min_rows=1, max_rows=3).passed


@pytest.mark.parametrize("bounds", [(4, 10), (0, 2)])
def test_row_count_fails_outside_range(good_df, bounds):
    assert not check_row_count(good_df, *bounds).passed


def test_run_quality_checks_returns_report_when_all_pass(good_df):
    report = run_quality_checks(good_df, min_rows=1, max_rows=10)
    assert report.passed
    assert [r.name for r in report.results] == ["schema", "no_null_keys", "unique_keys", "row_count"]
    assert "[PASS] row_count: 3 rows" in report.summary()


def test_run_quality_checks_raises_with_failing_checks(good_df):
    with pytest.raises(DataQualityError) as exc:
        run_quality_checks(good_df.union(good_df.limit(1)).select(*OUTPUT_COLUMNS[:-1]), min_rows=100)
    failed = {r.name for r in exc.value.report.failures}
    assert failed == {"schema", "unique_keys", "row_count"}
