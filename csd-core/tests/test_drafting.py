"""M11 drafts: offline, deterministic, and every sentence traces to the graph."""

from __future__ import annotations

import socket

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.adapters.protoiq_stub import StubProtoIQ
from csd_core.adapters.template_drafter import TemplateDraftProvider
from csd_core.application.study_service import StudyService, UntracedDraftError
from csd_core.domain.drafting import (
    SECTION_TITLES,
    DraftSection,
    SectionNumber,
    Sentence,
    untraced_sentences,
)
from csd_core.domain.models import StudyGraph, Visit
from csd_core.domain.operations import (
    AddVisit,
    ChangeEndpointTiming,
    MoveVisit,
    OperationError,
    RemoveVisit,
    UnscheduleActivity,
)
from csd_core.domain.versioning import Version
from csd_core.ports.drafter import DraftProvider
from csd_core.ports.protoiq import ProtoIQ
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study
from strategies import operations


def _texts(service: StudyService, version: Version, number: SectionNumber) -> list[str]:
    return [s.text for s in service.draft(version.id, (number,)).sections[0].sentences]


def test_the_three_sections_are_drafted_by_the_template_provider(
    service: StudyService, root: Version
) -> None:
    draft = service.draft(root.id)

    assert draft.provider == "template"
    assert [(s.number, s.title) for s in draft.sections] == [
        ("3", "Trial Objectives and Associated Estimands"),
        ("5", "Trial Design"),
        ("8", "Trial Assessments and Procedures"),
    ]
    assert all(section.sentences for section in draft.sections)


def test_every_sentence_carries_element_ids_that_exist_in_that_version(
    service: StudyService, root: Version
) -> None:
    known = root.graph.element_ids()
    for section in service.draft(root.id).sections:
        for sentence in section.sentences:
            assert sentence.element_ids, sentence.text
            assert set(sentence.element_ids) <= known, sentence.text


def test_section_3_states_objectives_endpoints_and_estimands(
    service: StudyService, root: Version
) -> None:
    section = service.draft(root.id, ("3",)).sections[0]

    assert section.sentences[0] == Sentence(
        text="The primary objective is: to evaluate the effect of Drug 100 mg compared with "
        "placebo on lung function.",
        element_ids=("OBJ-PRIM",),
    )
    assert section.sentences[1] == Sentence(
        text="The primary endpoint for this objective is change from baseline in trough FEV1 "
        "at Week 12, assessed by spirometry.",
        element_ids=("EP-FEV1", "OBJ-PRIM", "DA-SPIRO"),
    )
    assert section.sentences[2] == Sentence(
        text="The estimand for this endpoint is defined in adults with moderate to severe "
        "asthma, handles intercurrent events with a treatment policy strategy and is "
        "summarised as the difference in mean change from baseline.",
        element_ids=("EST-FEV1", "EP-FEV1"),
    )
    assert len(section.sentences) == 9


def test_section_5_states_the_design(service: StudyService, root: Version) -> None:
    assert _texts(service, root, "5") == [
        "This is a Phase 3, randomised, double-blind, placebo-controlled study in asthma "
        "with 2 arms.",
        "Participants in the Drug 100 mg arm receive Drug 100 mg.",
        "Participants in the Placebo arm receive Matching placebo.",
        "Participants are randomised to Drug 100 mg and Placebo in a 1:1 ratio.",
        "The study lasts 52 weeks and each participant attends 7 visits, from Screening "
        "(Day -14) to Follow-up (Day 393).",
        "Follow-up is conducted remotely.",
        "The primary endpoint, change from baseline in trough FEV1, is assessed at Week 12 "
        "(Day 85).",
    ]


def test_section_8_has_a_sentence_per_visit_activity_and_standard(
    service: StudyService, root: Version
) -> None:
    section = service.draft(root.id, ("8",)).sections[0]
    plan = root.graph.plan

    assert len(section.sentences) == len(plan.visits) + len(plan.activities) + len(plan.standards)
    week4 = next(s for s in section.sentences if s.text.startswith("Week 4 "))
    assert week4.text == (
        "Week 4 takes place on site on Day 29 (window of 3 days either side) and includes "
        "spirometry, ACQ-5, vital signs, adverse event review and study drug dispensing."
    )
    assert week4.element_ids == (
        "V-W4",
        "V-W4:A-SPIRO",
        "V-W4:A-ACQ5",
        "V-W4:A-VITALS",
        "V-W4:A-AE",
        "V-W4:A-DISP",
    )
    consent = next(s for s in section.sentences if s.text.startswith("Informed consent "))
    assert consent.text == "Informed consent is performed at 1 visit: Screening."
    assert consent.element_ids == ("A-ICF", "V-SCR:A-ICF")
    spirometry = next(s for s in section.sentences if s.text.startswith("Spirometry "))
    assert spirometry.text == (
        "Spirometry is performed at 6 visits to support spirometry (trough FEV1): Screening, "
        "Randomisation, Week 4, Week 12, Week 24 and Week 52."
    )
    assert spirometry.element_ids[:2] == ("A-SPIRO", "DA-SPIRO")


