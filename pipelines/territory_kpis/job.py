"""Entry point: extract -> transform -> quality checks -> load.

Run from the repo root:
    python pipelines/territory_kpis/job.py --input-dir data \
        --output pipelines/territory_kpis/output/territory_kpis.parquet
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `pipelines.territory_kpis` importable as a script

from pyspark.sql import SparkSession  # noqa: E402

from pipelines.territory_kpis.config import JobConfig  # noqa: E402
from pipelines.territory_kpis.extract import read_inputs  # noqa: E402
from pipelines.territory_kpis.load import write_output  # noqa: E402
from pipelines.territory_kpis.quality import run_quality_checks  # noqa: E402
from pipelines.territory_kpis.transform import build_territory_kpis  # noqa: E402


def build_spark(config: JobConfig) -> SparkSession:
    """Local SparkSession by default; on Databricks `getOrCreate` returns the cluster session."""
    return (
        SparkSession.builder.appName(config.app_name)
        .master(config.spark_master)
        .config("spark.sql.shuffle.partitions", str(config.shuffle_partitions))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def run(spark: SparkSession, config: JobConfig) -> Path:
    """Execute the pipeline with an existing session; returns the output path."""
    frames = read_inputs(spark, config.input_dir)
    kpis = build_territory_kpis(**frames).cache()
    report = run_quality_checks(kpis, min_rows=config.min_rows, max_rows=config.max_rows)
    print(report.summary())
    return write_output(kpis, config.output_path)


def main(argv: list[str] | None = None) -> int:
    config = JobConfig.from_args(argv)
    started = time.perf_counter()
    spark = build_spark(config)
    spark.sparkContext.setLogLevel("ERROR")
    try:
        output = run(spark, config)
    finally:
        spark.stop()
    print(f"territory_kpis written to {output} in {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
