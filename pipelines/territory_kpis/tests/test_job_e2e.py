import pandas as pd
import pytest

from pipelines.territory_kpis.config import EXPECTED_OUTPUT_PATH, JobConfig
from pipelines.territory_kpis.job import run
from pipelines.territory_kpis.parity import compare_frames
from pipelines.territory_kpis.transform import OUTPUT_COLUMNS


@pytest.fixture(scope="module")
def job_output(spark, tmp_path_factory):
    out = tmp_path_factory.mktemp("e2e") / "territory_kpis.parquet"
    cfg = JobConfig.from_args(["--output", str(out)], env={})
    run(spark, cfg)
    return pd.read_parquet(out)


def test_job_output_matches_frozen_notebook_output(job_output):
    expected = pd.read_parquet(EXPECTED_OUTPUT_PATH)
    assert len(job_output) == len(expected) == 520
    assert list(job_output.columns) == OUTPUT_COLUMNS
    report = compare_frames(job_output, expected, tolerance=1e-6)
    assert report.passed, report.render()
    assert report.rows_compared == 520
    assert report.render().splitlines()[-1] == "520 rows compared, 0 mismatches"


def test_compare_frames_detects_mismatches(job_output):
    expected = pd.read_parquet(EXPECTED_OUTPUT_PATH)
    tampered = job_output.copy()
    tampered.loc[0, "revenue_gbp"] += 1.0
    tampered.loc[1, "region"] = "Nowhere"
    report = compare_frames(tampered, expected)
    assert not report.passed
    assert {c.column: c.mismatches for c in report.columns if c.mismatches} == {"revenue_gbp": 1, "region": 1}
    assert report.render().endswith("520 rows compared, 2 mismatches")


def test_compare_frames_detects_missing_rows(job_output):
    expected = pd.read_parquet(EXPECTED_OUTPUT_PATH)
    report = compare_frames(job_output.iloc[:-1], expected)
    assert not report.passed
    assert any("row count differs" in p for p in report.problems)
    assert any("key sets differ" in p for p in report.problems)
