"""Pydantic models for the intent graph and the plan graph.

All models are frozen: a graph is never edited in place. Operations build a new graph.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal["primary", "secondary"]
VisitKind = Literal["screening", "randomisation", "treatment", "follow_up"]
StandardScope = Literal["screening", "on_site", "post_baseline"]


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- Intent graph -----------------------------------------------------------------


class Objective(Model):
    id: str
    level: Level
    text: str


class Timepoint(Model):
    """An endpoint timepoint, expressed as a study week (Week 12 is Day 85)."""

    week: int = Field(ge=0)

    @property
    def label(self) -> str:
        return f"Week {self.week}"

    @property
    def day(self) -> int:
        return self.week * 7 + 1


class Endpoint(Model):
    id: str
    name: str
    level: Level
    objective_id: str
    timepoint: Timepoint
    design_activity_id: str


class Estimand(Model):
    id: str
    endpoint_id: str
    population: str
    intercurrent_event_strategy: str
    summary_measure: str


class DesignActivity(Model):
    """An assessment or intervention the design needs (for example spirometry)."""

    id: str
    name: str
    purpose: str


class Arm(Model):
    id: str
    name: str
    intervention: str
    ratio: int = Field(ge=1)


class Assignment(Model):
    method: Literal["randomised", "non-randomised"]
    blinding: Literal["open-label", "single-blind", "double-blind"]
    control: str


class IntentGraph(Model):
    objectives: tuple[Objective, ...] = ()
    estimands: tuple[Estimand, ...] = ()
    endpoints: tuple[Endpoint, ...] = ()
    design_activities: tuple[DesignActivity, ...] = ()
    arms: tuple[Arm, ...] = ()
    assignment: Assignment


# --- Plan graph -------------------------------------------------------------------


class Visit(Model):
    id: str
    name: str
    day: int
    window: int = Field(default=0, ge=0)
    kind: VisitKind = "treatment"
    on_site: bool = True


class Activity(Model):
    """An operational activity that can be scheduled at visits.

    It traces to the intent graph through ``design_activity_id`` or to an
    operational standard that requires it.
    """

    id: str
    name: str
    unit_cost: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    design_activity_id: str | None = None


class OperationalStandard(Model):
    """A standard activity that must happen at every visit in ``applies_to``."""

    id: str
    name: str
    activity_id: str
    applies_to: StandardScope


class ScheduledActivity(Model):
    visit_id: str
    activity_id: str

    @property
    def id(self) -> str:
        return f"{self.visit_id}:{self.activity_id}"


class PlanGraph(Model):
    visits: tuple[Visit, ...] = ()
    activities: tuple[Activity, ...] = ()
    standards: tuple[OperationalStandard, ...] = ()
    schedule: tuple[ScheduledActivity, ...] = ()


# --- Study ------------------------------------------------------------------------


class StudyGraph(Model):
    title: str
    phase: str
    indication: str
    duration_weeks: int = Field(ge=1)
    intent: IntentGraph
    plan: PlanGraph

    def visit(self, visit_id: str) -> Visit | None:
        return next((v for v in self.plan.visits if v.id == visit_id), None)

    def activity(self, activity_id: str) -> Activity | None:
        return next((a for a in self.plan.activities if a.id == activity_id), None)

    def endpoint(self, endpoint_id: str) -> Endpoint | None:
        return next((e for e in self.intent.endpoints if e.id == endpoint_id), None)

    def visits_by_day(self) -> tuple[Visit, ...]:
        return tuple(sorted(self.plan.visits, key=lambda v: (v.day, v.id)))

    def is_scheduled(self, visit_id: str, activity_id: str) -> bool:
        return any(
            c.visit_id == visit_id and c.activity_id == activity_id for c in self.plan.schedule
        )

    def node_ids(self) -> tuple[str, ...]:
        """IDs of every node (not schedule cells), in a stable order."""
        intent, plan = self.intent, self.plan
        return (
            *(o.id for o in intent.objectives),
            *(e.id for e in intent.estimands),
            *(e.id for e in intent.endpoints),
            *(d.id for d in intent.design_activities),
            *(a.id for a in intent.arms),
            *(v.id for v in plan.visits),
            *(a.id for a in plan.activities),
            *(s.id for s in plan.standards),
        )

    def element_ids(self) -> frozenset[str]:
        """IDs of every node and every schedule cell (``visit_id:activity_id``)."""
        return frozenset((*self.node_ids(), *(c.id for c in self.plan.schedule)))
