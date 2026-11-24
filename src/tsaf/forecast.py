"""Phase 3 point forecasts: refit each driver's chosen model and forecast its horizon.

The model and its fixed hyper-parameters come from outputs/phase2/chosen_models.json (no
re-selection, no re-tuning). Models are rebuilt through the Phase 2 registry and refitted on
the full modelling window. An ensemble refits both members and averages their (clipped)
forecasts, exactly as Phase 2 scored it. A failed refit, a non-finite forecast, or one above
SANITY_MAX_RATIO x the largest training value falls back to seasonal naive (logged).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import config_phase3 as P3
from tsaf import baselines
from tsaf.models import base
from tsaf.models.registry import ModelSpec
from tsaf.pipeline_phase2 import make_ctx

log = logging.getLogger(__name__)


@dataclass
class PointResult:
    """Point forecast of one driver after any fallback, with what was used and why."""
    forecast: np.ndarray
    model_used: str
    family: str
    fallback: bool = False
    n_clipped: int = 0
    notes: list[str] = field(default_factory=list)


def driver_ctx(entry: dict, train: pd.Series, data_dir: Path) -> dict:
    """Phase 2 model context for this driver, built on `train` (the data the model may see)."""
    args = SimpleNamespace(fast=False, with_lstm=False)
    return make_ctx(entry, train, train, args, data_dir)


def ensemble_members(chosen: dict, leaderboard: pd.DataFrame | None) -> list[dict]:
    """The ensemble's two members: from params, else the two best non-ensemble models by CV MASE."""
    comps = chosen.get("params", {}).get("components")
    if comps:
        return comps
    if leaderboard is None:
        raise ValueError("ensemble members not in params and no leaderboard to read them from")
    lb = leaderboard[(leaderboard["driver"] == chosen["name"]) & (leaderboard["status"] == "ok")
                     & (leaderboard["model"] != "ensemble")].sort_values("cv_mase", kind="stable")
    return [{"model": m, "params": {}} for m in lb["model"].head(2)]


def _member(name: str, params: dict, train: pd.Series, h: int, ctx: dict,
            specs: dict[str, ModelSpec]) -> np.ndarray:
    fit = specs[name].fit(train, h, {**ctx, "params": params.get("selected", {})})
    fc = base.check_forecast(fit.forecast, h)
    return np.maximum(fc, 0.0) if ctx.get("nonneg", True) else fc


def model_forecast(chosen: dict, train: pd.Series, h: int, ctx: dict, specs: dict[str, ModelSpec],
                   leaderboard: pd.DataFrame | None = None) -> np.ndarray:
    """Forecast of the chosen model (ensemble = mean of the two refitted members)."""
    if chosen["chosen_model"] == "ensemble":
        parts = [_member(c["model"], c.get("params", {}), train, h, ctx, specs)
                 for c in ensemble_members(chosen, leaderboard)]
        return np.mean(parts, axis=0)
    return _member(chosen["chosen_model"], chosen.get("params", {}), train, h, ctx, specs)


def sanity(fc: np.ndarray, train: pd.Series) -> str | None:
    """None if the forecast is usable, otherwise the reason it is rejected."""
    if not np.all(np.isfinite(fc)):
        return "forecast is not finite"
    top = float(np.nanmax(np.abs(train)))
    if top > 0 and float(np.max(fc)) > P3.SANITY_MAX_RATIO * top:
        return f"forecast max {np.max(fc):,.0f} exceeds {P3.SANITY_MAX_RATIO:g} x the largest training value"
    return None


def future_inputs_note(train: pd.Series, h: int, grain: str) -> str:
    """Check the known-in-advance future inputs line up (h rows, calendar continues)."""
    idx = base.future_index(train.index, h, grain)
    if len(idx) != h:
        raise ValueError(f"future index has {len(idx)} rows, expected {h}")
    if isinstance(idx, pd.DatetimeIndex):
        return f"future dates {idx[0].date()} to {idx[-1].date()} ({h} rows)"
    if grain == "hourly":
        four = base.fourier(idx, {24: 3, 168: 3})
        assert four.shape[0] == h
        return (f"future hours {idx[0]}-{idx[-1]} ({h} rows); hour of day continues at "
                f"{int(idx[0]) % 24}, Fourier terms continue the hour index")
    dow = base.day_of_week(idx, grain)
    return (f"future days {idx[0]}-{idx[-1]} ({h} rows); day_of_cycle continues {int(dow[0])}..; "
            "inferred weekend = day_of_cycle 4-5")


def point_forecast(chosen: dict, train: pd.Series, h: int, ctx: dict, specs: dict[str, ModelSpec],
                   leaderboard: pd.DataFrame | None = None) -> PointResult:
    """Refit and forecast; fall back to seasonal naive on failure or an implausible forecast."""
    name, notes = chosen["chosen_model"], []
    try:
        notes.append(future_inputs_note(train, h, chosen["grain"]))
        fc = model_forecast(chosen, train, h, ctx, specs, leaderboard)
        why = sanity(fc, train)
        if why:
            raise ValueError(why)
        res = PointResult(fc, name, chosen.get("family", ""), notes=notes)
    except Exception as exc:  # noqa: BLE001 - the driver continues with the benchmark
        msg = f"{name} could not be used ({type(exc).__name__}: {str(exc)[:160]}); seasonal naive used instead"
        log.warning("%s: %s", chosen["name"], msg)
        fc = baselines.seasonal_naive(train, h, ctx.get("season"))
        res = PointResult(np.asarray(fc, dtype=float), "seasonal_naive", "baseline", True, notes=notes + [msg])
    res.n_clipped = int((res.forecast < 0).sum())
    res.forecast = np.maximum(res.forecast, 0.0)
    return res
