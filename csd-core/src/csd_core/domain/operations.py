"""Typed operations on the study graph.

Each operation is a small frozen model with an ``apply`` method that returns a new
graph. ``apply_operation`` adds the structural validity check on the result.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from csd_core.domain.models import (
    Activity,
    Arm,
    DesignActivity,
    Endpoint,
    Model,
    Objective,
    ScheduledActivity,
    StudyGraph,
    Timepoint,
    Visit,
)
from csd_core.domain.validity import check_validity


class OperationError(ValueError):
    """The operation cannot be applied to this graph. No version is created."""


def _with_plan(graph: StudyGraph, **changes: object) -> StudyGraph:
    return graph.model_copy(update={"plan": graph.plan.model_copy(update=changes)})


def _with_intent(graph: StudyGraph, **changes: object) -> StudyGraph:
    return graph.model_copy(update={"intent": graph.intent.model_copy(update=changes)})


def _require_visit(graph: StudyGraph, visit_id: str) -> Visit:
    visit = graph.visit(visit_id)
    if visit is None:
        raise OperationError(f"unknown visit {visit_id!r}")
    return visit


def _require_endpoint(graph: StudyGraph, endpoint_id: str) -> Endpoint:
    endpoint = graph.endpoint(endpoint_id)
    if endpoint is None:
        raise OperationError(f"unknown endpoint {endpoint_id!r}")
    return endpoint


def _replace_visit(graph: StudyGraph, new: Visit) -> StudyGraph:
    return _with_plan(graph, visits=tuple(new if v.id == new.id else v for v in graph.plan.visits))


class AddVisit(Model):
    type: Literal["AddVisit"] = "AddVisit"
    visit: Visit

    def apply(self, graph: StudyGraph) -> StudyGraph:
        return _with_plan(graph, visits=(*graph.plan.visits, self.visit))


class MoveVisit(Model):
    type: Literal["MoveVisit"] = "MoveVisit"
    visit_id: str
    day: int

    def apply(self, graph: StudyGraph) -> StudyGraph:
        visit = _require_visit(graph, self.visit_id)
        if visit.day == self.day:
            raise OperationError(f"visit {self.visit_id} is already on Day {self.day}")
        return _replace_visit(graph, visit.model_copy(update={"day": self.day}))


class SetVisitWindow(Model):
    type: Literal["SetVisitWindow"] = "SetVisitWindow"
    visit_id: str
    window: int = Field(ge=0)

    def apply(self, graph: StudyGraph) -> StudyGraph:
        visit = _require_visit(graph, self.visit_id)
        if visit.window == self.window:
            raise OperationError(f"visit {self.visit_id} already has window {self.window}")
        return _replace_visit(graph, visit.model_copy(update={"window": self.window}))


class RemoveVisit(Model):
    """Remove a visit and everything scheduled at it."""

    type: Literal["RemoveVisit"] = "RemoveVisit"
    visit_id: str

    def apply(self, graph: StudyGraph) -> StudyGraph:
        _require_visit(graph, self.visit_id)
        return _with_plan(
            graph,
            visits=tuple(v for v in graph.plan.visits if v.id != self.visit_id),
            schedule=tuple(c for c in graph.plan.schedule if c.visit_id != self.visit_id),
        )


class AddActivity(Model):
    type: Literal["AddActivity"] = "AddActivity"
    activity: Activity

    def apply(self, graph: StudyGraph) -> StudyGraph:
        return _with_plan(graph, activities=(*graph.plan.activities, self.activity))


class ScheduleActivity(Model):
    type: Literal["ScheduleActivity"] = "ScheduleActivity"
    visit_id: str
    activity_id: str

    def apply(self, graph: StudyGraph) -> StudyGraph:
        _require_visit(graph, self.visit_id)
        if graph.activity(self.activity_id) is None:
            raise OperationError(f"unknown activity {self.activity_id!r}")
        if graph.is_scheduled(self.visit_id, self.activity_id):
            raise OperationError(f"{self.activity_id} is already scheduled at {self.visit_id}")
        cell = ScheduledActivity(visit_id=self.visit_id, activity_id=self.activity_id)
        return _with_plan(graph, schedule=(*graph.plan.schedule, cell))


class UnscheduleActivity(Model):
    type: Literal["UnscheduleActivity"] = "UnscheduleActivity"
    visit_id: str
    activity_id: str

    def apply(self, graph: StudyGraph) -> StudyGraph:
        if not graph.is_scheduled(self.visit_id, self.activity_id):
            raise OperationError(f"{self.activity_id} is not scheduled at {self.visit_id}")
        cell = ScheduledActivity(visit_id=self.visit_id, activity_id=self.activity_id)
        return _with_plan(graph, schedule=tuple(c for c in graph.plan.schedule if c != cell))


class AddObjective(Model):
    type: Literal["AddObjective"] = "AddObjective"
    objective: Objective

    def apply(self, graph: StudyGraph) -> StudyGraph:
        return _with_intent(graph, objectives=(*graph.intent.objectives, self.objective))


class AddDesignActivity(Model):
    type: Literal["AddDesignActivity"] = "AddDesignActivity"
    design_activity: DesignActivity

    def apply(self, graph: StudyGraph) -> StudyGraph:
        return _with_intent(
            graph, design_activities=(*graph.intent.design_activities, self.design_activity)
        )


class AddEndpoint(Model):
    """Add an endpoint. New endpoints are secondary; use ChangePrimaryEndpoint to promote."""

    type: Literal["AddEndpoint"] = "AddEndpoint"
    endpoint: Endpoint

    def apply(self, graph: StudyGraph) -> StudyGraph:
        if self.endpoint.level != "secondary":
            raise OperationError("AddEndpoint only adds secondary endpoints")
        return _with_intent(graph, endpoints=(*graph.intent.endpoints, self.endpoint))


class ChangeEndpointTiming(Model):
    """Move an endpoint's timepoint to another study week."""

    type: Literal["ChangeEndpointTiming"] = "ChangeEndpointTiming"
    endpoint_id: str
    week: int = Field(ge=0)

    def apply(self, graph: StudyGraph) -> StudyGraph:
        endpoint = _require_endpoint(graph, self.endpoint_id)
        if endpoint.timepoint.week == self.week:
            raise OperationError(
                f"endpoint {self.endpoint_id} is already timed at Week {self.week}"
            )
        if self.week > graph.duration_weeks:
            raise OperationError(
                f"Week {self.week} is after the end of the {graph.duration_weeks} week study"
            )
        retimed = endpoint.model_copy(update={"timepoint": Timepoint(week=self.week)})
        return _with_intent(
            graph,
            endpoints=tuple(retimed if e.id == retimed.id else e for e in graph.intent.endpoints),
        )


