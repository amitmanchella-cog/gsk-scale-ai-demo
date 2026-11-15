"""The SQL adapter behaves exactly like the core's in-memory adapter."""

from __future__ import annotations

import pytest
from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import StudyService
from csd_core.domain.operations import (
    ChangeEndpointTiming,
    MoveVisit,
    Operation,
    OperationError,
    ScheduleActivity,
    SetVisitWindow,
    UnscheduleActivity,
)
from csd_core.ports.version_store import NotFoundError
from csd_core.reference.asthma import ACTIVITY_IDS, VISIT_IDS, reference_study
from hypothesis import given, settings
from hypothesis import strategies as st

from csd_api.sql_store import SqlVersionStore, make_engine

visit_ids = st.sampled_from(VISIT_IDS)
activity_ids = st.sampled_from(ACTIVITY_IDS)
operations: st.SearchStrategy[Operation] = st.one_of(
    st.builds(MoveVisit, visit_id=visit_ids, day=st.integers(-28, 420)),
    st.builds(SetVisitWindow, visit_id=visit_ids, window=st.integers(0, 14)),
    st.builds(ScheduleActivity, visit_id=visit_ids, activity_id=activity_ids),
    st.builds(UnscheduleActivity, visit_id=visit_ids, activity_id=activity_ids),
    st.builds(
        ChangeEndpointTiming,
        endpoint_id=st.sampled_from(["EP-FEV1", "EP-EXAC", "EP-ACQ5"]),
        week=st.integers(0, 52),
    ),
)


def sql_service() -> StudyService:
    return StudyService(SqlVersionStore(make_engine("sqlite://")))


@settings(max_examples=40, deadline=None)
@given(sequence=st.lists(operations, min_size=1, max_size=12))
def test_sql_store_matches_the_in_memory_store_for_any_sequence(
    sequence: list[Operation],
) -> None:
    sql, memory = sql_service(), StudyService(InMemoryVersionStore())
    sql_head = sql.create_study("s", reference_study())
    memory_head = memory.create_study("s", reference_study())

    for operation in sequence:
        try:
            memory_head = memory.apply(memory_head.id, operation)
        except OperationError:
            with pytest.raises(OperationError):
                sql.apply(sql_head.id, operation)
            continue
        parent = sql_head
        sql_head = sql.apply(sql_head.id, operation)
        # Every version keeps its parent link and round-trips through SQL unchanged.
        assert sql_head == memory_head
        assert sql_head.parent_id == parent.id
        assert sql.get_version(sql_head.id) == sql_head
        assert sql.get_version(parent.id) == parent

    assert sql.list_versions("s") == memory.list_versions("s")
    assert sql.list_branches("s") == memory.list_branches("s")
    assert sql.head("s") == memory.head("s")
    # Replaying the stored operations from the root gives the stored graph.
    assert sql.replay(sql_head.id) == sql_head.graph


def test_store_errors() -> None:
    store = SqlVersionStore(make_engine("sqlite://"))
    service = StudyService(store)
    root = service.create_study("s", reference_study())

    with pytest.raises(ValueError, match="already exists"):
        store.add_version(root)
    with pytest.raises(NotFoundError):
        store.get_version("v-nope")
    with pytest.raises(NotFoundError):
        store.get_branch("s", "nope")
    assert store.list_versions("nope") == []
    assert store.list_branches("nope") == []
    assert store.list_study_ids() == ["s"]
