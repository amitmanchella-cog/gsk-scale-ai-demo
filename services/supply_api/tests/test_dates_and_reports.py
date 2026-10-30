from datetime import date, timezone

import pytest
from app import data
from app.dates import date_range_weeks, parse_iso_datetime, to_site_local_date, week_start


def test_offset_datetime_resolves_to_next_day_in_tokyo():
    dt = parse_iso_datetime("2026-03-01T23:30:00-05:00")
    assert to_site_local_date(dt, "Asia/Tokyo") == date(2026, 3, 2)
    assert to_site_local_date(dt, "America/New_York") == date(2026, 3, 1)


def test_z_suffix_equals_plus_zero_offset():
    assert parse_iso_datetime("2026-03-01T12:00:00Z") == parse_iso_datetime("2026-03-01T12:00:00+00:00")
    assert parse_iso_datetime("2026-03-01T12:00:00Z").utcoffset() == timezone.utc.utcoffset(None)


def test_parse_rejects_naive_and_garbage():
    with pytest.raises(ValueError):
        parse_iso_datetime("2026-03-01T12:00:00")
    with pytest.raises(ValueError):
        parse_iso_datetime("not-a-date")


def test_week_start_is_monday():
    assert week_start(date(2026, 3, 1)) == date(2026, 2, 23)  # Sunday -> previous Monday
    assert week_start(date(2026, 3, 2)) == date(2026, 3, 2)  # Monday stays
    assert week_start(date(2026, 3, 8)) == date(2026, 3, 2)


def test_date_range_weeks_is_inclusive_by_week():
    assert date_range_weeks(date(2026, 3, 2), date(2026, 3, 15)) == [date(2026, 3, 2), date(2026, 3, 9)]
    assert date_range_weeks(date(2026, 3, 4), date(2026, 3, 4)) == [date(2026, 3, 2)]
    with pytest.raises(ValueError):
        date_range_weeks(date(2026, 3, 9), date(2026, 3, 2))


def test_report_uses_site_local_dates(client):
    # 23:30 in New York on 1 March is already 2 March in Tokyo, so the Tokyo report starts one week later.
    params = {"start": "2026-03-01T23:30:00-05:00", "end": "2026-03-15T00:00:00Z"}
    r = client.get("/reports/consumption", params=params)
    assert r.status_code == 200
    body = r.json()
    assert body["start"] == params["start"] and body["end"] == params["end"]
    assert len(body["lines"]) == len(data.SITES) * len(data.PRODUCTS)

    tokyo = [line for line in body["lines"] if line["site_id"] == "S007"]
    boston = [line for line in body["lines"] if line["site_id"] == "S001"]
    assert tokyo[0]["start_local_date"] == "2026-03-02"
    assert boston[0]["start_local_date"] == "2026-03-01"
    assert tokyo[0]["weeks_included"] == 2  # weeks of 2 Mar and 9 Mar
    assert boston[0]["weeks_included"] == 3  # weeks of 23 Feb, 2 Mar and 9 Mar


def test_report_totals_match_history(client):
    params = {"start": "2026-03-02T00:00:00Z", "end": "2026-03-09T00:00:00Z", "site_id": "S004"}
    body = client.get("/reports/consumption", params=params).json()
    assert {line["site_id"] for line in body["lines"]} == {"S004"}
    for line in body["lines"]:
        selected = {date(2026, 3, 2), date(2026, 3, 9)}
        points = [p for p in data.CONSUMPTION[("S004", line["product_id"])] if p.week_start in selected]
        assert line["total_quantity"] == sum(p.quantity for p in points)
        assert line["weeks_included"] == 2


def test_report_rejects_bad_dates(client):
    base = {"start": "2026-03-02T00:00:00Z", "end": "2026-03-01T00:00:00Z"}
    assert client.get("/reports/consumption", params=base).status_code == 422  # start > end
    assert client.get("/reports/consumption", params={"start": "nope", "end": base["end"]}).status_code == 422
    naive = {"start": "2026-03-01T00:00:00", "end": base["end"]}
    assert client.get("/reports/consumption", params=naive).status_code == 422
    unknown_site = {**base, "end": "2026-03-20T00:00:00Z", "site_id": "NOPE"}
    assert client.get("/reports/consumption", params=unknown_site).status_code == 404


def test_report_parses_z_like_utc_offset(client):
    zulu = {"start": "2026-03-02T00:00:00Z", "end": "2026-03-09T00:00:00Z"}
    offset = {"start": "2026-03-02T00:00:00+00:00", "end": "2026-03-09T00:00:00+00:00"}
    a = client.get("/reports/consumption", params=zulu)
    b = client.get("/reports/consumption", params=offset)
    assert a.json()["lines"] == b.json()["lines"]
