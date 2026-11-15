from __future__ import annotations

import pytest

from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import NotHeadError, StudyService
from csd_core.domain.operations import MoveVisit, OperationError, RemoveVisit
from csd_core.domain.versioning import Version
from csd_core.ports.version_store import NotFoundError
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study
from examples import EXAMPLES


def test_root_version(service: StudyService, root: Version) -> None:
    assert root.parent_id is None
    assert root.operation is None
    assert root.seq == 0
    assert root.branch == "main"
    assert service.list_study_ids() == [REFERENCE_STUDY_ID]
    [branch] = service.list_branches(REFERENCE_STUDY_ID)
    assert (branch.name, branch.base_version_id, branch.head_version_id) == ("main", None, root.id)


def test_history_follows_parent_links(service: StudyService, root: Version) -> None:
    v1 = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    v2 = service.apply(v1.id, RemoveVisit(visit_id="V-W4"))
    assert [v.id for v in service.history(v2.id)] == [root.id, v1.id, v2.id]
    assert [v.id for v in service.list_versions(root.study_id)] == [root.id, v1.id, v2.id]
    assert service.replay(v2.id) == v2.graph


def test_only_a_branch_head_accepts_operations(service: StudyService, root: Version) -> None:
    service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    with pytest.raises(NotHeadError):
        service.apply(root.id, RemoveVisit(visit_id="V-W4"))


def test_version_ids_are_deterministic() -> None:
    ids = []
    for _ in range(2):
        service = StudyService(InMemoryVersionStore())
        version = service.create_study(REFERENCE_STUDY_ID, reference_study())
        for name in ("MoveVisit", "RemoveVisit", "AddArm"):
            version = service.apply(version.id, EXAMPLES[name])
        ids.append([v.id for v in service.history(version.id)])
    assert ids[0] == ids[1]
    assert len(set(ids[0])) == 4


def test_versions_are_immutable(root: Version) -> None:
    with pytest.raises(Exception, match="frozen"):
        root.seq = 5  # type: ignore[misc]
    with pytest.raises(Exception, match="frozen"):
        root.graph.plan.visits[0].day = 5  # type: ignore[misc]


def test_create_study_rejects_duplicates_and_invalid_graphs(
    service: StudyService, root: Version
) -> None:
    with pytest.raises(OperationError, match="already exists"):
        service.create_study(REFERENCE_STUDY_ID, reference_study())
    graph = reference_study()
    broken = graph.model_copy(update={"plan": graph.plan.model_copy(update={"visits": ()})})
    with pytest.raises(OperationError, match="invalid"):
        service.create_study("broken", broken)


def test_unknown_ids_raise_not_found(service: StudyService, root: Version) -> None:
    with pytest.raises(NotFoundError):
        service.get_version("v-nope")
    with pytest.raises(NotFoundError):
        service.list_versions("nope")
    with pytest.raises(NotFoundError):
        service.list_branches("nope")
    with pytest.raises(NotFoundError):
        service.head(REFERENCE_STUDY_ID, "nope")


def test_memory_store_rejects_duplicate_versions(root: Version) -> None:
    store = InMemoryVersionStore()
    store.add_version(root)
    with pytest.raises(ValueError, match="already exists"):
        store.add_version(root)
