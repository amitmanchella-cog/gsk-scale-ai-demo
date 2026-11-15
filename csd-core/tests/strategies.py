"""Hypothesis strategies that draw operations which fit the current graph."""

from __future__ import annotations

from hypothesis import strategies as st

from csd_core.domain.models import (
    Activity,
    Arm,
    DesignActivity,
    Endpoint,
    Objective,
    StudyGraph,
    Timepoint,
    Visit,
)
from csd_core.domain.operations import (
    AddActivity,
    AddArm,
    AddDesignActivity,
    AddEndpoint,
    AddObjective,
    AddVisit,
    ChangeEndpointTiming,
    ChangePrimaryEndpoint,
    MoveVisit,
    Operation,
    RemoveVisit,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
)

days = st.integers(min_value=-28, max_value=420)
names = st.text(alphabet="abcdefghij ", min_size=1, max_size=12)


def _fresh_id(graph: StudyGraph, prefix: str) -> str:
    taken = set(graph.node_ids())
    n = 1
    while f"{prefix}-{n}" in taken:
        n += 1
    return f"{prefix}-{n}"


@st.composite
def operations(draw: st.DrawFn, graph: StudyGraph) -> Operation:
    """Draw an operation. Most are valid for ``graph``; some are deliberately not."""
    visit_ids = [v.id for v in graph.plan.visits]
    activity_ids = [a.id for a in graph.plan.activities]
    design_ids = [d.id for d in graph.intent.design_activities]
    kind = draw(
        st.sampled_from(
            [
                "AddVisit",
                "MoveVisit",
                "SetVisitWindow",
                "RemoveVisit",
                "AddActivity",
                "ScheduleActivity",
                "UnscheduleActivity",
                "AddObjective",
                "AddDesignActivity",
                "AddEndpoint",
                "ChangeEndpointTiming",
                "ChangePrimaryEndpoint",
                "AddArm",
            ]
        )
    )
    if kind == "AddVisit":
        return AddVisit(
            visit=Visit(
                id=_fresh_id(graph, "V-NEW"),
                name=draw(names),
                day=draw(days),
                window=draw(st.integers(0, 14)),
                on_site=draw(st.booleans()),
            )
        )
    if kind == "MoveVisit":
        return MoveVisit(visit_id=draw(st.sampled_from(visit_ids)), day=draw(days))
    if kind == "SetVisitWindow":
        return SetVisitWindow(
            visit_id=draw(st.sampled_from(visit_ids)), window=draw(st.integers(0, 14))
        )
    if kind == "RemoveVisit":
        return RemoveVisit(visit_id=draw(st.sampled_from(visit_ids)))
    if kind == "AddActivity":
        return AddActivity(
            activity=Activity(
                id=_fresh_id(graph, "A-NEW"),
                name=draw(names),
                unit_cost=draw(st.integers(0, 500)),
                duration_minutes=draw(st.integers(0, 120)),
                design_activity_id=draw(st.none() | st.sampled_from(design_ids)),
            )
        )
    if kind in ("ScheduleActivity", "UnscheduleActivity"):
        visit_id = draw(st.sampled_from(visit_ids))
        activity_id = draw(st.sampled_from(activity_ids))
        if kind == "ScheduleActivity":
            return ScheduleActivity(visit_id=visit_id, activity_id=activity_id)
        return UnscheduleActivity(visit_id=visit_id, activity_id=activity_id)
    if kind == "AddObjective":
        return AddObjective(
            objective=Objective(id=_fresh_id(graph, "OBJ-NEW"), level="secondary", text=draw(names))
        )
    if kind == "AddDesignActivity":
        return AddDesignActivity(
            design_activity=DesignActivity(
                id=_fresh_id(graph, "DA-NEW"), name=draw(names), purpose=draw(names)
            )
        )
    if kind == "AddEndpoint":
        return AddEndpoint(
            endpoint=Endpoint(
                id=_fresh_id(graph, "EP-NEW"),
                name=draw(names),
                level="secondary",
                objective_id=draw(st.sampled_from([o.id for o in graph.intent.objectives])),
                timepoint=Timepoint(week=draw(st.integers(0, 60))),
                design_activity_id=draw(st.sampled_from(design_ids)),
            )
        )
    if kind == "ChangeEndpointTiming":
        return ChangeEndpointTiming(
            endpoint_id=draw(st.sampled_from([e.id for e in graph.intent.endpoints])),
            week=draw(st.integers(0, 60)),
        )
    if kind == "ChangePrimaryEndpoint":
        return ChangePrimaryEndpoint(
            endpoint_id=draw(st.sampled_from([e.id for e in graph.intent.endpoints]))
        )
    return AddArm(
        arm=Arm(
            id=_fresh_id(graph, "ARM-NEW"),
            name=draw(names),
            intervention=draw(names),
            ratio=draw(st.integers(1, 3)),
        )
    )
