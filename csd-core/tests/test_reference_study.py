from __future__ import annotations

from csd_core.domain.validity import check_validity
from csd_core.reference.asthma import ACTIVITY_IDS, SCHEDULE, VISIT_IDS, reference_study


def test_reference_study_is_structurally_valid() -> None:
    assert check_validity(reference_study()) == []


def test_reference_study_matches_the_brief() -> None:
    graph = reference_study()
    visits = [(v.name, v.day) for v in graph.visits_by_day()]
    assert visits == [
        ("Screening", -14),
        ("Randomisation", 1),
        ("Week 4", 29),
        ("Week 12", 85),
        ("Week 24", 169),
        ("Week 52", 365),
        ("Follow-up", 393),
    ]
    assert graph.visit("V-SCR").window == 7  # type: ignore[union-attr]
    assert [a.id for a in graph.plan.activities] == list(ACTIVITY_IDS)
    assert [v.id for v in graph.visits_by_day()] == list(VISIT_IDS)
    assert [(a.name, a.ratio) for a in graph.intent.arms] == [("Drug 100 mg", 1), ("Placebo", 1)]
    assert graph.duration_weeks == 52

    primary = [e for e in graph.intent.endpoints if e.level == "primary"]
    assert [(e.id, e.timepoint.label, e.timepoint.day) for e in primary] == [
        ("EP-FEV1", "Week 12", 85)
    ]
    secondary = {e.id: e.timepoint.label for e in graph.intent.endpoints if e.level == "secondary"}
    assert secondary == {"EP-EXAC": "Week 52", "EP-ACQ5": "Week 24"}


def test_reference_schedule_matrix() -> None:
    graph = reference_study()
    for activity_id in ACTIVITY_IDS:
        scheduled = tuple(v for v in VISIT_IDS if graph.is_scheduled(v, activity_id))
        assert scheduled == SCHEDULE[activity_id]
    assert len(graph.plan.schedule) == sum(len(v) for v in SCHEDULE.values())


def test_element_ids_cover_nodes_and_schedule_cells() -> None:
    graph = reference_study()
    ids = graph.element_ids()
    assert {"EP-FEV1", "V-W12", "A-SPIRO", "STD-VITALS", "ARM-PBO", "V-W12:A-SPIRO"} <= ids
    assert len(ids) == len(graph.node_ids()) + len(graph.plan.schedule)
