"""Side-by-side comparison of two versions: scores, findings and graph differences."""

from __future__ import annotations

from typing import Literal

from csd_core.domain.findings import Finding
from csd_core.domain.models import Model, StudyGraph
from csd_core.domain.scoring import Score, score
from csd_core.domain.versioning import Version

ChangeKind = Literal["added", "removed", "changed"]


class ElementChange(Model):
    """One graph element that differs, going from the left version to the right one."""

    element_id: str
    element_type: str
    change: ChangeKind
    label: str


class ComparedVersion(Model):
    version_id: str
    branch: str
    seq: int
    score: Score
    findings: tuple[Finding, ...]


class Comparison(Model):
    left: ComparedVersion
    right: ComparedVersion
    delta: Score
    """Right minus left: negative numbers mean the right version is lighter."""
    changes: tuple[ElementChange, ...]


def _elements(graph: StudyGraph) -> dict[str, tuple[str, str, object]]:
    """Every graph element by ID, as (type, label, value)."""
    activities = {activity.id: activity.name for activity in graph.plan.activities}
    visits = {visit.id: visit.name for visit in graph.plan.visits}
    elements: dict[str, tuple[str, str, object]] = {}
    for kind, items in (
        ("objective", graph.intent.objectives),
        ("estimand", graph.intent.estimands),
        ("endpoint", graph.intent.endpoints),
        ("design activity", graph.intent.design_activities),
        ("arm", graph.intent.arms),
        ("visit", graph.plan.visits),
        ("activity", graph.plan.activities),
        ("operational standard", graph.plan.standards),
    ):
        for item in items:
            label = getattr(item, "name", None) or getattr(item, "text", None) or item.id
            elements[item.id] = (kind, str(label), item)
    for cell in graph.plan.schedule:
        label = f"{activities[cell.activity_id]} at {visits[cell.visit_id]}"
        elements[cell.id] = ("scheduled activity", label, cell)
    return elements


def diff_graphs(left: StudyGraph, right: StudyGraph) -> tuple[ElementChange, ...]:
    """Elements added, removed or changed going from ``left`` to ``right``."""
    before, after = _elements(left), _elements(right)
    changes: list[ElementChange] = []
    for element_id, (kind, label, value) in before.items():
        if element_id not in after:
            changes.append(
                ElementChange(
                    element_id=element_id, element_type=kind, change="removed", label=label
                )
            )
        elif after[element_id][2] != value:
            changes.append(
                ElementChange(
                    element_id=element_id,
                    element_type=kind,
                    change="changed",
                    label=after[element_id][1],
                )
            )
    for element_id, (kind, label, _) in after.items():
        if element_id not in before:
            changes.append(
                ElementChange(element_id=element_id, element_type=kind, change="added", label=label)
            )
    return tuple(changes)


def _side(version: Version) -> ComparedVersion:
    return ComparedVersion(
        version_id=version.id,
        branch=version.branch,
        seq=version.seq,
        score=score(version.graph),
        findings=version.findings,
    )


def compare_versions(left: Version, right: Version) -> Comparison:
    a, b = _side(left), _side(right)
    return Comparison(
        left=a,
        right=b,
        delta=Score(
            visit_count=b.score.visit_count - a.score.visit_count,
            patient_time_minutes=b.score.patient_time_minutes - a.score.patient_time_minutes,
            cost_proxy=b.score.cost_proxy - a.score.cost_proxy,
        ),
        changes=diff_graphs(left.graph, right.graph),
    )
