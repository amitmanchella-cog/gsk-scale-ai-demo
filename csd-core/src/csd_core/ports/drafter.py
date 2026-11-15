"""Drafting port. Providers turn a graph into M11 section drafts."""

from __future__ import annotations

from typing import Protocol

from csd_core.domain.drafting import DraftSection, SectionNumber
from csd_core.domain.models import StudyGraph


class DraftProvider(Protocol):
    @property
    def name(self) -> str:
        """Shown with every draft so a reader knows what wrote it."""

    def draft_section(self, graph: StudyGraph, number: SectionNumber) -> DraftSection:
        """Draft one section. Every sentence must carry IDs of elements of ``graph``."""
