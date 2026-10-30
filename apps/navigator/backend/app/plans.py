"""Weekly plan builder (S3): in-memory per-rep plans, capacity rule and warnings.

A plan is five Mon–Fri slots for the week of the as-of date (``week_start`` is that week's Monday). The
:class:`PlanStore` only keeps ``(visit_id, hcp_id, day)`` per rep; :func:`build_plan` re-enriches every visit from
``views.territory_hcps`` on each read so names, scores and warnings follow the current as-of date and rules.

Configuration (read on every call, so tests can monkeypatch the environment):

* ``NAVIGATOR_MAX_VISITS_PER_DAY`` — day capacity (default 6; AC4).
* ``NAVIGATOR_OVERDUE_DAYS`` — a Segment A HCP is overdue when ``days_since_last_visit`` exceeds this or the HCP
  was never visited (default 30; AC5).

S4 adds ``to_csv(plan)`` here and the ``/export.csv`` route in ``routers/plan.py``.
"""

import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from .data import DataStore
from .scoring import ScoringRules
from .views import territory_hcps, to_records

MAX_VISITS_ENV = "NAVIGATOR_MAX_VISITS_PER_DAY"
OVERDUE_DAYS_ENV = "NAVIGATOR_OVERDUE_DAYS"
DEFAULT_MAX_VISITS_PER_DAY = 6
DEFAULT_OVERDUE_DAYS = 30
OVERDUE_SEGMENT = "A"

DayCode = Literal["Mon", "Tue", "Wed", "Thu", "Fri"]
DAYS: tuple[DayCode, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri")
DAY_NAMES: dict[str, str] = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}")
    return value


def max_visits_per_day() -> int:
    return _env_int(MAX_VISITS_ENV, DEFAULT_MAX_VISITS_PER_DAY)


def overdue_days() -> int:
    return _env_int(OVERDUE_DAYS_ENV, DEFAULT_OVERDUE_DAYS)


def week_start(as_of: date) -> date:
    """Monday of the week containing ``as_of``."""
    return as_of - timedelta(days=as_of.weekday())


def day_date(as_of: date, day: str) -> date:
    return week_start(as_of) + timedelta(days=DAYS.index(day))


# ---- response models (JSON shape per docs/uc4/design.md §4, mirrored in frontend/src/api.ts) ----


class PlanVisit(BaseModel):
    visit_id: int
    hcp_id: str
    hcp_name: str
    specialty: str
    segment: str
    score: int
    reason: str


class PlanDay(BaseModel):
    day: DayCode
    date: date
    count: int
    capacity: int
    visits: list[PlanVisit]


class PlanWarning(BaseModel):
    type: Literal["overdue_segment_a", "duplicate"]
    hcp_id: str
    hcp_name: str
    days: list[DayCode]
    message: str


class Plan(BaseModel):
    rep_id: str
    territory_id: str
    week_start: date
    as_of: date
    max_visits_per_day: int
    total_visits: int
    days: list[PlanDay]
    warnings: list[PlanWarning]


class AddVisitRequest(BaseModel):
    hcp_id: str
    day: DayCode


# ---- errors (mapped to HTTP status codes by routers/plan.py) ----


class PlanError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(PlanError):
    status_code = 404


class DayFull(PlanError):
    status_code = 409


class NotInTerritory(PlanError):
    status_code = 422


# ---- store ----


@dataclass
class StoredVisit:
    visit_id: int
    hcp_id: str
    day: str


@dataclass
class _RepPlan:
    next_visit_id: int = 1
    visits: list[StoredVisit] = field(default_factory=list)


class PlanStore:
    """Process-local ``dict[rep_id, visits]`` guarded by a lock; ``visit_id`` increments per plan."""

    def __init__(self) -> None:
        self._plans: dict[str, _RepPlan] = {}
        self._lock = threading.Lock()

    def visits(self, rep_id: str) -> list[StoredVisit]:
        with self._lock:
            plan = self._plans.get(rep_id)
            return list(plan.visits) if plan else []

    def add_visit(self, rep_id: str, hcp_id: str, day: str, capacity: int) -> StoredVisit:
        """Append a visit, raising :class:`DayFull` (plan unchanged) when ``day`` already holds ``capacity``."""
        with self._lock:
            plan = self._plans.setdefault(rep_id, _RepPlan())
            if sum(1 for visit in plan.visits if visit.day == day) >= capacity:
                raise DayFull(f"{DAY_NAMES[day]} already has {capacity} visits (max {capacity})")
            visit = StoredVisit(plan.next_visit_id, hcp_id, day)
            plan.next_visit_id += 1
            plan.visits.append(visit)
            return visit

    def remove_visit(self, rep_id: str, visit_id: int) -> bool:
        with self._lock:
            plan = self._plans.get(rep_id)
            if plan is None:
                return False
            before = len(plan.visits)
            plan.visits = [visit for visit in plan.visits if visit.visit_id != visit_id]
            return len(plan.visits) < before

    def clear(self, rep_id: str) -> None:
        with self._lock:
            self._plans.pop(rep_id, None)

    def reset(self) -> None:
        """Forget every rep's plan (tests)."""
        with self._lock:
            self._plans.clear()


PLAN_STORE = PlanStore()


# ---- building a plan ----


