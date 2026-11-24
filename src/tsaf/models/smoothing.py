"""Smoothing models (syllabus Module 2): moving average, SES, Holt, damped Holt, Holt-Winters.

statsmodels.tsa.holtwinters with optimized=True. If a fit raises or returns non-finite
values, the next simpler model in FALLBACK is used for that fold and the fallback is
recorded in `Fit.info["fallback"]`. The moving-average window is chosen once, on the first
training window, from config_phase2.MA_WINDOWS by the MAE on its last 20%.
"""
from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing

import config_phase2 as P2
from tsaf import baselines
from tsaf.models.base import Fit

log = logging.getLogger(__name__)
FALLBACK = {"hw_multiplicative": "hw_additive", "hw_additive": "damped_holt",
            "damped_holt": "holt", "holt": "ses", "ses": "naive"}


def _season(ctx: dict) -> int:
    """Holt-Winters period: the handoff season (hourly uses 24 only; 168 is too slow)."""
    return int(ctx["season"])


def _build(kind: str, y: np.ndarray, m: int):
    est = {"initialization_method": "estimated"}
    if kind == "ses":
        return SimpleExpSmoothing(y, **est)
    if kind == "holt":
        return Holt(y, **est)
    if kind == "damped_holt":
        return Holt(y, damped_trend=True, **est)
    if kind == "hw_additive":
        return ExponentialSmoothing(y, trend="add", seasonal="add", seasonal_periods=m, **est)
    if kind == "hw_multiplicative":
        if np.any(y <= 0):
            raise ValueError("multiplicative Holt-Winters needs a strictly positive series")
        return ExponentialSmoothing(y, trend="add", seasonal="mul", seasonal_periods=m, **est)
    raise KeyError(kind)


def _params(res) -> dict:
    p = res.params
    keys = {"smoothing_level": "alpha", "smoothing_trend": "beta",
            "smoothing_seasonal": "gamma", "damping_trend": "phi"}
    return {short: float(p[k]) for k, short in keys.items()
            if k in p and p[k] is not None and np.isfinite(p[k])}


def _fit_one(kind: str, y: np.ndarray, h: int, m: int) -> Fit:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = _build(kind, y, m).fit(optimized=True)
        fc = np.asarray(res.forecast(h), dtype=float)
        fitted = np.asarray(res.fittedvalues, dtype=float)
    if not np.all(np.isfinite(fc)) or not np.all(np.isfinite(fitted)):
        raise ValueError(f"{kind} returned non-finite values")
    return Fit(forecast=fc, insample=fitted, info=_params(res))


def make_smoother(kind: str):
    """`fit(train, h, ctx)` for one smoothing model, with the fallback chain."""

    def fit(train: pd.Series, h: int, ctx: dict) -> Fit:
        y = np.asarray(train, dtype=float)
        current = kind
        while current != "naive":
            try:
                out = _fit_one(current, y, h, _season(ctx))
                if current != kind:
                    out.info["fallback"] = current
                return out
            except Exception as exc:  # noqa: BLE001 - fall back to the simpler model
                log.debug("%s %s failed (%s); falling back to %s", ctx.get("name"), current, exc,
                          FALLBACK[current])
                current = FALLBACK[current]
        ins = np.r_[np.nan, y[:-1]]
        return Fit(forecast=baselines.naive(train, h), insample=ins, info={"fallback": "naive"})

    fit.__name__ = f"fit_{kind}"
    return fit


def _windows(ctx: dict) -> tuple[int, ...]:
    return P2.MA_WINDOWS["daily" if ctx["grain"] == "daily" else "other"]


def select_ma_window(train0: pd.Series, ctx: dict) -> dict:
    """Pick the moving-average window by MAE on the last 20% of the first training window."""
    y = np.asarray(train0, dtype=float)
    v = max(1, int(round(P2.VALIDATION_SHARE * len(y))))
    fit_part, val = y[:-v], y[-v:]
    scores = {w: float(np.mean(np.abs(val - fit_part[-w:].mean())))
              for w in _windows(ctx) if w <= len(fit_part)}
    if not scores:
        return {"window": min(_windows(ctx)), "selection": "default (window too short)"}
    best = min(scores, key=lambda w: (scores[w], w))
    return {"window": best, "validation_mae": scores[best], "candidates": str(sorted(scores))}


def fit_moving_average(train: pd.Series, h: int, ctx: dict) -> Fit:
    """Flat forecast at the mean of the last `window` values; fitted = trailing mean."""
    w = int(ctx["params"]["window"])
    y = pd.Series(np.asarray(train, dtype=float))
    ins = y.shift(1).rolling(w).mean().to_numpy()
    return Fit(forecast=np.full(h, y.iloc[-w:].mean()), insample=ins, info={"window": w})
