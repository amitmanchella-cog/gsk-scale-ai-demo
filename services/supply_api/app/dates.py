"""Timezone-aware date helpers built on the standard library's zoneinfo."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime with an offset ("+09:00") or "Z"; reject naive values."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid ISO 8601 datetime: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"datetime must include a timezone offset or 'Z': {value!r}")
    return parsed


def to_site_local_date(dt: datetime, tz_name: str) -> date:
    """Return the calendar date for ``dt``, normalised to UTC so every site reports on the same day boundary."""
    ZoneInfo(tz_name)  # validate the site timezone name
    return dt.astimezone(timezone.utc).date()


def week_start(day: date) -> date:
    """Return the Monday that starts the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def date_range_weeks(start: date, end: date) -> list[date]:
    """Return every Monday from the week containing ``start`` through the week containing ``end``."""
    if start > end:
        raise ValueError("start must be on or before end")
    first, last = week_start(start), week_start(end)
    return [first + timedelta(weeks=i) for i in range((last - first).days // 7 + 1)]
