"""Small, dependency-free forecasting helpers."""

from collections.abc import Sequence


def moving_average(values: Sequence[float], window: int) -> float:
    """Mean of the last ``window`` values (or of all values if fewer are available)."""
    if window < 1:
        raise ValueError("window must be >= 1")
    if not values:
        raise ValueError("values must not be empty")
    tail = list(values[-window:])
    return sum(tail) / len(tail)


def linear_trend(values: Sequence[float], horizon: int) -> list[float]:
    """Least-squares line through ``values`` extrapolated ``horizon`` steps ahead (clamped at 0)."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    n = len(values)
    if n == 0:
        raise ValueError("values must not be empty")
    if n == 1:
        return [max(0.0, float(values[0]))] * horizon
    xs = range(n)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    return [max(0.0, intercept + slope * (n + step)) for step in range(horizon)]


def forecast_consumption(history: Sequence[float], weeks: int, method: str = "moving_average") -> list[float]:
    """Forecast ``weeks`` weekly quantities from ``history`` using the named method."""
    if method == "moving_average":
        return [round(moving_average(history, window=4), 2)] * weeks
    if method == "linear_trend":
        return [round(v, 2) for v in linear_trend(history, weeks)]
    raise ValueError(f"unknown forecast method: {method!r}")
