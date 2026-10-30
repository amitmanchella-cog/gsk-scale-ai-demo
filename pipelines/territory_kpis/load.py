"""Write the KPI table to Parquet."""
from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame


def write_output(df: DataFrame, output_path: Path, partitions: int = 1) -> Path:
    """Overwrite `output_path` (a Parquet directory) with `df`, creating parent directories first."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.coalesce(partitions).write.mode("overwrite").parquet(str(output_path))
    return output_path
