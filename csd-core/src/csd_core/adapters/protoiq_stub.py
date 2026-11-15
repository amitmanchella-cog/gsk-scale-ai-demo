"""Stub adapter for the ProtoIQ port: makes no external call and proposes nothing."""

from __future__ import annotations

from collections.abc import Sequence

from csd_core.domain.models import StudyGraph
from csd_core.domain.operations import Operation


class StubProtoIQ:
    def propose_operations(self, graph: StudyGraph, goal: str) -> Sequence[Operation]:
        return ()
