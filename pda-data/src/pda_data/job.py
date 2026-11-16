"""Entry point: read the committed raw snapshot and write versioned Parquet.

    python -m pda_data.job --raw data/raw --out output

writes ``output/v<DATASET_VERSION>/{trial_features,recruiting_trials}`` and a
``_MANIFEST.json`` with row counts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from pda_data import DATASET_VERSION
from pda_data.schema import PERSON_LEVEL_TOKENS, RAW_SCHEMA
from pda_data.transform import build_recruiting_trials, build_trial_features


def get_spark(app_name: str = "pda-data") -> SparkSession:
    return (
        SparkSession.builder.master("local[2]")
        .appName(app_name)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )


def read_raw(spark: SparkSession, path: Path) -> DataFrame:
    """Read a JSON-lines snapshot (optionally gzipped) with the explicit API schema."""
    return spark.read.schema(RAW_SCHEMA).json(str(path))


def assert_no_person_level_columns(df: DataFrame) -> None:
    """Fail fast if an output column looks like person-level data."""
    offenders = [c for c in df.columns if any(tok in c.lower().split("_") for tok in PERSON_LEVEL_TOKENS)]
    if offenders:
        raise ValueError(f"person-level columns are not allowed in the output: {offenders}")


def write_parquet(df: DataFrame, path: Path) -> int:
    assert_no_person_level_columns(df)
    df.coalesce(1).write.mode("overwrite").parquet(str(path))
    return df.count()


def run(spark: SparkSession, raw_dir: Path, out_dir: Path) -> dict[str, object]:
    version_dir = out_dir / f"v{DATASET_VERSION}"
    benchmark = build_trial_features(read_raw(spark, raw_dir / "benchmark_studies.jsonl.gz")).cache()
    recruiting = build_recruiting_trials(read_raw(spark, raw_dir / "recruiting_studies.jsonl.gz")).cache()
    manifest: dict[str, object] = {
        "dataset_version": DATASET_VERSION,
        "tables": {
            "trial_features": {"rows": write_parquet(benchmark, version_dir / "trial_features")},
            "recruiting_trials": {"rows": write_parquet(recruiting, version_dir / "recruiting_trials")},
        },
    }
    source_manifest = raw_dir / "MANIFEST.json"
    if source_manifest.exists():
        source = json.loads(source_manifest.read_text())
        manifest["source"] = {"api": source.get("source"), "fetched_at": source.get("fetched_at")}
    (version_dir / "_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the PDA benchmark dataset")
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()
    spark = get_spark()
    try:
        print(json.dumps(run(spark, args.raw, args.out), indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
