import pytest
from app import data
from app.forecast import forecast_consumption, linear_trend, moving_average


def test_moving_average_exact_values():
    assert moving_average([10, 20, 30, 40], 2) == 35.0
    assert moving_average([10, 20, 30, 40], 4) == 25.0
    assert moving_average([10, 20], 5) == 15.0  # window larger than series falls back to all values


def test_moving_average_rejects_bad_input():
    with pytest.raises(ValueError):
        moving_average([], 2)
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


def test_linear_trend_extrapolates_a_straight_line():
    assert linear_trend([10, 20, 30, 40], 3) == [50.0, 60.0, 70.0]
    assert linear_trend([40, 30, 20, 10, 0], 2) == [0.0, 0.0]  # clamped at zero


def test_forecast_consumption_dispatch():
    assert forecast_consumption([10, 20, 30, 40], 2, "moving_average") == [25.0, 25.0]
    assert forecast_consumption([10, 20, 30, 40], 2, "linear_trend") == [50.0, 60.0]
    with pytest.raises(ValueError):
        forecast_consumption([1, 2, 3], 1, "crystal_ball")


def test_forecast_endpoint_default_horizon_is_four_weeks(client):
    r = client.get("/forecast/S001/IP-100")
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "moving_average"
    assert len(body["weeks"]) == 4
    first = body["weeks"][0]["week_start"]
    assert first == "2026-03-30"  # the Monday after the last week of history


def test_forecast_endpoint_matches_pure_function(client):
    history = [p.quantity for p in data.CONSUMPTION[("S004", "IP-200")]]
    body = client.get("/forecast/S004/IP-200", params={"weeks": 3, "method": "linear_trend"}).json()
    assert [w["quantity"] for w in body["weeks"]] == forecast_consumption(history, 3, "linear_trend")


def test_forecast_endpoint_validation(client):
    assert client.get("/forecast/S001/IP-100", params={"method": "oracle"}).status_code == 422
    assert client.get("/forecast/S001/IP-100", params={"weeks": 0}).status_code == 422
    assert client.get("/forecast/NOPE/IP-100").status_code == 404
