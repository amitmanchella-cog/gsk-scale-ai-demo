"""Competing recruiting trials per planned country."""

from __future__ import annotations

from pda_api.benchmark import RecruitingTrial
from pda_api.schemas import CompetingTrial, CountryCompetition, Level, ProtocolDesign

MAX_LISTED = 25
# Number of recruiting trials of the same indication in a country.
CROWDED = 10
BUSY = 4


def crowding(n_trials: int) -> Level:
    return "high" if n_trials >= CROWDED else "moderate" if n_trials >= BUSY else "low"


def competing_by_country(design: ProtocolDesign, recruiting: tuple[RecruitingTrial, ...]) -> list[CountryCompetition]:
    out: list[CountryCompetition] = []
    for planned in design.planned_countries:
        rows = sorted(
            (row for row in recruiting if row.indication == design.indication and row.country == planned.country),
            key=lambda row: (-row.sites_in_country, row.nct_id),
        )
        out.append(
            CountryCompetition(
                country=planned.country,
                planned_sites=planned.sites,
                competing_trials=len(rows),
                competing_sites=sum(row.sites_in_country for row in rows),
                crowding=crowding(len(rows)),
                trials=[
                    CompetingTrial(
                        nct_id=row.nct_id,
                        title=row.title,
                        phase=row.phase,
                        enrollment=row.enrollment,
                        sites_in_country=row.sites_in_country,
                    )
                    for row in rows[:MAX_LISTED]
                ],
            )
        )
    return out
