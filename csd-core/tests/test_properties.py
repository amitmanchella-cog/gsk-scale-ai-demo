"""Property tests over random operation sequences on the reference study."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import StudyService
from csd_core.domain.operations import OperationError
from csd_core.domain.validity import check_validity
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study
from strategies import operations


@settings(max_examples=150, deadline=None)
@given(data=st.data(), steps=st.integers(min_value=1, max_value=15))
def test_any_sequence_of_valid_operations_keeps_the_graph_valid_and_replayable(
    data: st.DataObject, steps: int
) -> None:
    service = StudyService(InMemoryVersionStore())
    head = service.create_study(REFERENCE_STUDY_ID, reference_study())
    accepted = 0

    for _ in range(steps):
        operation = data.draw(operations(head.graph))
        parent_snapshot = head.model_dump_json()
        try:
            child = service.apply(head.id, operation)
        except OperationError:
            # A rejected operation creates nothing and moves nothing.
            assert service.head(REFERENCE_STUDY_ID).id == head.id
            continue
        accepted += 1

        # Any accepted operation produces a valid graph in a new version.
        assert check_validity(child.graph) == []
        # Every version keeps its parent link, and the parent is untouched.
        assert child.parent_id == head.id
        assert child.seq == head.seq + 1
        assert service.get_version(head.id).model_dump_json() == parent_snapshot
        head = child

    # The parent chain leads back to the root and has one version per accepted operation.
    history = service.history(head.id)
    assert len(history) == accepted + 1
    assert history[0].parent_id is None
    for parent, child in zip(history, history[1:], strict=False):
        assert child.parent_id == parent.id
    # Replaying a version's operations from the root gives the same graph.
    for version in history:
        assert service.replay(version.id) == version.graph
