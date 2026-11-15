"""Seeded defect catalogue: broken variants of the reference study.

Each defect is a short list of operations applied to the clean reference study and the
exact set of findings the rules must then report.
"""

from __future__ import annotations

from csd_core.domain.findings import FindingType
from csd_core.domain.models import Activity, Endpoint, Model, StudyGraph, Timepoint, Visit
from csd_core.domain.operations import (
    AddActivity,
    AddEndpoint,
    AddVisit,
    MoveVisit,
    Operation,
    RemoveVisit,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
    apply_operation,
)
from csd_core.reference.asthma import reference_study


class SeededDefect(Model):
    id: str
    type: FindingType
    description: str
    operations: tuple[Operation, ...]
    expected_finding_ids: tuple[str, ...]

    def build(self) -> StudyGraph:
        """The broken variant of the reference study."""
        graph = reference_study()
        for operation in self.operations:
            graph = apply_operation(graph, operation)
        return graph


def _untraced(
    number: int, activity_id: str, name: str, cost: float, minutes: int, *visits: str
) -> SeededDefect:
    return SeededDefect(
        id=f"D{number:02d}",
        type="untraced_activity",
        description=f"{name} is scheduled at {', '.join(visits)} but traces to nothing",
        operations=(
            AddActivity(
                activity=Activity(
                    id=activity_id, name=name, unit_cost=cost, duration_minutes=minutes
                )
            ),
            *(ScheduleActivity(visit_id=v, activity_id=activity_id) for v in visits),
        ),
        expected_finding_ids=(f"untraced_activity:{activity_id}",),
    )


def _unmet(
    number: int,
    description: str,
    endpoint_id: str,
    *operations: Operation,
    also: tuple[str, ...] = (),
) -> SeededDefect:
    return SeededDefect(
        id=f"D{number:02d}",
        type="unmet_endpoint_timepoint",
        description=description,
        operations=operations,
        expected_finding_ids=(f"unmet_endpoint_timepoint:{endpoint_id}", *also),
    )


def _missing(
    number: int, description: str, pairs: tuple[tuple[str, str], ...], *ops: Operation
) -> SeededDefect:
    return SeededDefect(
        id=f"D{number:02d}",
        type="missing_operational_standard",
        description=description,
        operations=ops,
        expected_finding_ids=tuple(
            f"missing_operational_standard:{visit}:{standard}" for visit, standard in pairs
        ),
    )


