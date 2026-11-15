"""In-memory view of the Parquet tables produced by pda-data."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

THRESHOLD_NAMES = ["hba1c", "bmi", "fev1_pct", "pack_years", "egfr"]


@dataclass(frozen=True)
class Trial:
    nct_id: str
    title: str | None
    indication: str
    phase: str
    phase_group: int
    overall_status: str
    stop_category: str
    low_accrual_terminated: bool
    enrollment: int
    site_count: int | None
    countries: tuple[str, ...]
    duration_months: float
    accrual_rate_per_site_month: float | None
    min_age_years: float | None
    max_age_years: float | None
    n_inclusion: int
    n_exclusion: int
    categories: frozenset[str]
    thresholds: dict[str, tuple[float | None, float | None]] = field(compare=False, hash=False)

    @property
    def n_criteria(self) -> int:
        return self.n_inclusion + self.n_exclusion


@dataclass(frozen=True)
class RecruitingTrial:
    nct_id: str
    title: str | None
    indication: str
    phase: str
    enrollment: int | None
    country: str
    sites_in_country: int


@dataclass(frozen=True)
class Benchmark:
    trials: tuple[Trial, ...]
    recruiting: tuple[RecruitingTrial, ...]

    def trial_ids(self) -> set[str]:
        return {trial.nct_id for trial in self.trials}

    def by_id(self) -> dict[str, Trial]:
        return {trial.nct_id: trial for trial in self.trials}


def _trial(row: dict[str, Any]) -> Trial:
    thresholds = {
        name: (row.get(f"{name}_min"), row.get(f"{name}_max"))
        for name in THRESHOLD_NAMES
        if row.get(f"{name}_min") is not None or row.get(f"{name}_max") is not None
    }
    return Trial(
        nct_id=row["nct_id"],
        title=row.get("title"),
        indication=row["indication"],
        phase=row["phase"],
        phase_group=int(row["phase_group"]),
        overall_status=row["overall_status"],
        stop_category=row.get("stop_category") or "none",
        low_accrual_terminated=bool(row.get("low_accrual_terminated")),
        enrollment=int(row["enrollment"]),
        site_count=row.get("site_count"),
        countries=tuple(row.get("countries") or ()),
        duration_months=float(row["duration_months"]),
        accrual_rate_per_site_month=row.get("accrual_rate_per_site_month"),
        min_age_years=row.get("min_age_years"),
        max_age_years=row.get("max_age_years"),
        n_inclusion=int(row.get("n_inclusion") or 0),
        n_exclusion=int(row.get("n_exclusion") or 0),
        categories=frozenset(row.get("criteria_categories") or ()),
        thresholds=thresholds,
    )


def _read(path: Path) -> list[dict[str, Any]]:
    # Accept a single file (committed sample copy) or a Spark output directory.
    source = path if path.exists() else path.with_suffix("")
    rows: list[dict[str, Any]] = pq.read_table(source).to_pylist()
    return rows


@lru_cache(maxsize=4)
def load_benchmark(directory: Path) -> Benchmark:
    trials = tuple(_trial(row) for row in _read(directory / "trial_features.parquet"))
    recruiting = tuple(
        RecruitingTrial(
            nct_id=row["nct_id"],
            title=row.get("title"),
            indication=row["indication"],
            phase=row["phase"],
            enrollment=row.get("enrollment"),
            country=row["country"],
            sites_in_country=int(row.get("sites_in_country") or 0),
        )
        for row in _read(directory / "recruiting_trials.parquet")
    )
    return Benchmark(trials=trials, recruiting=recruiting)
