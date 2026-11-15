from __future__ import annotations

import pytest

from csd_core.application.study_service import StudyService
from csd_core.domain.models import Activity, Endpoint, Timepoint, Visit
from csd_core.domain.operations import (
    OPERATION_ADAPTER,
    AddActivity,
    AddEndpoint,
    AddVisit,
    ChangePrimaryEndpoint,
    MoveVisit,
    Operation,
    OperationError,
    RemoveVisit,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
    operation_types,
)
from csd_core.domain.validity import check_validity
from csd_core.domain.versioning import Version
from examples import EXAMPLES


def test_at_least_ten_operation_types_and_each_has_an_example() -> None:
    assert len(operation_types()) >= 10
    assert set(EXAMPLES) == set(operation_types())
    required = {
        "AddVisit",
        "MoveVisit",
        "RemoveVisit",
        "AddActivity",
        "ScheduleActivity",
        "UnscheduleActivity",
        "AddEndpoint",
        "ChangePrimaryEndpoint",
        "AddArm",
    }
    assert required <= set(operation_types())


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_operation_creates_new_version_and_leaves_parent_unchanged(
    name: str, service: StudyService, root: Version
) -> None:
    operation = EXAMPLES[name]
    parent_before = root.model_dump_json()

    child = service.apply(root.id, operation)

    assert child.id != root.id
    assert child.parent_id == root.id
    assert child.seq == root.seq + 1
    assert child.operation == operation
    assert child.graph != root.graph
    assert check_validity(child.graph) == []
    assert service.get_version(root.id).model_dump_json() == parent_before
    assert service.head(root.study_id).id == child.id


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_operation_round_trips_through_json(name: str) -> None:
    operation = EXAMPLES[name]
    assert OPERATION_ADAPTER.validate_json(OPERATION_ADAPTER.dump_json(operation)) == operation


def test_move_visit_changes_only_the_day(service: StudyService, root: Version) -> None:
    child = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    moved = child.graph.visit("V-W12")
    assert moved is not None and moved.day == 99 and moved.name == "Week 12"
    assert child.graph.plan.schedule == root.graph.plan.schedule
    assert child.graph.intent == root.graph.intent


def test_remove_visit_removes_its_schedule_cells(service: StudyService, root: Version) -> None:
    child = service.apply(root.id, RemoveVisit(visit_id="V-W4"))
    assert child.graph.visit("V-W4") is None
    assert all(c.visit_id != "V-W4" for c in child.graph.plan.schedule)


def test_change_primary_endpoint_demotes_the_previous_primary(
    service: StudyService, root: Version
) -> None:
    child = service.apply(root.id, ChangePrimaryEndpoint(endpoint_id="EP-ACQ5"))
    levels = {e.id: e.level for e in child.graph.intent.endpoints}
    assert levels == {"EP-FEV1": "secondary", "EP-EXAC": "secondary", "EP-ACQ5": "primary"}


REJECTED: list[tuple[str, Operation]] = [
    ("unknown visit", MoveVisit(visit_id="V-NOPE", day=10)),
    ("same day", MoveVisit(visit_id="V-W12", day=85)),
    ("day taken", MoveVisit(visit_id="V-W12", day=29)),
    ("day zero", MoveVisit(visit_id="V-W12", day=0)),
    ("same window", SetVisitWindow(visit_id="V-W12", window=3)),
    ("unknown visit window", SetVisitWindow(visit_id="V-NOPE", window=3)),
    ("unknown visit remove", RemoveVisit(visit_id="V-NOPE")),
    ("duplicate visit id", AddVisit(visit=Visit(id="V-W4", name="Week 4 again", day=30))),
    ("duplicate id across kinds", AddVisit(visit=Visit(id="A-ICF", name="Clash", day=30))),
    (
        "duplicate activity",
        AddActivity(activity=Activity(id="A-ICF", name="ICF", unit_cost=1, duration_minutes=1)),
    ),
    (
        "unknown design activity",
        AddActivity(
            activity=Activity(
                id="A-X", name="X", unit_cost=1, duration_minutes=1, design_activity_id="DA-NOPE"
            )
        ),
    ),
    ("already scheduled", ScheduleActivity(visit_id="V-W4", activity_id="A-SPIRO")),
    ("unknown activity", ScheduleActivity(visit_id="V-W4", activity_id="A-NOPE")),
    ("unknown visit schedule", ScheduleActivity(visit_id="V-NOPE", activity_id="A-SPIRO")),
    ("not scheduled", UnscheduleActivity(visit_id="V-W4", activity_id="A-LABS")),
    ("already primary", ChangePrimaryEndpoint(endpoint_id="EP-FEV1")),
    ("unknown endpoint", ChangePrimaryEndpoint(endpoint_id="EP-NOPE")),
    (
        "second primary",
        AddEndpoint(
            endpoint=Endpoint(
                id="EP-2",
                name="Another primary",
                level="primary",
                objective_id="OBJ-PRIM",
                timepoint=Timepoint(week=12),
                design_activity_id="DA-SPIRO",
            )
        ),
    ),
    (
        "endpoint with unknown objective",
        AddEndpoint(
            endpoint=Endpoint(
                id="EP-2",
                name="Dangling",
                level="secondary",
                objective_id="OBJ-NOPE",
                timepoint=Timepoint(week=12),
                design_activity_id="DA-SPIRO",
            )
        ),
    ),
]


@pytest.mark.parametrize(("reason", "operation"), REJECTED, ids=[r for r, _ in REJECTED])
def test_invalid_operation_is_rejected_and_creates_no_version(
    reason: str, operation: Operation, service: StudyService, root: Version
) -> None:
    with pytest.raises(OperationError):
        service.apply(root.id, operation)
    assert service.list_versions(root.study_id) == [root]
    assert service.head(root.study_id) == root
