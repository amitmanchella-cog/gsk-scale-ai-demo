"""Application service: create studies and apply operations to versions."""

from __future__ import annotations

import re

from csd_core.domain.compare import Comparison, compare_versions
from csd_core.domain.findings import compute_findings
from csd_core.domain.models import StudyGraph
from csd_core.domain.operations import Operation, OperationError, apply_operation
from csd_core.domain.scoring import Score, score
from csd_core.domain.validity import check_validity
from csd_core.domain.versioning import MAIN_BRANCH, Branch, Version, version_id
from csd_core.ports.version_store import NotFoundError, VersionStore


class NotHeadError(OperationError):
    """Operations can only be applied to the head version of a branch."""


BRANCH_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class StudyService:
    def __init__(self, store: VersionStore) -> None:
        self._store = store

    # --- commands -----------------------------------------------------------------

    def create_study(self, study_id: str, graph: StudyGraph) -> Version:
        """Store ``graph`` as the root version of a new study on the main branch."""
        if study_id in self._store.list_study_ids():
            raise OperationError(f"study {study_id!r} already exists")
        problems = check_validity(graph)
        if problems:
            raise OperationError("the study is invalid: " + "; ".join(problems))
        root = self._build_version(study_id, None, MAIN_BRANCH, 0, None, graph)
        self._store.add_version(root)
        self._store.save_branch(
            Branch(
                study_id=study_id, name=MAIN_BRANCH, base_version_id=None, head_version_id=root.id
            )
        )
        return root

    def create_branch(self, version_id_: str, name: str) -> Branch:
        """Start a branch from any version, head or not. No version is created.

        The branch's head is the base version until the first operation is applied
        to it with ``apply(base_version_id, operation, branch=name)``.
        """
        base = self._store.get_version(version_id_)
        if not BRANCH_NAME.match(name):
            raise OperationError(
                f"branch name {name!r} must be lower-case letters, digits and dashes"
            )
        if any(branch.name == name for branch in self._store.list_branches(base.study_id)):
            raise OperationError(f"branch {name!r} already exists")
        branch = Branch(
            study_id=base.study_id, name=name, base_version_id=base.id, head_version_id=base.id
        )
        self._store.save_branch(branch)
        return branch

    def apply(self, version_id_: str, operation: Operation, branch: str | None = None) -> Version:
        """Apply ``operation`` to a branch head and return the new version.

        ``branch`` defaults to the branch the version was created on; name another
        branch to apply the first operation of a branch to its base version.

        The parent version is left unchanged. Findings are recomputed for the new
        version. Raises ``OperationError`` when the operation is not applicable or
        would make the graph structurally invalid.
        """
        parent = self._store.get_version(version_id_)
        target = self._store.get_branch(parent.study_id, branch or parent.branch)
        if target.head_version_id != parent.id:
            raise NotHeadError(
                f"version {parent.id} is not the head of branch {target.name!r}; "
                "create a branch from it to change it"
            )
        graph = apply_operation(parent.graph, operation)
        child = self._build_version(
            parent.study_id, parent.id, target.name, parent.seq + 1, operation, graph
        )
        self._store.add_version(child)
        self._store.save_branch(target.model_copy(update={"head_version_id": child.id}))
        return child

    # --- queries ------------------------------------------------------------------

    def get_version(self, version_id_: str) -> Version:
        return self._store.get_version(version_id_)

    def head(self, study_id: str, branch: str = MAIN_BRANCH) -> Version:
        return self._store.get_version(self._store.get_branch(study_id, branch).head_version_id)

    def list_study_ids(self) -> list[str]:
        return self._store.list_study_ids()

    def list_versions(self, study_id: str) -> list[Version]:
        versions = self._store.list_versions(study_id)
        if not versions:
            raise NotFoundError(f"study {study_id!r} not found")
        return versions

    def list_branches(self, study_id: str) -> list[Branch]:
        branches = self._store.list_branches(study_id)
        if not branches:
            raise NotFoundError(f"study {study_id!r} not found")
        return branches

    def score(self, version_id_: str) -> Score:
        return score(self._store.get_version(version_id_).graph)

    def compare(self, left_version_id: str, right_version_id: str) -> Comparison:
        """Compare two versions of the same study side by side."""
        left = self._store.get_version(left_version_id)
        right = self._store.get_version(right_version_id)
        if left.study_id != right.study_id:
            raise OperationError("versions of different studies cannot be compared")
        return compare_versions(left, right)

    def history(self, version_id_: str) -> list[Version]:
        """The chain of versions from the root to ``version_id_``, following parent links."""
        chain = [self._store.get_version(version_id_)]
        while chain[-1].parent_id is not None:
            chain.append(self._store.get_version(chain[-1].parent_id))
        chain.reverse()
        return chain

    def replay(self, version_id_: str) -> StudyGraph:
        """Rebuild a version's graph by replaying its operations from the root graph."""
        chain = self.history(version_id_)
        graph = chain[0].graph
        for version in chain[1:]:
            assert version.operation is not None
            graph = apply_operation(graph, version.operation)
        return graph

    # --- internals ----------------------------------------------------------------

    def _build_version(
        self,
        study_id: str,
        parent_id: str | None,
        branch: str,
        seq: int,
        operation: Operation | None,
        graph: StudyGraph,
    ) -> Version:
        return Version(
            id=version_id(study_id, parent_id, branch, operation),
            study_id=study_id,
            parent_id=parent_id,
            branch=branch,
            seq=seq,
            operation=operation,
            graph=graph,
            findings=compute_findings(graph),
        )
