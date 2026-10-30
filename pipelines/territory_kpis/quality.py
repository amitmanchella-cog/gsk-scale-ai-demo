"""Data-quality checks on the final KPI table. Each check returns a CheckResult; run_quality_checks raises."""
from __future__ import annotations

from dataclasses import dataclass, field

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

from pipelines.territory_kpis.transform import KEY_COLUMNS, OUTPUT_COLUMNS

# Column -> accepted Spark type family. Kept loose (int vs long) so the checks describe intent, not Spark internals.
EXPECTED_SCHEMA: dict[str, tuple[type, ...]] = {
    "territory_id": (T.StringType,),
    "region": (T.StringType,),
    "week": (T.DateType, T.TimestampType),
    "visits": (T.IntegralType,),
    "unique_hcps": (T.IntegralType,),
    "f2f_visits": (T.IntegralType,),
    "f2f_share": (T.FractionalType,),
    "avg_duration_min": (T.FractionalType,),
    "open_follow_ups": (T.IntegralType,),
    "rep_count": (T.IntegralType,),
    "visits_per_rep": (T.FractionalType,),
    "units": (T.IntegralType,),
    "revenue_gbp": (T.FractionalType,),
    "revenue_per_visit": (T.FractionalType,),
}
assert list(EXPECTED_SCHEMA) == OUTPUT_COLUMNS


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str = ""


@dataclass
class QualityReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> str:
        lines = [f"[{'PASS' if r.passed else 'FAIL'}] {r.name}: {r.details}" for r in self.results]
        return "\n".join(lines)


class DataQualityError(RuntimeError):
    def __init__(self, report: QualityReport):
        self.report = report
        failed = ", ".join(r.name for r in report.failures)
        super().__init__(f"Data quality checks failed: {failed}\n{report.summary()}")


def check_schema(df: DataFrame, expected: dict[str, tuple[type, ...]] | None = None) -> CheckResult:
    """All required columns are present with a compatible type."""
    expected = EXPECTED_SCHEMA if expected is None else expected
    actual = {f.name: f.dataType for f in df.schema.fields}
    missing = [c for c in expected if c not in actual]
    wrong_type = [
        f"{c} is {actual[c].simpleString()}" for c, families in expected.items()
        if c in actual and not isinstance(actual[c], families)
    ]
    problems = []
    if missing:
        problems.append(f"missing columns: {missing}")
    if wrong_type:
        problems.append(f"unexpected types: {wrong_type}")
    return CheckResult("schema", not problems, "; ".join(problems) or f"{len(expected)} required columns present")


def check_no_null_keys(df: DataFrame, keys: list[str] | None = None) -> CheckResult:
    """Key columns contain no nulls."""
    keys = KEY_COLUMNS if keys is None else keys
    null_counts = df.select([F.count(F.when(F.col(k).isNull(), 1)).alias(k) for k in keys]).first().asDict()
    bad = {k: v for k, v in null_counts.items() if v}
    return CheckResult("no_null_keys", not bad, f"null keys: {bad}" if bad else f"no nulls in {keys}")


def check_unique_keys(df: DataFrame, keys: list[str] | None = None) -> CheckResult:
    """(territory_id, week) is unique."""
    keys = KEY_COLUMNS if keys is None else keys
    dupes = df.groupBy(*keys).count().filter(F.col("count") > 1).count()
    return CheckResult("unique_keys", dupes == 0, f"{dupes} duplicated {keys} combinations")


def check_row_count(df: DataFrame, min_rows: int = 100, max_rows: int = 5000) -> CheckResult:
    """Row count lies within [min_rows, max_rows]."""
    n = df.count()
    return CheckResult("row_count", min_rows <= n <= max_rows, f"{n} rows (expected {min_rows}-{max_rows})")


def run_quality_checks(df: DataFrame, min_rows: int = 100, max_rows: int = 5000) -> QualityReport:
    """Run every check; return the report when all pass, raise DataQualityError otherwise."""
    report = QualityReport(
        [
            check_schema(df),
            check_no_null_keys(df),
            check_unique_keys(df),
            check_row_count(df, min_rows=min_rows, max_rows=max_rows),
        ]
    )
    if not report.passed:
        raise DataQualityError(report)
    return report
