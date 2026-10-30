"""Read the Parquet source tables into Spark DataFrames."""
from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

INPUT_TABLES = ("territories", "reps", "visits", "follow_ups", "weekly_sales")


def read_table(spark: SparkSession, input_dir: Path, name: str) -> DataFrame:
    path = Path(input_dir) / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Input table '{name}' not found at {path}")
    return spark.read.parquet(str(path))


def read_inputs(spark: SparkSession, input_dir: Path) -> dict[str, DataFrame]:
    """Return {'territories', 'reps', 'visits', 'follow_ups', 'weekly_sales'} as DataFrames."""
    return {name: read_table(spark, input_dir, name) for name in INPUT_TABLES}
