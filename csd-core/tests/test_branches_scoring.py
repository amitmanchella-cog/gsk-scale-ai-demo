"""Branches from any version, scores, and side-by-side compare."""

from __future__ import annotations

import pytest

from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import NotHeadError, StudyService
from csd_core.domain.compare import diff_graphs
from csd_core.domain.operations import (
    ChangePrimaryEndpoint,
    MoveVisit,
    OperationError,
    RemoveVisit,
    UnscheduleActivity,
)
from csd_core.domain.scoring import Score, score, visit_durations
from csd_core.domain.versioning import Version
from csd_core.ports.version_store import NotFoundError
from csd_core.reference.asthma import reference_study

# By hand from the unit costs and durations: visit minutes 120+110+90+105+105+95+15,
# visit costs 420+425+220+370+370+330+25. Week 4 alone is 90 minutes and 220.
REFERENCE_SCORE = Score(visit_count=7, patient_time_minutes=640, cost_proxy=2160)


def test_reference_study_score() -> None:
    graph = reference_study()
    assert score(graph) == REFERENCE_SCORE
    durations = visit_durations(graph)
    assert set(durations) == {v.id for v in graph.plan.visits}
    assert sum(durations.values()) == REFERENCE_SCORE.patient_time_minutes


def test_a_visit_with_nothing_scheduled_takes_no_time(service: StudyService, root: Version) -> None:
    v1 = service.apply(root.id, UnscheduleActivity(visit_id="V-FU", activity_id="A-AE"))
    assert visit_durations(v1.graph)["V-FU"] == 0
    assert service.score(v1.id).visit_count == 7


def test_branch_from_a_head_starts_at_its_base(service: StudyService, root: Version) -> None:
    branch = service.create_branch(root.id, "fewer-visits")
    assert (branch.base_version_id, branch.head_version_id) == (root.id, root.id)
    assert [b.name for b in service.list_branches(root.study_id)] == ["main", "fewer-visits"]
    assert service.head(root.study_id, "fewer-visits") == root
    # No version was created.
    assert [v.id for v in service.list_versions(root.study_id)] == [root.id]


def test_operations_on_a_branch_leave_main_alone(service: StudyService, root: Version) -> None:
    service.create_branch(root.id, "fewer-visits")
    b1 = service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="fewer-visits")
    assert (b1.branch, b1.parent_id, b1.seq) == ("fewer-visits", root.id, 1)
    assert service.head(root.study_id, "fewer-visits") == b1
    assert service.head(root.study_id) == root
    # Main still accepts operations on the same base, and the two heads differ.
    m1 = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    assert m1.branch == "main" and m1.id != b1.id
    assert service.get_version(root.id) == root
    # The branch continues from its own head without naming the branch again.
    b2 = service.apply(b1.id, UnscheduleActivity(visit_id="V-W24", activity_id="A-LABS"))
    assert b2.branch == "fewer-visits"
    assert [v.id for v in service.history(b2.id)] == [root.id, b1.id, b2.id]
    assert service.replay(b2.id) == b2.graph


def test_branch_from_a_version_that_is_not_a_head(service: StudyService, root: Version) -> None:
    v1 = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    with pytest.raises(NotHeadError):
        service.apply(root.id, RemoveVisit(visit_id="V-W4"))
    service.create_branch(root.id, "from-root")
    b1 = service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="from-root")
    assert b1.parent_id == root.id
    assert b1.findings == () and len(v1.findings) == 1


def test_branch_rules(service: StudyService, root: Version) -> None:
    service.create_branch(root.id, "alt")
    with pytest.raises(OperationError, match="already exists"):
        service.create_branch(root.id, "alt")
    with pytest.raises(OperationError, match="already exists"):
        service.create_branch(root.id, "main")
    with pytest.raises(OperationError, match="lower-case"):
        service.create_branch(root.id, "Not OK")
    with pytest.raises(NotFoundError):
        service.create_branch("v-missing", "x")
    with pytest.raises(NotFoundError):
        service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="missing")
    # Once a branch has moved on, its base is no longer its head.
    service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="alt")
    with pytest.raises(NotHeadError):
        service.apply(root.id, RemoveVisit(visit_id="V-W24"), branch="alt")


def test_fewer_visits_branch_scores_lower_than_main(service: StudyService, root: Version) -> None:
    service.create_branch(root.id, "fewer-visits")
    fewer = service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="fewer-visits")
    main, branch = service.score(root.id), service.score(fewer.id)
    assert branch.visit_count < main.visit_count
    assert branch.patient_time_minutes < main.patient_time_minutes
    assert branch.cost_proxy < main.cost_proxy
    # Exactly: one visit, and Week 4's spirometry, ACQ-5, vital signs, AE review and dispensing.
    assert branch == Score(visit_count=6, patient_time_minutes=550, cost_proxy=1940)


def test_compare_two_branches_side_by_side(service: StudyService, root: Version) -> None:
    service.create_branch(root.id, "fewer-visits")
    service.create_branch(root.id, "acq5-primary")
    fewer = service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="fewer-visits")
    acq5 = service.apply(
        root.id, ChangePrimaryEndpoint(endpoint_id="EP-ACQ5"), branch="acq5-primary"
    )

    comparison = service.compare(fewer.id, acq5.id)
    assert (comparison.left.version_id, comparison.left.branch) == (fewer.id, "fewer-visits")
    assert (comparison.right.version_id, comparison.right.branch) == (acq5.id, "acq5-primary")
    assert comparison.left.score == Score(visit_count=6, patient_time_minutes=550, cost_proxy=1940)
    assert comparison.right.score == REFERENCE_SCORE
    assert comparison.delta == Score(visit_count=1, patient_time_minutes=90, cost_proxy=220)
    assert comparison.left.findings == () and comparison.right.findings == ()

    changes = {(c.element_id, c.change) for c in comparison.changes}
    assert changes == {
        ("V-W4", "added"),
        ("V-W4:A-SPIRO", "added"),
        ("V-W4:A-ACQ5", "added"),
        ("V-W4:A-VITALS", "added"),
        ("V-W4:A-AE", "added"),
        ("V-W4:A-DISP", "added"),
        ("EP-FEV1", "changed"),
        ("EP-ACQ5", "changed"),
    }
    labels = {c.element_id: (c.element_type, c.label) for c in comparison.changes}
    assert labels["V-W4:A-SPIRO"] == ("scheduled activity", "Spirometry at Week 4")
    assert labels["V-W4"] == ("visit", "Week 4")

    # The other way round, added becomes removed and the delta changes sign.
    reverse = service.compare(acq5.id, fewer.id)
    assert reverse.delta.visit_count == -1
    assert ("V-W4", "removed") in {(c.element_id, c.change) for c in reverse.changes}


def test_compare_shows_findings_and_rejects_other_studies(
    service: StudyService, root: Version
) -> None:
    moved = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    comparison = service.compare(root.id, moved.id)
    assert comparison.left.findings == ()
    assert [f.id for f in comparison.right.findings] == ["unmet_endpoint_timepoint:EP-FEV1"]
    assert [(c.element_id, c.change) for c in comparison.changes] == [("V-W12", "changed")]
    assert comparison.delta == Score(visit_count=0, patient_time_minutes=0, cost_proxy=0)
    assert diff_graphs(root.graph, root.graph) == ()

    other = StudyService(InMemoryVersionStore())
    other_root = other.create_study("other", reference_study())
    service._store.add_version(other_root)  # noqa: SLF001
    with pytest.raises(OperationError, match="different studies"):
        service.compare(root.id, other_root.id)
