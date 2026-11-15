"""The flagship scenario, version by version.

Warning (not error) is the default agreed in the clarifying comment on MBA-3867.
"""

from __future__ import annotations

import pytest

from csd_core.application.study_service import StudyService
from csd_core.domain.operations import ChangeEndpointTiming, MoveVisit, OperationError
from csd_core.domain.schedule import schedule_grid
from csd_core.domain.versioning import Version
from csd_core.reference.asthma import ACTIVITY_IDS, SCHEDULE, VISIT_IDS

EXPECTED_MESSAGE = (
    'Primary endpoint "Change from baseline in trough FEV1" is timed at Week 12 (Day 85), '
    "but no visit performs Spirometry within its window of that day. "
    'The nearest is "Week 12" on Day 99 (window of 3 days).'
)


def test_flagship_scenario_reproduces_exactly(service: StudyService, root: Version) -> None:
    # v0: the clean reference study
    assert root.findings == ()
    assert root.graph.visit("V-W12").day == 85  # type: ignore[union-attr]

    # v1: MoveVisit Week 12 from Day 85 to Day 99 raises exactly one warning on FEV1
    v1 = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    assert v1.parent_id == root.id
    assert v1.graph.visit("V-W12").day == 99  # type: ignore[union-attr]
    [finding] = v1.findings
    assert finding.id == "unmet_endpoint_timepoint:EP-FEV1"
    assert finding.type == "unmet_endpoint_timepoint"
    assert finding.severity == "warning"
    assert finding.subject_id == "EP-FEV1"
    assert finding.element_ids == ("EP-FEV1", "DA-SPIRO")
    assert finding.message == EXPECTED_MESSAGE

    # v2: ChangeEndpointTiming of the primary endpoint to Week 14 clears it
    v2 = service.apply(v1.id, ChangeEndpointTiming(endpoint_id="EP-FEV1", week=14))
    assert v2.parent_id == v1.id
    endpoint = v2.graph.endpoint("EP-FEV1")
    assert endpoint is not None
    assert endpoint.level == "primary"
    assert (endpoint.timepoint.week, endpoint.timepoint.day) == (14, 99)
    assert v2.findings == ()

    # Each step is its own version, and earlier versions are unchanged
    assert [v.id for v in service.history(v2.id)] == [root.id, v1.id, v2.id]
    assert len({root.id, v1.id, v2.id}) == 3
    assert service.get_version(root.id).findings == ()
    assert service.get_version(v1.id).findings == (finding,)
    assert service.get_version(v1.id).graph.endpoint("EP-FEV1").timepoint.week == 12  # type: ignore[union-attr]
    assert service.replay(v2.id) == v2.graph


def test_change_endpoint_timing_rejections(service: StudyService, root: Version) -> None:
    for operation in (
        ChangeEndpointTiming(endpoint_id="EP-FEV1", week=12),  # no change
        ChangeEndpointTiming(endpoint_id="EP-FEV1", week=53),  # after the study ends
        ChangeEndpointTiming(endpoint_id="EP-NOPE", week=14),
    ):
        with pytest.raises(OperationError):
            service.apply(root.id, operation)
    assert service.head(root.study_id).id == root.id


def test_retiming_an_endpoint_to_a_week_without_a_visit_is_a_warning(
    service: StudyService, root: Version
) -> None:
    v1 = service.apply(root.id, ChangeEndpointTiming(endpoint_id="EP-FEV1", week=14))
    assert [f.id for f in v1.findings] == ["unmet_endpoint_timepoint:EP-FEV1"]


def test_schedule_grid_matches_the_reference_matrix(service: StudyService, root: Version) -> None:
    grid = schedule_grid(root.graph)
    assert tuple(v.id for v in grid.visits) == VISIT_IDS
    assert tuple(r.activity_id for r in grid.rows) == ACTIVITY_IDS
    for row in grid.rows:
        assert row.cells == tuple(v in SCHEDULE[row.activity_id] for v in VISIT_IDS)

    moved = service.apply(root.id, MoveVisit(visit_id="V-W12", day=200))
    assert [v.id for v in schedule_grid(moved.graph).visits] == [
        "V-SCR", "V-RAND", "V-W4", "V-W24", "V-W12", "V-W52", "V-FU",
    ]  # fmt: skip
