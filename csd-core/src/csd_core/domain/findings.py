"""Intent-vs-plan consistency rules.

Findings are warnings: they never block an operation. They are recomputed for every
version and stored on it.
"""

from __future__ import annotations

from typing import Literal

from csd_core.domain.models import Model, StudyGraph, Visit

FindingType = Literal[
    "untraced_activity", "unmet_endpoint_timepoint", "missing_operational_standard"
]
FINDING_TYPES: tuple[FindingType, ...] = (
    "untraced_activity",
    "unmet_endpoint_timepoint",
    "missing_operational_standard",
)


class Finding(Model):
    """One inconsistency between the intent graph and the plan graph."""

    id: str
    type: FindingType
    severity: Literal["warning"] = "warning"
    subject_id: str
    message: str
    element_ids: tuple[str, ...]


def _untraced_activities(graph: StudyGraph) -> list[Finding]:
    """A scheduled activity that traces to no design activity or operational standard."""
    required_by_standard = {s.activity_id for s in graph.plan.standards}
    findings = []
    for activity in graph.plan.activities:
        cells = [c for c in graph.plan.schedule if c.activity_id == activity.id]
        if not cells or activity.design_activity_id or activity.id in required_by_standard:
            continue
        findings.append(
            Finding(
                id=f"untraced_activity:{activity.id}",
                type="untraced_activity",
                subject_id=activity.id,
                message=f'Activity "{activity.name}" is scheduled at {len(cells)} visit(s) but '
                "traces to no design activity or operational standard.",
                element_ids=(activity.id, *(c.id for c in cells)),
            )
        )
    return findings


def _unmet_endpoint_timepoints(graph: StudyGraph) -> list[Finding]:
    """An endpoint whose timepoint has no visit that performs the activity it needs."""
    design_names = {d.id: d.name for d in graph.intent.design_activities}
    measures = {a.id: a.design_activity_id for a in graph.plan.activities}
    findings = []
    for endpoint in graph.intent.endpoints:
        target = endpoint.timepoint.day
        performing = [
            v
            for v in graph.visits_by_day()
            if any(
                c.visit_id == v.id and measures[c.activity_id] == endpoint.design_activity_id
                for c in graph.plan.schedule
            )
        ]
        if any(abs(v.day - target) <= v.window for v in performing):
            continue
        needed = design_names[endpoint.design_activity_id]
        message = (
            f'{endpoint.level.capitalize()} endpoint "{endpoint.name}" is timed at '
            f"{endpoint.timepoint.label} (Day {target}), but no visit performs {needed} "
            "within its window of that day."
        )
        if performing:
            nearest = min(performing, key=lambda v: abs(v.day - target))
            message += (
                f' The nearest is "{nearest.name}" on Day {nearest.day} '
                f"(window of {nearest.window} days)."
            )
        findings.append(
            Finding(
                id=f"unmet_endpoint_timepoint:{endpoint.id}",
                type="unmet_endpoint_timepoint",
                subject_id=endpoint.id,
                message=message,
                element_ids=(endpoint.id, endpoint.design_activity_id),
            )
        )
    return findings


def standard_applies(scope: str, visit: Visit) -> bool:
    if scope == "screening":
        return visit.kind == "screening"
    if scope == "on_site":
        return visit.on_site
    return visit.day > 1  # post_baseline: every visit after randomisation (Day 1)


def _missing_operational_standards(graph: StudyGraph) -> list[Finding]:
    """A visit missing a required standard activity."""
    findings = []
    for visit in graph.visits_by_day():
        for standard in graph.plan.standards:
            if not standard_applies(standard.applies_to, visit):
                continue
            if graph.is_scheduled(visit.id, standard.activity_id):
                continue
            activity = graph.activity(standard.activity_id)
            assert activity is not None
            findings.append(
                Finding(
                    id=f"missing_operational_standard:{visit.id}:{standard.id}",
                    type="missing_operational_standard",
                    subject_id=visit.id,
                    message=f'Visit "{visit.name}" (Day {visit.day}) is missing '
                    f'"{activity.name}", required by the standard "{standard.name}".',
                    element_ids=(visit.id, standard.id, activity.id),
                )
            )
    return findings


def compute_findings(graph: StudyGraph) -> tuple[Finding, ...]:
    """All intent-vs-plan findings of a structurally valid graph, in a stable order."""
    return (
        *_untraced_activities(graph),
        *_unmet_endpoint_timepoints(graph),
        *_missing_operational_standards(graph),
    )
