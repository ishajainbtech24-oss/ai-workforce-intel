"""Shared pieces for every Phase 2 model: the result type, future index, calendar and Fourier terms.

Every model is a function `fit(train, h, ctx) -> Fit`. `Fit.forecast` has length h;
`Fit.insample` holds one-step in-sample fitted values aligned with `train` (NaN where a
model has no fitted value, e.g. before the first full lag window). `fit_predict` is the
plain interface `(train, h, ctx) -> np.ndarray` used by the backtest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

FREQ = {"daily": "D", "weekly": "W-MON", "monthly": "MS", "quarterly": "QS"}


@dataclass
class Fit:
    """Result of one model fit: forecast, in-sample fitted values, fitted parameters, table."""
    forecast: np.ndarray
    insample: np.ndarray | None = None
    info: dict = field(default_factory=dict)
    table: pd.DataFrame | None = None


FitFn = Callable[[pd.Series, int, dict], Fit]


def fit_predict(fn: FitFn, train: pd.Series, h: int, ctx: dict) -> np.ndarray:
    """The common interface: forecast array of length h."""
    return np.asarray(fn(train, h, ctx).forecast, dtype=float)


def future_index(index: pd.Index, h: int, grain: str) -> pd.Index:
    """The h labels after `index` (integers for BurstGPT, dates for dated series)."""
    if isinstance(index, pd.DatetimeIndex):
        freq = index.freq or pd.infer_freq(index) or FREQ[grain]
        return pd.date_range(index[-1], periods=h + 1, freq=freq)[1:]
    last = int(index[-1])
    return pd.RangeIndex(last + 1, last + 1 + h)


def day_of_week(index: pd.Index, grain: str) -> np.ndarray:
    """Day of the cycle: BurstGPT day_index % 7 (hour // 24 for hourly), or the calendar weekday."""
    if isinstance(index, pd.DatetimeIndex):
        return index.dayofweek.to_numpy()
    t = np.asarray(index, dtype=int)
    return (t // 24) % 7 if grain == "hourly" else t % 7


def is_weekend(index: pd.Index, grain: str) -> np.ndarray:
    """1.0 on weekend days. BurstGPT: day_of_cycle 4 and 5 (INFERRED from low volume);
    dated series: Saturday and Sunday (known calendar)."""
    dow = day_of_week(index, grain)
    days = (5, 6) if isinstance(index, pd.DatetimeIndex) else (4, 5)
    return np.isin(dow, days).astype(float)


def cycle_position(index: pd.Index, grain: str) -> tuple[np.ndarray, int]:
    """(position within the main cycle, cycle length): hour of day for hourly, weekday for daily."""
    if grain == "hourly" and not isinstance(index, pd.DatetimeIndex):
        return np.asarray(index, dtype=int) % 24, 24
    return day_of_week(index, grain), 7


def fourier(index: pd.Index, terms: dict[int, int]) -> pd.DataFrame:
    """Fourier terms sin/cos(2 pi k t / P), k = 1..K, for each period P (t = integer index)."""
    t = np.asarray(index, dtype=float)
    cols = {}
    for period, k_max in terms.items():
        for k in range(1, k_max + 1):
            cols[f"sin{period}_{k}"] = np.sin(2 * np.pi * k * t / period)
            cols[f"cos{period}_{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(cols, index=index)


def check_forecast(fc, h: int) -> np.ndarray:
    """Validate a forecast: length h, all finite (raises ValueError otherwise)."""
    fc = np.asarray(fc, dtype=float).reshape(-1)
    if len(fc) != h:
        raise ValueError(f"forecast has length {len(fc)}, expected {h}")
    if not np.all(np.isfinite(fc)):
        raise ValueError("forecast contains NaN or infinite values")
    return fc
