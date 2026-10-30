"""Job configuration: CLI args > environment variables > repo-relative defaults."""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "data"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "pipelines" / "territory_kpis" / "output" / "territory_kpis.parquet"
EXPECTED_OUTPUT_PATH = REPO_ROOT / "notebooks" / "expected_output" / "territory_kpis.parquet"

ENV_PREFIX = "TERRITORY_KPIS_"


@dataclass(frozen=True)
class JobConfig:
    input_dir: Path = DEFAULT_INPUT_DIR
    output_path: Path = DEFAULT_OUTPUT_PATH
    spark_master: str = "local[*]"
    app_name: str = "territory_kpis"
    shuffle_partitions: int = 8
    min_rows: int = 100
    max_rows: int = 5000

    @classmethod
    def from_args(cls, argv: list[str] | None = None, env: dict[str, str] | None = None) -> "JobConfig":
        env = os.environ if env is None else env
        defaults = cls()
        parser = argparse.ArgumentParser(description="Build weekly territory KPIs with PySpark.")
        parser.add_argument("--input-dir", default=env.get(f"{ENV_PREFIX}INPUT_DIR", str(defaults.input_dir)),
                            help="Directory containing the Parquet input tables.")
        parser.add_argument("--output", default=env.get(f"{ENV_PREFIX}OUTPUT", str(defaults.output_path)),
                            help="Output Parquet path (overwritten).")
        parser.add_argument("--master", default=env.get(f"{ENV_PREFIX}SPARK_MASTER", defaults.spark_master),
                            help="Spark master URL (ignored on Databricks where a session already exists).")
        parser.add_argument("--shuffle-partitions", type=int,
                            default=int(env.get(f"{ENV_PREFIX}SHUFFLE_PARTITIONS", defaults.shuffle_partitions)))
        parser.add_argument("--min-rows", type=int, default=int(env.get(f"{ENV_PREFIX}MIN_ROWS", defaults.min_rows)),
                            help="Lower bound of the row-count quality check.")
        parser.add_argument("--max-rows", type=int, default=int(env.get(f"{ENV_PREFIX}MAX_ROWS", defaults.max_rows)),
                            help="Upper bound of the row-count quality check.")
        ns = parser.parse_args(argv)
        return cls(
            input_dir=_resolve(ns.input_dir),
            output_path=_resolve(ns.output),
            spark_master=ns.master,
            shuffle_partitions=ns.shuffle_partitions,
            min_rows=ns.min_rows,
            max_rows=ns.max_rows,
        )


def _resolve(path: str) -> Path:
    """Absolute paths are kept; relative paths are resolved against the repo root (not the CWD)."""
    p = Path(path).expanduser()
    return p if p.is_absolute() else (REPO_ROOT / p).resolve()
