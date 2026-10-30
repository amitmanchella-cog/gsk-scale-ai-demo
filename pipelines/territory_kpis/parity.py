"""Parity check: job output vs the frozen notebook output (notebooks/expected_output/territory_kpis.parquet).

    python pipelines/territory_kpis/parity.py [--output PATH] [--expected PATH] [--tolerance 1e-6]

Runs the job first if the output Parquet does not exist, then compares every column aligned on
(territory_id, week). Prints a per-column summary and a final line `N rows compared, M mismatches`;
exits non-zero on any mismatch.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.territory_kpis.config import DEFAULT_OUTPUT_PATH, EXPECTED_OUTPUT_PATH  # noqa: E402
from pipelines.territory_kpis.transform import KEY_COLUMNS, OUTPUT_COLUMNS  # noqa: E402

DEFAULT_TOLERANCE = 1e-6


@dataclass
class ColumnResult:
    column: str
    mismatches: int
    max_abs_diff: float | None = None
    example: str = ""


@dataclass
class ParityReport:
    rows_compared: int = 0
    columns: list[ColumnResult] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def mismatches(self) -> int:
        return sum(c.mismatches for c in self.columns)

    @property
    def passed(self) -> bool:
        return not self.problems and self.mismatches == 0

    def render(self) -> str:
        lines = [f"{'column':20s} {'mismatches':>10s} {'max_abs_diff':>14s}  example"]
        for c in self.columns:
            diff = "" if c.max_abs_diff is None else f"{c.max_abs_diff:.3g}"
            lines.append(f"{c.column:20s} {c.mismatches:10d} {diff:>14s}  {c.example}")
        lines.extend(f"PROBLEM: {p}" for p in self.problems)
        lines.append(f"{self.rows_compared} rows compared, {self.mismatches} mismatches")
        return "\n".join(lines)


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce `week` to a date, order by key and reset the index so both sides are row-aligned."""
    out = df.copy()
    out["week"] = pd.to_datetime(out["week"]).dt.date
    return out.sort_values(KEY_COLUMNS).reset_index(drop=True)


def compare_frames(actual: pd.DataFrame, expected: pd.DataFrame, tolerance: float = DEFAULT_TOLERANCE) -> ParityReport:
    report = ParityReport()
    actual, expected = normalise(actual), normalise(expected)

    if len(actual) != len(expected):
        report.problems.append(f"row count differs: job={len(actual)} expected={len(expected)}")
    actual_keys = set(map(tuple, actual[KEY_COLUMNS].itertuples(index=False)))
    expected_keys = set(map(tuple, expected[KEY_COLUMNS].itertuples(index=False)))
    if actual_keys != expected_keys:
        only_job, only_exp = actual_keys - expected_keys, expected_keys - actual_keys
        report.problems.append(f"key sets differ: {len(only_job)} only in job, {len(only_exp)} only in expected")
    missing_cols = [c for c in OUTPUT_COLUMNS if c not in actual.columns]
    if missing_cols:
        report.problems.append(f"job output is missing columns: {missing_cols}")
    if list(actual.columns) != list(expected.columns):
        report.problems.append(f"column order differs: job={list(actual.columns)} expected={list(expected.columns)}")
    if report.problems and (len(actual) != len(expected) or actual_keys != expected_keys):
        return report  # cannot align rows -> per-column comparison would be meaningless

    merged = expected.merge(actual, on=KEY_COLUMNS, how="inner", suffixes=("_exp", "_job"))
    report.rows_compared = len(merged)
    for col in expected.columns:
        if col in KEY_COLUMNS:
            continue
        exp, job = merged[f"{col}_exp"], merged[f"{col}_job"]
        if pd.api.types.is_numeric_dtype(exp) and pd.api.types.is_numeric_dtype(job):
            e, j = exp.astype(float).to_numpy(), job.astype(float).to_numpy()
            diff = np.abs(e - j)
            bad = ~((diff <= tolerance) | (np.isnan(e) & np.isnan(j)))
            max_diff = float(np.nanmax(diff)) if len(diff) else 0.0
        else:
            bad = ~((exp == job) | (exp.isna() & job.isna())).to_numpy()
            max_diff = None
        example = ""
        if bad.any():
            i = int(np.argmax(bad))
            key = tuple(merged.loc[i, KEY_COLUMNS])
            example = f"{key}: expected={exp.iloc[i]!r} job={job.iloc[i]!r}"
        report.columns.append(ColumnResult(col, int(bad.sum()), max_diff, example))
    return report


def ensure_output(output_path: Path) -> None:
    if output_path.exists():
        return
    print(f"{output_path} not found - running the job first")
    from pipelines.territory_kpis.job import main as job_main

    job_main(["--output", str(output_path)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Job output Parquet path.")
    parser.add_argument("--expected", type=Path, default=EXPECTED_OUTPUT_PATH, help="Frozen notebook output.")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE, help="Absolute numeric tolerance.")
    args = parser.parse_args(argv)

    ensure_output(args.output)
    actual = pd.read_parquet(args.output)
    expected = pd.read_parquet(args.expected)
    report = compare_frames(actual, expected, tolerance=args.tolerance)
    print(report.render())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
