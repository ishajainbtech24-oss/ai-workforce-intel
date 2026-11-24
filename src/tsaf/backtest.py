"""Time-series cross-validation (syllabus Modules 2 and 4: rolling-origin evaluation).

Expanding window, no shuffling: fold k trains on observations [0, origin_k) and tests on
[origin_k, origin_k + h). A final hold-out at the end of the series is reserved and scored
once; folds only ever see data before the hold-out.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from tsaf.metrics import score_all


def resolve_settings(base: dict, n: int, override: dict | None = None,
                     max_folds: int | None = None) -> dict:
    """Turn a CV_SETTINGS entry into integers for a series of length n (share -> count)."""
    s = {**base, **(override or {})}
    init = s["initial"]
    s["initial"] = int(round(init * n)) if isinstance(init, float) and init < 1 else int(init)
    if max_folds is not None:
        s["max_folds"] = min(max_folds, s["max_folds"] or max_folds)
    return s


def holdout_split(series: pd.Series, holdout: int) -> tuple[pd.Series, pd.Series]:
    """Split into (train, test) where test is the last `holdout` points."""
    if holdout <= 0 or holdout >= len(series):
        raise ValueError(f"holdout={holdout} must be between 1 and len(series)-1={len(series)-1}")
    return series.iloc[:-holdout], series.iloc[-holdout:]


def fold_origins(n: int, initial: int, h: int, step: int, max_folds: int | None = None) -> list[int]:
    """Positions where each fold's test window starts (each test window fits fully in n)."""
    origins = list(range(initial, n - h + 1, step))
    return origins[:max_folds] if max_folds else origins


def rolling_origin(series: pd.Series, forecaster: Callable, h: int, initial: int, step: int,
                   max_folds: int | None, season: int | None) -> pd.DataFrame:
    """Run `forecaster` over expanding-window folds; tidy rows per fold and step ahead."""
    rows = []
    for fold, origin in enumerate(fold_origins(len(series), initial, h, step, max_folds)):
        train, test = series.iloc[:origin], series.iloc[origin:origin + h]
        fc = np.asarray(forecaster(train, h, season), dtype=float)
        for k in range(h):
            rows.append({"fold": fold, "step_ahead": k + 1, "origin_index": origin,
                         "time": test.index[k], "actual": float(test.iloc[k]),
                         "forecast": float(fc[k])})
    cols = ["fold", "step_ahead", "origin_index", "time", "actual", "forecast"]
    return pd.DataFrame(rows, columns=cols)


def score_folds(folds: pd.DataFrame, series: pd.Series, season: int | None) -> pd.DataFrame:
    """Accuracy per fold; MASE uses each fold's own training data for its scale."""
    out = []
    for fold, g in folds.groupby("fold"):
        train = series.iloc[: int(g["origin_index"].iloc[0])]
        out.append({"fold": fold, **score_all(g["actual"], g["forecast"], train, season)})
    return pd.DataFrame(out)


def score_holdout(series: pd.Series, forecaster: Callable, holdout: int,
                  season: int | None) -> tuple[dict, pd.Series, np.ndarray]:
    """Fit on everything before the hold-out, forecast it in one go, and score it."""
    train, test = holdout_split(series, holdout)
    fc = np.asarray(forecaster(train, holdout, season), dtype=float)
    return score_all(test, fc, train, season), test, fc
