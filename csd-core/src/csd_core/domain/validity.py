"""Structural validity rules.

These are hard rules: an operation whose result breaks one is rejected and no
version is created. Intent-vs-plan consistency is reported separately as findings.
"""

from __future__ import annotations

from collections import Counter

from csd_core.domain.models import StudyGraph


def check_validity(graph: StudyGraph) -> list[str]:
    """Return the structural violations of ``graph`` (empty when valid)."""
    problems: list[str] = []
    intent, plan = graph.intent, graph.plan

    for dup, count in Counter(graph.node_ids()).items():
        if count > 1:
            problems.append(f"duplicate id {dup!r}")

    objective_ids = {o.id for o in intent.objectives}
    design_ids = {d.id for d in intent.design_activities}
    endpoint_ids = {e.id for e in intent.endpoints}
    visit_ids = {v.id for v in plan.visits}
    activity_ids = {a.id for a in plan.activities}

    for endpoint in intent.endpoints:
        if endpoint.objective_id not in objective_ids:
            problems.append(f"endpoint {endpoint.id} references unknown objective")
        if endpoint.design_activity_id not in design_ids:
            problems.append(f"endpoint {endpoint.id} references unknown design activity")
    primaries = [e.id for e in intent.endpoints if e.level == "primary"]
    if len(primaries) != 1:
        problems.append(f"exactly one primary endpoint is required, found {len(primaries)}")
    for estimand in intent.estimands:
        if estimand.endpoint_id not in endpoint_ids:
            problems.append(f"estimand {estimand.id} references unknown endpoint")
    if not intent.arms:
        problems.append("at least one arm is required")

    if not plan.visits:
        problems.append("at least one visit is required")
    for day, count in Counter(v.day for v in plan.visits).items():
        if count > 1:
            problems.append(f"{count} visits share study day {day}")
    for visit in plan.visits:
        if visit.day == 0:
            problems.append(f"visit {visit.id} is on Day 0, which does not exist")
    for activity in plan.activities:
        if (
            activity.design_activity_id is not None
            and activity.design_activity_id not in design_ids
        ):
            problems.append(f"activity {activity.id} references unknown design activity")
    for standard in plan.standards:
        if standard.activity_id not in activity_ids:
            problems.append(f"standard {standard.id} references unknown activity")
    for cell, count in Counter(plan.schedule).items():
        if count > 1:
            problems.append(f"schedule cell {cell.id} is duplicated")
        if cell.visit_id not in visit_ids:
            problems.append(f"schedule cell {cell.id} references unknown visit")
        if cell.activity_id not in activity_ids:
            problems.append(f"schedule cell {cell.id} references unknown activity")
    return problems
