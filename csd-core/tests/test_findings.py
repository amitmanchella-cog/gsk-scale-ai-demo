from __future__ import annotations

import time
from collections import Counter

import pytest

from csd_core.application.study_service import StudyService
from csd_core.domain.findings import FINDING_TYPES, compute_findings
from csd_core.domain.models import Activity
from csd_core.domain.operations import (
    AddActivity,
    MoveVisit,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
)
from csd_core.domain.versioning import Version
from csd_core.reference.asthma import reference_study
from csd_core.reference.defects import DEFECT_CATALOGUE, SeededDefect
from examples import EXAMPLES


def test_clean_reference_study_has_zero_findings(root: Version) -> None:
    assert compute_findings(reference_study()) == ()
    assert root.findings == ()


def test_catalogue_has_at_least_20_defects_across_all_three_types() -> None:
    assert len(DEFECT_CATALOGUE) >= 20
    assert len({d.id for d in DEFECT_CATALOGUE}) == len(DEFECT_CATALOGUE)
    per_type = Counter(d.type for d in DEFECT_CATALOGUE)
    assert set(per_type) == set(FINDING_TYPES)
    assert all(count >= 5 for count in per_type.values())


@pytest.mark.parametrize("defect", DEFECT_CATALOGUE, ids=[d.id for d in DEFECT_CATALOGUE])
def test_every_seeded_defect_is_detected_with_the_right_finding(defect: SeededDefect) -> None:
    findings = compute_findings(defect.build())

    assert sorted(f.id for f in findings) == sorted(defect.expected_finding_ids)
    primary = next(f for f in findings if f.id == defect.expected_finding_ids[0])
    assert primary.type == defect.type
    assert primary.severity == "warning"


@pytest.mark.parametrize("defect", DEFECT_CATALOGUE, ids=[d.id for d in DEFECT_CATALOGUE])
def test_findings_only_reference_elements_of_the_graph(defect: SeededDefect) -> None:
    graph = defect.build()
    for finding in compute_findings(graph):
        assert finding.subject_id in graph.element_ids()
        assert set(finding.element_ids) <= graph.element_ids()


def test_findings_are_stored_on_every_version(service: StudyService, root: Version) -> None:
    v1 = service.apply(root.id, UnscheduleActivity(visit_id="V-W4", activity_id="A-VITALS"))
    v2 = service.apply(v1.id, ScheduleActivity(visit_id="V-W4", activity_id="A-VITALS"))
    assert [f.id for f in v1.findings] == ["missing_operational_standard:V-W4:STD-VITALS"]
    assert v2.findings == ()
    assert service.get_version(root.id).findings == ()


def test_an_unscheduled_untraced_activity_is_not_a_finding(
    service: StudyService, root: Version
) -> None:
    ecg = Activity(id="A-ECG", name="ECG", unit_cost=60, duration_minutes=20)
    v1 = service.apply(root.id, AddActivity(activity=ecg))
    assert v1.findings == ()
    v2 = service.apply(v1.id, ScheduleActivity(visit_id="V-W12", activity_id="A-ECG"))
    [finding] = v2.findings
    assert finding.type == "untraced_activity"
    assert finding.element_ids == ("A-ECG", "V-W12:A-ECG")


def test_a_wider_visit_window_keeps_the_endpoint_timepoint_met(
    service: StudyService, root: Version
) -> None:
    v1 = service.apply(root.id, SetVisitWindow(visit_id="V-W12", window=14))
    v2 = service.apply(v1.id, MoveVisit(visit_id="V-W12", day=99))
    assert v2.findings == ()


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_checks_run_in_under_one_second_per_operation(
    name: str, service: StudyService, root: Version
) -> None:
    start = time.perf_counter()
    child = service.apply(root.id, EXAMPLES[name])
    elapsed = time.perf_counter() - start

    assert child.findings == compute_findings(child.graph)
    assert elapsed < 1.0, f"{name} took {elapsed:.3f}s"


def test_checks_stay_under_one_second_over_a_long_history(
    service: StudyService, root: Version
) -> None:
    head = root
    slowest = 0.0
    for step in range(100):
        day = 99 if step % 2 == 0 else 85
        start = time.perf_counter()
        head = service.apply(head.id, MoveVisit(visit_id="V-W12", day=day))
        slowest = max(slowest, time.perf_counter() - start)
    assert head.seq == 100
    assert slowest < 1.0
