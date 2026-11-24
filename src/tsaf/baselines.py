"""The five Phase 1 benchmark forecasts (syllabus Module 2: simple forecasting methods).

Every function has the signature f(train, h, season) -> np.ndarray of length h, so the
backtest harness can treat them, and every Phase 2 model, the same way. No tuning: the
seasonal moving average always uses the last 3 values.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

Forecaster = Callable[[pd.Series, int, "int | None"], np.ndarray]
MA_WINDOW = 3


def _y(train) -> np.ndarray:
    y = np.asarray(train, dtype=float)
    if len(y) == 0:
        raise ValueError("empty training series")
    return y


def naive(train: pd.Series, h: int, season: int | None = None) -> np.ndarray:
    """Repeat the last observed value."""
    return np.full(h, _y(train)[-1])


def seasonal_naive(train: pd.Series, h: int, season: int | None = None) -> np.ndarray:
    """Repeat the last full season; falls back to naive when there is no usable season."""
    y = _y(train)
    if not season or season <= 1 or len(y) < season:
        return naive(train, h)
    last = y[-season:]
    return np.array([last[k % season] for k in range(h)])


def mean_forecast(train: pd.Series, h: int, season: int | None = None) -> np.ndarray:
    """Training mean for every step."""
    return np.full(h, _y(train).mean())


def drift(train: pd.Series, h: int, season: int | None = None) -> np.ndarray:
    """Extend the straight line through the first and last training values."""
    y = _y(train)
    slope = (y[-1] - y[0]) / (len(y) - 1) if len(y) > 1 else 0.0
    return y[-1] + slope * np.arange(1, h + 1)


def seasonal_ma(train: pd.Series, h: int, season: int | None = None) -> np.ndarray:
    """Mean of the last 3 values at the same seasonal position (plain MA(3) without season)."""
    y = _y(train)
    n = len(y)
    if not season or season <= 1:
        return np.full(h, y[-MA_WINDOW:].mean())
    pos = np.arange(n) % season
    out = np.empty(h)
    for k in range(h):
        same = y[pos == (n + k) % season][-MA_WINDOW:]
        out[k] = same.mean() if len(same) else y[-1]
    return out


BASELINES: dict[str, Forecaster] = {
    "naive": naive,
    "seasonal_naive": seasonal_naive,
    "mean": mean_forecast,
    "drift": drift,
    "seasonal_ma3": seasonal_ma,
}