class ChangePrimaryEndpoint(Model):
    """Promote an endpoint to primary; the previous primary becomes secondary."""

    type: Literal["ChangePrimaryEndpoint"] = "ChangePrimaryEndpoint"
    endpoint_id: str

    def apply(self, graph: StudyGraph) -> StudyGraph:
        target = _require_endpoint(graph, self.endpoint_id)
        if target.level == "primary":
            raise OperationError(f"endpoint {self.endpoint_id} is already primary")
        endpoints = tuple(
            e.model_copy(update={"level": "primary" if e.id == target.id else "secondary"})
            for e in graph.intent.endpoints
        )
        return _with_intent(graph, endpoints=endpoints)


class AddArm(Model):
    type: Literal["AddArm"] = "AddArm"
    arm: Arm

    def apply(self, graph: StudyGraph) -> StudyGraph:
        return _with_intent(graph, arms=(*graph.intent.arms, self.arm))


Operation = Annotated[
    AddVisit
    | MoveVisit
    | SetVisitWindow
    | RemoveVisit
    | AddActivity
    | ScheduleActivity
    | UnscheduleActivity
    | AddObjective
    | AddDesignActivity
    | AddEndpoint
    | ChangeEndpointTiming
    | ChangePrimaryEndpoint
    | AddArm,
    Field(discriminator="type"),
]

OPERATION_ADAPTER: TypeAdapter[Operation] = TypeAdapter(Operation)


def operation_types() -> tuple[str, ...]:
    """Names of every operation type the core supports."""
    schema = OPERATION_ADAPTER.json_schema()
    return tuple(sorted(schema["discriminator"]["mapping"]))


def apply_operation(graph: StudyGraph, operation: Operation) -> StudyGraph:
    """Apply ``operation`` and return the new graph, or raise ``OperationError``."""
    result = operation.apply(graph)
    problems = check_validity(result)
    if problems:
        raise OperationError(
            f"{operation.type} would make the study invalid: " + "; ".join(problems)
        )
    return result
