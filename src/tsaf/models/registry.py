"""Model registry: every Phase 2 model by name and family, with the rule for where it runs.

`ModelSpec.skip_reason(ctx)` returns None when the model runs for this driver, otherwise the
logged reason. `select` (optional) chooses hyper-parameters once, on the first training
window; they then stay fixed across folds and the hold-out.

ctx keys used here: name, grain, season, decomposition, positive (training data > 0),
extra (extra series or None), fast, with_lstm.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable

import numpy as np
import pandas as pd

import config_phase2 as P2
from optional import has_prophet, has_torch, has_xgboost
from tsaf.models import arima, ml, optional_models, smoothing
from tsaf.models.base import Fit, FitFn
from tsaf.models.baseline_models import make_baseline

Rule = Callable[[dict], "str | None"]
Selector = Callable[[pd.Series, dict], dict]


@dataclass(frozen=True)
class ModelSpec:
    """One registered model."""
    name: str
    family: str
    fit: FitFn
    select: Selector | None = None
    rule: Rule | None = None

    def skip_reason(self, ctx: dict) -> str | None:
        return self.rule(ctx) if self.rule else None

    def fit_predict(self, train: pd.Series, h: int, ctx: dict) -> np.ndarray:
        return np.asarray(self.fit(train, h, ctx).forecast, dtype=float)


def _seasonal(ctx):
    return None if (ctx["season"] or 1) > 1 else "no seasonal period (season <= 1)"


def _hw_mul(ctx):
    if _seasonal(ctx):
        return _seasonal(ctx)
    if ctx["decomposition"] != "multiplicative":
        return "handoff decomposition is additive"
    return None if ctx["positive"] else "training series is not strictly positive"


def _sarima(ctx):
    if _seasonal(ctx):
        return _seasonal(ctx)
    return "hourly: seasonal order not used (Fourier terms in SARIMAX instead)" if ctx["grain"] == "hourly" else None


def _sarimax(ctx):
    if arima.exog_kind(ctx) is None:
        return f"no exogenous variable defined for {ctx['grain']} series"
    if ctx["grain"] == "hourly" and ctx["fast"]:
        return "hourly SARIMAX skipped in --fast mode"
    return None


def _ml(ctx):
    return None if ctx["grain"] in P2.ML_GRAINS else "too few observations for ML"


def _ml_extra(ctx):
    if _ml(ctx):
        return _ml(ctx)
    return None if ctx.get("extra") else "no extra series configured for this driver"


def _prophet(ctx):
    if ctx["name"] not in P2.PROPHET_DRIVERS:
        return "Prophet runs only for " + ", ".join(P2.PROPHET_DRIVERS)
    if ctx["fast"]:
        return "skipped in --fast mode"
    return None if has_prophet() else "skipped (not installed)"


def _lstm(ctx):
    if ctx["name"] not in P2.LSTM_DRIVERS:
        return "LSTM runs only for " + ", ".join(P2.LSTM_DRIVERS)
    if ctx["fast"]:
        return "skipped in --fast mode"
    if not ctx.get("with_lstm"):
        return "off by default (enable with --with-lstm)"
    return None if has_torch() else "skipped (not installed)"


def _tree_select(kind: str) -> Selector:
    return lambda train0, ctx: ml.tree_params(kind, ctx)


def _gb_name() -> str:
    return "xgboost" if has_xgboost() else "hist_gradient_boosting"


def build_registry() -> list[ModelSpec]:
    """All models in a fixed order (baselines first; the ensemble is added by the pipeline)."""
    specs = [ModelSpec(n, "baseline", make_baseline(n))
             for n in ("naive", "seasonal_naive", "mean", "drift", "seasonal_ma3")]
    specs.append(ModelSpec("moving_average", "smoothing", smoothing.fit_moving_average,
                           smoothing.select_ma_window))
    for kind, rule in [("ses", None), ("holt", None), ("damped_holt", None),
                       ("hw_additive", _seasonal), ("hw_multiplicative", _hw_mul)]:
        specs.append(ModelSpec(kind, "smoothing", smoothing.make_smoother(kind), rule=rule))
    for kind, rule in [("arima", None), ("sarima", _sarima), ("sarimax", _sarimax)]:
        specs.append(ModelSpec(kind, "arima", arima.fit_arima_family, arima.make_selector(kind), rule))
    gb = _gb_name()
    for extra in (False, True):
        sfx, rule = ("_with_requests", _ml_extra) if extra else ("", _ml)
        specs.append(ModelSpec("ridge" + sfx, "ml", ml.make_ml("ridge", extra),
                               partial(ml.select_ridge_alpha, with_extra=extra), rule))
        specs.append(ModelSpec("random_forest" + sfx, "ml", ml.make_ml("random_forest", extra),
                               _tree_select("random_forest"), rule))
        specs.append(ModelSpec(gb + sfx, "ml", ml.make_ml(gb, extra), _tree_select(gb), rule))
    specs.append(ModelSpec("prophet", "deep", optional_models.fit_prophet, rule=_prophet))
    specs.append(ModelSpec("lstm", "deep", optional_models.fit_lstm, rule=_lstm))
    return specs


def by_name(specs: list[ModelSpec]) -> dict[str, ModelSpec]:
    return {s.name: s for s in specs}


def by_family(specs: list[ModelSpec]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for s in specs:
        out.setdefault(s.family, []).append(s.name)
    return out


__all__ = ["ModelSpec", "Fit", "build_registry", "by_name", "by_family"]
