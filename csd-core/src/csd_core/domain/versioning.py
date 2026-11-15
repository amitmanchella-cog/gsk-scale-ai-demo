"""Immutable versions and branches."""

from __future__ import annotations

import hashlib
import json

from csd_core.domain.findings import Finding
from csd_core.domain.models import Model, StudyGraph
from csd_core.domain.operations import Operation

MAIN_BRANCH = "main"


class Version(Model):
    """One immutable state of the study, created by applying ``operation`` to its parent."""

    id: str
    study_id: str
    parent_id: str | None
    branch: str
    seq: int
    operation: Operation | None
    graph: StudyGraph
    findings: tuple[Finding, ...] = ()


class Branch(Model):
    study_id: str
    name: str
    base_version_id: str | None
    head_version_id: str


def version_id(
    study_id: str, parent_id: str | None, branch: str, operation: Operation | None
) -> str:
    """Deterministic ID: the same operation on the same parent and branch gives the same ID."""
    payload = json.dumps(
        [study_id, parent_id, branch, operation.model_dump(mode="json") if operation else None],
        sort_keys=True,
    )
    return "v-" + hashlib.sha256(payload.encode()).hexdigest()[:12]
