"""outputs/phase2/chosen_models.json: the Phase 3 hand-off (one entry per modelled driver).

Phase 3 refits exactly the chosen model on the full clean window and resamples the saved
out-of-sample errors, so `params` holds everything needed to refit it. `validate` is a small
schema check that raises ValueError on a missing key or a wrong type.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import config_phase2 as P2
from tsaf.models import ml

KEYS = {"name": str, "file": str, "value_col": str, "grain": str, "season": (int, type(None)),
        "chosen_model": str, "family": str, "params": dict, "beats_seasonal_naive": bool,
        "cv_mase": (int, float), "holdout_mase": (int, float),
        "interval_coverage_80": (int, float, type(None)), "horizon_for_forecast": int, "notes": str}


def clean(v):
    """JSON-safe values: numpy scalars to Python, NaN to None, tuples to lists."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    return v


def model_params(name: str, dr: dict) -> dict:
    """Everything needed to refit model `name` for driver result `dr`."""
    ctx, r = dr["ctx"], dr["results"][name]
    if name == "ensemble":
        return {"components": [{"model": c, "family": dr["results"][c].family,
                                "params": model_params(c, dr)} for c in r.params["components"]],
                "weights": r.params["weights"]}
    out = {"selected": r.params, "season": ctx["season"], "d": ctx["d"], "D": ctx["D"],
           "decomposition": ctx["decomposition"], "forecasts_clipped_at_zero": ctx["nonneg"]}
    if r.family == "ml":
        spec = ml.feature_spec(ctx, with_extra=name.endswith("_with_requests"))
        out["features"] = {"lags": list(spec.lags), "rolling_window": spec.roll,
                           "is_weekend": spec.weekend, "cycle_sin_cos": True, "trend_index": True,
                           "extra_series": ctx["extra"]["col"] if spec.extra_lag else None,
                           "extra_lag": spec.extra_lag, "multi_step": "recursive"}
    if r.holdout_info:
        out["fit_on_pre_holdout"] = {k: v for k, v in r.holdout_info.items() if k != "features"}
    return out


def make_entry(dr: dict, chosen_row: dict) -> dict:
    """One chosen_models.json entry (keys exactly as KEYS)."""
    e, name = dr["entry"], dr["chosen"]
    board = dr["board"].set_index("model")
    return clean({"name": e["name"], "file": e["file"], "value_col": e["value_col"], "grain": e["grain"],
                  "season": e["season"], "chosen_model": name, "family": dr["results"][name].family,
                  "params": model_params(name, dr),
                  "beats_seasonal_naive": bool(chosen_row["beats_seasonal_naive"]),
                  "cv_mase": float(board.loc[name, "cv_mase"]),
                  "holdout_mase": float(board.loc[name, "holdout_mase"]),
                  "interval_coverage_80": float(board.loc[name].get("coverage_80", np.nan)),
                  "horizon_for_forecast": int(P2.HORIZON_FOR_FORECAST[e["grain"]]),
                  "notes": chosen_row["why"]})


def validate(doc: dict) -> None:
    """Raise ValueError if the document or any entry misses a key or has a wrong type."""
    if not isinstance(doc.get("drivers"), list) or not doc["drivers"]:
        raise ValueError("chosen_models.json: 'drivers' must be a non-empty list")
    for i, d in enumerate(doc["drivers"]):
        for k, t in KEYS.items():
            if k not in d:
                raise ValueError(f"chosen_models.json driver {i}: missing key '{k}'")
            if not isinstance(d[k], t) or (isinstance(d[k], bool) and t is not bool):
                raise ValueError(f"chosen_models.json driver {i}: key '{k}' has type {type(d[k]).__name__}")


def write(entries: list[dict], skipped: list[dict], path: Path) -> dict:
    """Validate and write the hand-off file; returns the document."""
    doc = {"phase": 2, "drivers": entries, "skipped": skipped,
           "how_to_use": ("Refit `chosen_model` with `params` on the full clean window, forecast "
                          "`horizon_for_forecast` steps, and resample the out-of-sample errors in "
                          "tables/cv_residuals.parquet (same driver and model).")}
    validate(doc)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc
