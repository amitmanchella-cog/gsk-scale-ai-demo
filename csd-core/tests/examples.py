"""One valid example of every operation type against the reference study."""

from __future__ import annotations

from csd_core.domain.models import (
    Activity,
    Arm,
    DesignActivity,
    Endpoint,
    Objective,
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
    ChangePrimaryEndpoint,
    MoveVisit,
    Operation,
    RemoveVisit,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
)

EXAMPLES: dict[str, Operation] = {
    "AddVisit": AddVisit(visit=Visit(id="V-W36", name="Week 36", day=253, window=7)),
    "MoveVisit": MoveVisit(visit_id="V-W12", day=99),
    "SetVisitWindow": SetVisitWindow(visit_id="V-W12", window=14),
    "RemoveVisit": RemoveVisit(visit_id="V-W4"),
    "AddActivity": AddActivity(
        activity=Activity(id="A-ECG", name="ECG", unit_cost=60, duration_minutes=20)
    ),
    "ScheduleActivity": ScheduleActivity(visit_id="V-W4", activity_id="A-LABS"),
    "UnscheduleActivity": UnscheduleActivity(visit_id="V-W4", activity_id="A-ACQ5"),
    "AddObjective": AddObjective(
        objective=Objective(id="OBJ-SEC-QOL", level="secondary", text="To evaluate quality of life")
    ),
    "AddDesignActivity": AddDesignActivity(
        design_activity=DesignActivity(id="DA-ECG", name="ECG", purpose="Cardiac safety")
    ),
    "AddEndpoint": AddEndpoint(
        endpoint=Endpoint(
            id="EP-FEV1-W24",
            name="Change from baseline in trough FEV1",
            level="secondary",
            objective_id="OBJ-PRIM",
            timepoint=Timepoint(week=24),
            design_activity_id="DA-SPIRO",
        )
    ),
    "ChangePrimaryEndpoint": ChangePrimaryEndpoint(endpoint_id="EP-ACQ5"),
    "AddArm": AddArm(
        arm=Arm(id="ARM-DRUG-200", name="Drug 200 mg", intervention="Drug 200 mg", ratio=1)
    ),
}
