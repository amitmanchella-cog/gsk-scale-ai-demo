"""Port for ProtoIQ, a future external agentic system. Nothing implements it for real yet.

The core only ever sees typed operations coming back, so whatever an agent proposes
goes through the same rules, findings and versioning as a human edit.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from csd_core.domain.models import StudyGraph
from csd_core.domain.operations import Operation


class ProtoIQ(Protocol):
    def propose_operations(self, graph: StudyGraph, goal: str) -> Sequence[Operation]:
        """Operations the agent suggests to move ``graph`` towards ``goal``."""