def test_the_draft_follows_the_graph_version_by_version(
    service: StudyService, root: Version
) -> None:
    moved = service.apply(root.id, MoveVisit(visit_id="V-W12", day=99))
    retimed = service.apply(moved.id, ChangeEndpointTiming(endpoint_id="EP-FEV1", week=14))

    assert any("Week 12 takes place on site on Day 99" in t for t in _texts(service, moved, "8"))
    assert any("Week 12 takes place on site on Day 85" in t for t in _texts(service, root, "8"))
    assert _texts(service, retimed, "5")[-1] == (
        "The primary endpoint, change from baseline in trough FEV1, is assessed at Week 14 "
        "(Day 99)."
    )
    assert "at Week 14, assessed by spirometry." in _texts(service, retimed, "3")[1]


def test_removed_elements_leave_the_draft(service: StudyService, root: Version) -> None:
    removed = service.apply(root.id, RemoveVisit(visit_id="V-W4"))
    draft = service.draft(removed.id)

    ids = {i for section in draft.sections for s in section.sentences for i in s.element_ids}
    assert not any(i.startswith("V-W4") for i in ids)
    assert "attends 6 visits" in _texts(service, removed, "5")[4]


def test_empty_visits_and_unscheduled_activities_are_still_drafted(
    service: StudyService, root: Version
) -> None:
    added = service.apply(root.id, AddVisit(visit=Visit(id="V-W36", name="Week 36", day=253)))
    version = service.apply(added.id, UnscheduleActivity(visit_id="V-SCR", activity_id="A-ICF"))
    texts = _texts(service, version, "8")

    assert "Week 36 takes place on site on Day 253 with no scheduled activities." in texts
    assert "Informed consent is not scheduled at any visit." in texts


def test_drafting_is_deterministic(service: StudyService, root: Version) -> None:
    assert service.draft(root.id) == service.draft(root.id)
    assert TemplateDraftProvider().draft_section(
        reference_study(), "8"
    ) == TemplateDraftProvider().draft_section(reference_study(), "8")


def test_drafting_makes_no_network_call(
    service: StudyService, root: Version, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the template provider must run offline")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    assert len(service.draft(root.id).sections) == 3


class _Hallucinating:
    name = "hallucinating"

    def __init__(self, element_ids: tuple[str, ...]) -> None:
        self._element_ids = element_ids

    def draft_section(self, graph: StudyGraph, number: SectionNumber) -> DraftSection:
        return DraftSection(
            number=number,
            title=SECTION_TITLES[number],
            sentences=(Sentence(text="Invented.", element_ids=self._element_ids),),
        )


@pytest.mark.parametrize("element_ids", [(), ("V-NOPE",), ("V-W4", "V-NOPE")])
def test_a_provider_whose_sentence_does_not_trace_is_refused(element_ids: tuple[str, ...]) -> None:
    provider: DraftProvider = _Hallucinating(element_ids)
    service = StudyService(InMemoryVersionStore(), drafter=provider)
    root = service.create_study(REFERENCE_STUDY_ID, reference_study())

    with pytest.raises(UntracedDraftError, match="Invented"):
        service.draft(root.id)
    section = provider.draft_section(root.graph, "3")
    assert untraced_sentences(root.graph, section) == ["Invented."]


def test_the_protoiq_stub_fits_the_port_and_proposes_nothing() -> None:
    agent: ProtoIQ = StubProtoIQ()

    assert agent.propose_operations(reference_study(), "fewer visits") == ()


@settings(max_examples=60, deadline=None)
@given(data=st.data(), steps=st.integers(min_value=1, max_value=12))
def test_drafts_trace_to_the_graph_after_any_sequence_of_operations(
    data: st.DataObject, steps: int
) -> None:
    service = StudyService(InMemoryVersionStore())
    head = service.create_study(REFERENCE_STUDY_ID, reference_study())
    for _ in range(steps):
        try:
            head = service.apply(head.id, data.draw(operations(head.graph)))
        except OperationError:
            continue

    known = head.graph.element_ids()
    for section in service.draft(head.id).sections:
        for sentence in section.sentences:
            assert sentence.element_ids
            assert set(sentence.element_ids) <= known
