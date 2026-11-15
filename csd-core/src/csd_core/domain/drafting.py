"""ICH M11 protocol section drafts with sentence-level traceability to the graph."""

from __future__ import annotations

from typing import Literal, get_args

from csd_core.domain.models import Model, StudyGraph

SectionNumber = Literal["3", "5", "8"]
SECTION_NUMBERS: tuple[SectionNumber, ...] = get_args(SectionNumber)
SECTION_TITLES: dict[SectionNumber, str] = {
    "3": "Trial Objectives and Associated Estimands",
    "5": "Trial Design",
    "8": "Trial Assessments and Procedures",
}


class Sentence(Model):
    """One drafted sentence and the IDs of the graph elements it was written from."""

    text: str
    element_ids: tuple[str, ...]


class DraftSection(Model):
    number: SectionNumber
    title: str
    sentences: tuple[Sentence, ...]


class Draft(Model):
    provider: str
    sections: tuple[DraftSection, ...]


def untraced_sentences(graph: StudyGraph, section: DraftSection) -> list[str]:
    """Sentences with no element ID, or with an ID that is not in ``graph``."""
    known = graph.element_ids()
    return [
        sentence.text
        for sentence in section.sentences
        if not sentence.element_ids or not known.issuperset(sentence.element_ids)
    ]
