"""The synthetic fallback must flow through the same pipeline as the real snapshot."""

import sys
from pathlib import Path

from pyspark.sql import SparkSession

from pda_data.job import run

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from generate_synthetic import generate  # noqa: E402


def test_synthetic_snapshot_runs_through_pipeline(spark: SparkSession, tmp_path: Path) -> None:
    counts = generate(tmp_path / "raw", trials=60, seed=1)
    assert counts["benchmark"] == {"asthma": 20, "copd": 20, "type_2_diabetes": 20}
    manifest = run(spark, tmp_path / "raw", tmp_path / "out")
    assert manifest["tables"]["trial_features"]["rows"] == 60  # type: ignore[index]
    df = spark.read.parquet(str(tmp_path / "out" / "v1" / "trial_features"))
    assert df.filter(~df.nct_id.startswith("SYN")).count() == 0
    assert df.filter(df.accrual_rate_per_site_month.isNull()).count() == 0


def test_synthetic_snapshot_is_deterministic(tmp_path: Path) -> None:
    generate(tmp_path / "a", trials=30, seed=3)
    generate(tmp_path / "b", trials=30, seed=3)
    import gzip

    read = lambda d: gzip.open(d / "benchmark_studies.jsonl.gz", "rt").read()  # noqa: E731
    assert read(tmp_path / "a") == read(tmp_path / "b")
