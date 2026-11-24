"""Phase 1 baselines wrapped in the Phase 2 model interface (syllabus Module 2).

The forecasts come unchanged from `tsaf.baselines`; this module only adds the one-step
in-sample fitted values needed for residual diagnostics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tsaf import baselines
from tsaf.models.base import Fit


def _season(ctx: dict) -> int:
    s = ctx.get("season")
    return int(s) if s and s > 1 else 1


def _insample(name: str, y: np.ndarray, m: int) -> np.ndarray:
    """One-step fitted values of each baseline (NaN where undefined)."""
    n = len(y)
    out = np.full(n, np.nan)
    if name == "naive" and n > 1:
        out[1:] = y[:-1]
    elif name == "seasonal_naive" and n > m:
        out[m:] = y[:-m]
    elif name == "mean":
        out[:] = y.mean()
    elif name == "drift" and n > 1:
        slope = (y[-1] - y[0]) / (n - 1)
        out[1:] = y[:-1] + slope
    elif name == "seasonal_ma3":
        s = pd.Series(y)
        if m > 1:
            out = s.groupby(np.arange(n) % m).transform(
                lambda g: g.shift(1).rolling(baselines.MA_WINDOW).mean()).to_numpy()
        else:
            out = s.shift(1).rolling(baselines.MA_WINDOW).mean().to_numpy()
    return out


def make_baseline(name: str):
    """Return a `fit(train, h, ctx)` function for the Phase 1 baseline `name`."""
    f = baselines.BASELINES[name]

    def fit(train: pd.Series, h: int, ctx: dict) -> Fit:
        y = np.asarray(train, dtype=float)
        return Fit(forecast=f(train, h, ctx.get("season")), insample=_insample(name, y, _season(ctx)))

    fit.__name__ = f"fit_{name}"
    return fit