def rep_territory(store: DataStore, rep_id: str) -> str:
    reps = store["reps"]
    match = reps.loc[reps["rep_id"] == rep_id, "territory_id"]
    if match.empty:
        raise NotFound(f"rep {rep_id} not found")
    return str(match.iloc[0])


def _times(count: int) -> str:
    return "twice" if count == 2 else f"{count} times"


def _overdue_message(name: str, days: int | None) -> str:
    if days is None:
        return f"{name} (Segment {OVERDUE_SEGMENT}) has never been visited and is not planned"
    return f"{name} (Segment {OVERDUE_SEGMENT}) is {days} days overdue and not planned"


def _overdue_order(record: dict) -> tuple:
    """Never visited first, then most days overdue first, then name."""
    days = record["days_since_last_visit"]
    return (days is not None, -(days or 0), record["hcp_name"])


def _warnings(records: dict[str, dict], visits: list[StoredVisit], threshold: int) -> list[PlanWarning]:
    days_by_hcp: dict[str, list[str]] = defaultdict(list)
    for visit in visits:
        days_by_hcp[visit.hcp_id].append(visit.day)

    warnings = [
        PlanWarning(
            type="duplicate",
            hcp_id=hcp_id,
            hcp_name=records[hcp_id]["hcp_name"],
            days=days,
            message=f"{records[hcp_id]['hcp_name']} is planned {_times(len(days))} ({', '.join(days)})",
        )
        for hcp_id, days in days_by_hcp.items()
        if len(days) > 1
    ]

    overdue = [
        record
        for record in records.values()
        if record["segment"] == OVERDUE_SEGMENT
        and record["hcp_id"] not in days_by_hcp
        and (record["days_since_last_visit"] is None or record["days_since_last_visit"] > threshold)
    ]
    overdue.sort(key=_overdue_order)
    warnings.extend(
        PlanWarning(
            type="overdue_segment_a",
            hcp_id=record["hcp_id"],
            hcp_name=record["hcp_name"],
            days=[],
            message=_overdue_message(record["hcp_name"], record["days_since_last_visit"]),
        )
        for record in overdue
    )
    return warnings


def build_plan(
    store: DataStore,
    rep_id: str,
    as_of: date | None = None,
    rules: ScoringRules | None = None,
    plan_store: PlanStore = PLAN_STORE,
) -> Plan:
    """The rep's current plan with every visit re-enriched from ``territory_hcps`` and warnings recomputed."""
    territory_id = rep_territory(store, rep_id)
    as_of = as_of or store.as_of
    capacity = max_visits_per_day()
    records = {record["hcp_id"]: record for record in to_records(territory_hcps(store, territory_id, as_of, rules))}
    visits = plan_store.visits(rep_id)

    days = []
    for day in DAYS:
        day_visits = [
            PlanVisit(visit_id=visit.visit_id, **{key: records[visit.hcp_id][key] for key in _VISIT_FIELDS})
            for visit in visits
            if visit.day == day and visit.hcp_id in records
        ]
        days.append(
            PlanDay(day=day, date=day_date(as_of, day), count=len(day_visits), capacity=capacity, visits=day_visits)
        )

    return Plan(
        rep_id=rep_id,
        territory_id=territory_id,
        week_start=week_start(as_of),
        as_of=as_of,
        max_visits_per_day=capacity,
        total_visits=sum(day.count for day in days),
        days=days,
        warnings=_warnings(records, visits, overdue_days()),
    )


_VISIT_FIELDS = ("hcp_id", "hcp_name", "specialty", "segment", "score", "reason")


def add_visit(
    store: DataStore,
    rep_id: str,
    hcp_id: str,
    day: str,
    as_of: date | None = None,
    plan_store: PlanStore = PLAN_STORE,
) -> Plan:
    """Validate (rep 404 → day full 409 → hcp 404 → outside territory 422), store the visit and return the plan."""
    territory_id = rep_territory(store, rep_id)
    capacity = max_visits_per_day()
    if sum(1 for visit in plan_store.visits(rep_id) if visit.day == day) >= capacity:
        raise DayFull(f"{DAY_NAMES[day]} already has {capacity} visits (max {capacity})")
    hcps = store["hcps"]
    match = hcps.loc[hcps["hcp_id"] == hcp_id, "territory_id"]
    if match.empty:
        raise NotFound(f"HCP {hcp_id} not found")
    if match.iloc[0] != territory_id:
        raise NotInTerritory(f"HCP {hcp_id} is not in territory {territory_id}")
    plan_store.add_visit(rep_id, hcp_id, day, capacity)
    return build_plan(store, rep_id, as_of, plan_store=plan_store)


def remove_visit(
    store: DataStore, rep_id: str, visit_id: int, as_of: date | None = None, plan_store: PlanStore = PLAN_STORE
) -> Plan:
    rep_territory(store, rep_id)
    if not plan_store.remove_visit(rep_id, visit_id):
        raise NotFound(f"visit {visit_id} not found in {rep_id}'s plan")
    return build_plan(store, rep_id, as_of, plan_store=plan_store)


def clear_plan(store: DataStore, rep_id: str, as_of: date | None = None, plan_store: PlanStore = PLAN_STORE) -> Plan:
    rep_territory(store, rep_id)
    plan_store.clear(rep_id)
    return build_plan(store, rep_id, as_of, plan_store=plan_store)
