"""The schedule-of-activities grid: activities as rows, visits (by study day) as columns."""

from __future__ import annotations

from csd_core.domain.models import Model, StudyGraph


class GridVisit(Model):
    id: str
    name: str
    day: int
    window: int
    on_site: bool


class GridRow(Model):
    activity_id: str
    activity_name: str
    cells: tuple[bool, ...]


class ScheduleGrid(Model):
    visits: tuple[GridVisit, ...]
    rows: tuple[GridRow, ...]


def schedule_grid(graph: StudyGraph) -> ScheduleGrid:
    visits = graph.visits_by_day()
    scheduled = {(c.visit_id, c.activity_id) for c in graph.plan.schedule}
    return ScheduleGrid(
        visits=tuple(
            GridVisit(id=v.id, name=v.name, day=v.day, window=v.window, on_site=v.on_site)
            for v in visits
        ),
        rows=tuple(
            GridRow(
                activity_id=a.id,
                activity_name=a.name,
                cells=tuple((v.id, a.id) in scheduled for v in visits),
            )
            for a in graph.plan.activities
        ),
    )
