"""Forecast accuracy measures (syllabus Module 2: evaluating forecast accuracy).

MAE and RMSE are scale-dependent; sMAPE and MAPE are percentage errors (MAPE is undefined
when an actual is 0, so it returns NaN unless every actual is above 0); MASE scales the MAE
by the in-sample MAE of the seasonal naive forecast, so MASE < 1 means "better than seasonal
naive on the training data" and series of different sizes can be compared.
"""
from __future__ import annotations

import numpy as np


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def mae(actual, forecast) -> float:
    """Mean absolute error."""
    return float(np.mean(np.abs(_arr(actual) - _arr(forecast))))


def rmse(actual, forecast) -> float:
    """Root mean squared error."""
    return float(np.sqrt(np.mean((_arr(actual) - _arr(forecast)) ** 2)))


def smape(actual, forecast) -> float:
    """Symmetric MAPE in percent: mean of 200*|f-y|/(|y|+|f|); a 0/0 term counts as 0."""
    y, f = _arr(actual), _arr(forecast)
    den = np.abs(y) + np.abs(f)
    terms = np.divide(200.0 * np.abs(f - y), den, out=np.zeros_like(den), where=den > 0)
    return float(np.mean(terms))


def mape(actual, forecast) -> float:
    """MAPE in percent; NaN unless every actual is strictly above 0."""
    y, f = _arr(actual), _arr(forecast)
    if np.any(y <= 0):
        return float("nan")
    return float(np.mean(100.0 * np.abs((y - f) / y)))


def mase_scale(train, season: int | None) -> float:
    """In-sample MAE of the seasonal naive forecast (naive when season is None or 1)."""
    y = _arr(train)
    m = season if season and season > 1 else 1
    if len(y) <= m:
        return float("nan")
    return float(np.mean(np.abs(y[m:] - y[:-m])))


def mase(actual, forecast, train, season: int | None) -> float:
    """Mean absolute scaled error; NaN when the scale is 0 or cannot be computed."""
    scale = mase_scale(train, season)
    if not np.isfinite(scale) or scale == 0:
        return float("nan")
    return mae(actual, forecast) / scale


def score_all(actual, forecast, train, season: int | None) -> dict[str, float]:
    """All five measures in one dict (keys: mae, rmse, smape, mape, mase)."""
    return {"mae": mae(actual, forecast), "rmse": rmse(actual, forecast),
            "smape": smape(actual, forecast), "mape": mape(actual, forecast),
            "mase": mase(actual, forecast, train, season)}
