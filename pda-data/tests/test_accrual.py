"""Accrual benchmark aggregates on a hand-built trial table, so every expected number is obvious."""

from __future__ import annotations

import pytest
from pyspark.sql import DataFrame, Row, SparkSession

from pda_data.schema import ACCRUAL_BENCHMARK_COLUMNS, COUNTRY_ACCRUAL_COLUMNS
from pda_data.transform import build_accrual_benchmarks, build_country_accrual, build_trial_features

SCHEMA = (
    "nct_id string, indication string, phase_group int, overall_status string, low_accrual_terminated boolean, "
    "site_count int, duration_months double, accrual_rate_per_site_month double, countries array<string>"
)

# Asthma phase 3: five trials with rates 1..5, one without sites, one with a zero rate.
TRIALS = [
    ("SYN1", "asthma", 3, "COMPLETED", False, 10, 10.0, 1.0, ["France", "Spain"]),
    ("SYN2", "asthma", 3, "COMPLETED", False, 20, 12.0, 2.0, ["France"]),
    ("SYN3", "asthma", 3, "COMPLETED", False, 30, 14.0, 3.0, ["France"]),
    ("SYN4", "asthma", 3, "TERMINATED", True, 40, 16.0, 4.0, ["Spain"]),
    ("SYN5", "asthma", 3, "TERMINATED", False, 50, 18.0, 5.0, ["Spain"]),
    ("SYN6", "asthma", 3, "COMPLETED", False, None, 20.0, None, []),
    ("SYN7", "asthma", 3, "TERMINATED", True, 60, 22.0, 0.0, ["Spain"]),
    ("SYN8", "copd", 2, "COMPLETED", False, 5, 6.0, 0.5, ["Japan"]),
]


@pytest.fixture(scope="module")
def trials(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(TRIALS, SCHEMA)


@pytest.fixture(scope="module")
def benchmarks(trials: DataFrame) -> dict[tuple[str, int], Row]:
    df = build_accrual_benchmarks(trials)
    assert df.columns == ACCRUAL_BENCHMARK_COLUMNS
    return {(r["indication"], r["phase_group"]): r for r in df.collect()}


def test_one_row_per_indication_and_phase_group(benchmarks: dict[tuple[str, int], Row]) -> None:
    assert set(benchmarks) == {("asthma", 3), ("copd", 2)}


def test_percentiles_use_only_trials_with_a_positive_rate(benchmarks: dict[tuple[str, int], Row]) -> None:
    row = benchmarks[("asthma", 3)]
    assert row["n_trials"] == 7
    assert row["n_with_accrual_rate"] == 5
    assert row["accrual_rate_p50"] == pytest.approx(3.0)
    assert row["accrual_rate_p25"] == pytest.approx(2.0)
    assert row["accrual_rate_p75"] == pytest.approx(4.0)
    assert row["accrual_rate_p10"] == pytest.approx(1.4)
    assert row["accrual_rate_p90"] == pytest.approx(4.6)


def test_percentiles_are_ordered(benchmarks: dict[tuple[str, int], Row]) -> None:
    for row in benchmarks.values():
        values = [row[f"accrual_rate_p{p}"] for p in (10, 25, 50, 75, 90)]
        assert values == sorted(values)


def test_low_accrual_termination_share(benchmarks: dict[tuple[str, int], Row]) -> None:
    row = benchmarks[("asthma", 3)]
    assert row["n_terminated"] == 3
    assert row["n_low_accrual_terminated"] == 2
    assert row["low_accrual_terminated_share"] == pytest.approx(2 / 7)
    assert benchmarks[("copd", 2)]["low_accrual_terminated_share"] == 0.0


def test_medians_ignore_missing_site_counts(benchmarks: dict[tuple[str, int], Row]) -> None:
    row = benchmarks[("asthma", 3)]
    assert row["median_site_count"] == pytest.approx(35.0)
    assert row["median_duration_months"] == pytest.approx(16.0)


def test_country_accrual_counts_a_trial_once_per_country(trials: DataFrame) -> None:
    df = build_country_accrual(trials)
    assert df.columns == COUNTRY_ACCRUAL_COLUMNS
    rows = {(r["indication"], r["country"]): r for r in df.collect()}
    assert set(rows) == {("asthma", "France"), ("asthma", "Spain"), ("copd", "Japan")}
    france, spain = rows[("asthma", "France")], rows[("asthma", "Spain")]
    assert (france["n_trials"], france["n_with_accrual_rate"]) == (3, 3)
    assert france["accrual_rate_p50"] == pytest.approx(2.0)
    assert france["n_low_accrual_terminated"] == 0
    assert (spain["n_trials"], spain["n_with_accrual_rate"]) == (4, 3)
    assert spain["accrual_rate_p50"] == pytest.approx(4.0)
    assert spain["n_low_accrual_terminated"] == 2


def test_aggregates_build_from_the_real_feature_table(raw: DataFrame) -> None:
    features = build_trial_features(raw)
    benchmarks = build_accrual_benchmarks(features)
    assert benchmarks.agg({"n_trials": "sum"}).first()[0] == features.count()
    assert build_country_accrual(features).filter("n_with_accrual_rate > n_trials").count() == 0