DEFECT_CATALOGUE: tuple[SeededDefect, ...] = (
    # --- untraced activity ---------------------------------------------------------
    _untraced(1, "A-ECG", "ECG", 60, 20, "V-W12"),
    _untraced(2, "A-PK", "PK sampling", 90, 10, "V-W4", "V-W24"),
    _untraced(3, "A-CXR", "Chest X-ray", 110, 25, "V-SCR"),
    _untraced(4, "A-PREG", "Pregnancy test", 12, 5, "V-RAND"),
    _untraced(5, "A-FENO", "FeNO measurement", 45, 15, "V-W52"),
    _untraced(6, "A-DIARY", "Diary review", 10, 10, "V-FU"),
    _untraced(7, "A-PE", "Physical examination", 70, 20, "V-SCR", "V-W52"),
    _untraced(8, "A-GEN", "Genetic sample", 200, 10, "V-RAND"),
    # --- unmet endpoint timepoint --------------------------------------------------
    _unmet(
        9,
        "Week 12 visit moved to Day 99: FEV1 is no longer measured at Week 12",
        "EP-FEV1",
        MoveVisit(visit_id="V-W12", day=99),
    ),
    _unmet(
        10,
        "Spirometry dropped from the Week 12 visit",
        "EP-FEV1",
        UnscheduleActivity(visit_id="V-W12", activity_id="A-SPIRO"),
    ),
    _unmet(11, "Week 12 visit removed", "EP-FEV1", RemoveVisit(visit_id="V-W12")),
    _unmet(
        12,
        "Week 24 visit moved three weeks later: ACQ-5 is no longer measured at Week 24",
        "EP-ACQ5",
        MoveVisit(visit_id="V-W24", day=190),
    ),
    _unmet(
        13,
        "ACQ-5 dropped from the Week 24 visit",
        "EP-ACQ5",
        UnscheduleActivity(visit_id="V-W24", activity_id="A-ACQ5"),
    ),
    _unmet(
        14,
        "Adverse event review dropped from Week 52: exacerbations are not assessed at "
        "Week 52 (and the adverse event standard is broken)",
        "EP-EXAC",
        UnscheduleActivity(visit_id="V-W52", activity_id="A-AE"),
        also=("missing_operational_standard:V-W52:STD-AE",),
    ),
    _unmet(
        15,
        "Week 52 visit moved to Day 340, outside its 7 day window of Day 365",
        "EP-EXAC",
        MoveVisit(visit_id="V-W52", day=340),
    ),
    _unmet(
        16,
        "New FEV1 endpoint at Week 36 with no visit at Week 36",
        "EP-FEV1-W36",
        AddEndpoint(
            endpoint=Endpoint(
                id="EP-FEV1-W36",
                name="Change from baseline in trough FEV1",
                level="secondary",
                objective_id="OBJ-PRIM",
                timepoint=Timepoint(week=36),
                design_activity_id="DA-SPIRO",
            )
        ),
    ),
    _unmet(
        17,
        "Week 12 window tightened to 0 days and the visit moved by one day",
        "EP-FEV1",
        SetVisitWindow(visit_id="V-W12", window=0),
        MoveVisit(visit_id="V-W12", day=86),
    ),
    _unmet(18, "Week 24 visit removed", "EP-ACQ5", RemoveVisit(visit_id="V-W24")),
    # --- missing operational standard ----------------------------------------------
    _missing(
        19,
        "Vital signs dropped from the Week 4 visit",
        (("V-W4", "STD-VITALS"),),
        UnscheduleActivity(visit_id="V-W4", activity_id="A-VITALS"),
    ),
    _missing(
        20,
        "Informed consent dropped from screening",
        (("V-SCR", "STD-CONSENT"),),
        UnscheduleActivity(visit_id="V-SCR", activity_id="A-ICF"),
    ),
    _missing(
        21,
        "Eligibility check dropped from screening",
        (("V-SCR", "STD-ELIG"),),
        UnscheduleActivity(visit_id="V-SCR", activity_id="A-ELIG"),
    ),
    _missing(
        22,
        "Adverse event review dropped from the follow-up call",
        (("V-FU", "STD-AE"),),
        UnscheduleActivity(visit_id="V-FU", activity_id="A-AE"),
    ),
    _missing(
        23,
        "New on-site Week 36 visit with nothing scheduled",
        (("V-W36", "STD-VITALS"), ("V-W36", "STD-AE")),
        AddVisit(visit=Visit(id="V-W36", name="Week 36", day=253, window=7)),
    ),
    _missing(
        24,
        "New Week 8 phone call with nothing scheduled",
        (("V-W8", "STD-AE"),),
        AddVisit(visit=Visit(id="V-W8", name="Week 8 call", day=57, window=3, on_site=False)),
    ),
    _missing(
        25,
        "New re-screening visit with nothing scheduled",
        (("V-RESCR", "STD-CONSENT"), ("V-RESCR", "STD-ELIG"), ("V-RESCR", "STD-VITALS")),
        AddVisit(
            visit=Visit(id="V-RESCR", name="Re-screening", day=-7, window=3, kind="screening")
        ),
    ),
    _missing(
        26,
        "Vital signs dropped from the randomisation visit",
        (("V-RAND", "STD-VITALS"),),
        UnscheduleActivity(visit_id="V-RAND", activity_id="A-VITALS"),
    ),
)
