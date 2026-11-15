"""Deterministic template provider for M11 drafts. Offline: no model calls.

The same graph always gives the same text, and each sentence lists the graph
elements whose values appear in it.
"""

from __future__ import annotations

from csd_core.domain.drafting import SECTION_TITLES, DraftSection, SectionNumber, Sentence
from csd_core.domain.models import StudyGraph, Visit


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _lower(text: str) -> str:
    """Lower-case the first letter for mid-sentence use, leaving acronyms such as ACQ-5."""
    first = text.split(" ", 1)[0]
    if not first or sum(c.isupper() or c.isdigit() for c in first) > 1:
        return text
    return text[0].lower() + text[1:]


def _window(visit: Visit) -> str:
    return f" (window of {visit.window} days either side)" if visit.window else ""


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class TemplateDraftProvider:
    name = "template"

    def draft_section(self, graph: StudyGraph, number: SectionNumber) -> DraftSection:
        writers = {"3": _objectives, "5": _design, "8": _assessments}
        sentences = tuple(s for s in writers[number](graph) if s.element_ids)
        return DraftSection(number=number, title=SECTION_TITLES[number], sentences=sentences)


def _objectives(graph: StudyGraph) -> list[Sentence]:
    intent = graph.intent
    design_activities = {d.id: d for d in intent.design_activities}
    out: list[Sentence] = []
    ordered = sorted(intent.objectives, key=lambda o: o.level != "primary")
    for objective in ordered:
        out.append(
            Sentence(
                text=f"The {objective.level} objective is: {_lower(objective.text)}.",
                element_ids=(objective.id,),
            )
        )
        for endpoint in intent.endpoints:
            if endpoint.objective_id != objective.id:
                continue
            activity = design_activities.get(endpoint.design_activity_id)
            how = f", assessed by {_lower(activity.name)}" if activity else ""
            out.append(
                Sentence(
                    text=f"The {endpoint.level} endpoint for this objective is "
                    f"{_lower(endpoint.name)} at "
                    f"{endpoint.timepoint.label}{how}.",
                    element_ids=(endpoint.id, objective.id, *([activity.id] if activity else [])),
                )
            )
            for estimand in intent.estimands:
                if estimand.endpoint_id == endpoint.id:
                    out.append(
                        Sentence(
                            text=f"The estimand for this endpoint is defined in "
                            f"{_lower(estimand.population)}, "
                            f"handles intercurrent events with a "
                            f"{_lower(estimand.intercurrent_event_strategy)} strategy and is "
                            f"summarised as the {_lower(estimand.summary_measure)}.",
                            element_ids=(estimand.id, endpoint.id),
                        )
                    )
    return out


def _design(graph: StudyGraph) -> list[Sentence]:
    intent = graph.intent
    arms = intent.arms
    arm_ids = tuple(a.id for a in arms)
    visits = graph.visits_by_day()
    assignment = intent.assignment
    out = [
        Sentence(
            text=f"This is a {graph.phase}, {assignment.method}, {assignment.blinding}, "
            f"{assignment.control}-controlled study in {_lower(graph.indication)} with "
            f"{_plural(len(arms), 'arm')}.",
            element_ids=arm_ids,
        )
    ]
    out.extend(
        Sentence(
            text=f"Participants in the {arm.name} arm receive {arm.intervention}.",
            element_ids=(arm.id,),
        )
        for arm in arms
    )
    if len(arms) > 1:
        verb = "randomised" if assignment.method == "randomised" else "assigned"
        out.append(
            Sentence(
                text=f"Participants are {verb} to {_join([a.name for a in arms])} in a "
                f"{':'.join(str(a.ratio) for a in arms)} ratio.",
                element_ids=arm_ids,
            )
        )
    if visits:
        first, last = visits[0], visits[-1]
        out.append(
            Sentence(
                text=f"The study lasts {graph.duration_weeks} weeks and each participant "
                f"attends {_plural(len(visits), 'visit')}, from {first.name} (Day {first.day}) "
                f"to {last.name} (Day {last.day}).",
                element_ids=tuple(v.id for v in visits),
            )
        )
        remote = [v for v in visits if not v.on_site]
        if remote:
            out.append(
                Sentence(
                    text=f"{_join([v.name for v in remote])} "
                    f"{'is' if len(remote) == 1 else 'are'} conducted remotely.",
                    element_ids=tuple(v.id for v in remote),
                )
            )
    out.extend(
        Sentence(
            text=f"The primary endpoint, {_lower(endpoint.name)}, is "
            f"assessed at {endpoint.timepoint.label} (Day {endpoint.timepoint.day}).",
            element_ids=(endpoint.id,),
        )
        for endpoint in intent.endpoints
        if endpoint.level == "primary"
    )
    return out


def _assessments(graph: StudyGraph) -> list[Sentence]:
    plan = graph.plan
    visits = graph.visits_by_day()
    visit_names = {v.id: v.name for v in visits}
    activity_names = {a.id: a.name for a in plan.activities}
    design_activities = {d.id: d for d in graph.intent.design_activities}
    out: list[Sentence] = []
    for visit in visits:
        cells = [c for a in plan.activities for c in plan.schedule if c.id == f"{visit.id}:{a.id}"]
        where = "on site" if visit.on_site else "remotely"
        if cells:
            names = _join([_lower(activity_names[c.activity_id]) for c in cells])
            text = (
                f"{visit.name} takes place {where} on Day {visit.day}{_window(visit)} and "
                f"includes {names}."
            )
        else:
            text = (
                f"{visit.name} takes place {where} on Day {visit.day}{_window(visit)} with no "
                f"scheduled activities."
            )
        out.append(Sentence(text=text, element_ids=(visit.id, *(c.id for c in cells))))
    for activity in plan.activities:
        cells = [c for v in visits for c in plan.schedule if c.id == f"{v.id}:{activity.id}"]
        design = design_activities.get(activity.design_activity_id or "")
        why = f" to support {_lower(design.name)} ({_lower(design.purpose)})" if design else ""
        if cells:
            text = (
                f"{activity.name} is performed at {_plural(len(cells), 'visit')}{why}: "
                f"{_join([visit_names[c.visit_id] for c in cells])}."
            )
        else:
            text = f"{activity.name} is not scheduled at any visit."
        out.append(
            Sentence(
                text=text,
                element_ids=(
                    activity.id,
                    *([design.id] if design else []),
                    *(c.id for c in cells),
                ),
            )
        )
    scopes = {
        "screening": "at screening",
        "on_site": "at every on-site visit",
        "post_baseline": "at every visit after randomisation",
    }
    out.extend(
        Sentence(
            text=f"As an operational standard, {_lower(activity_names[standard.activity_id])} "
            f"is required {scopes[standard.applies_to]}.",
            element_ids=(standard.id, standard.activity_id),
        )
        for standard in plan.standards
        if standard.activity_id in activity_names
    )
    return out
