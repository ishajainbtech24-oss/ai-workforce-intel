"""Company inputs for the cost-and-value engine: one validated dict, no hidden defaults.

`load_inputs(path)` reads a JSON file whose fields are either plain values or
{"value": ..., "illustrative": true, "unit": ..., "note": ...}; `validate(inputs)` checks every
required field and raises InputError listing ONE clear message per problem. Nothing is defaulted:
a missing field is an error.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


class InputError(ValueError):
    """Raised when company inputs are missing or out of range (message lists every problem)."""


# field -> (kind, minimum, maximum); kind: int, float, share, choice, bool
FIELDS: dict[str, tuple] = {
    "employees": ("int", 0, None), "adoption_start": ("share", 0, 1), "adoption_target": ("share", 0, 1),
    "ramp_months": ("int", 1, 120), "ramp_shape": ("choice", ("linear", "logistic"), None),
    "tokens_per_active_user_per_month": ("float", 0, None), "price_multiplier_vs_frontier": ("float", 0, None),
    "fixed_token_price_per_mtok": ("float", 0, None), "base_monthly_hosting_cost": ("float", 0, None),
    "base_hourly_wage_staff": ("float", 0, None), "base_hourly_wage_engineer": ("float", 0, None),
    "training_hours_per_new_user": ("float", 0, None), "refresher_hours_per_user_per_year": ("float", 0, None),
    "fixed_enablement_cost_per_month": ("float", 0, None), "engineering_hours_build": ("float", 0, None),
    "build_months": ("int", 1, 120), "maintenance_share_per_month": ("share", 0, 1),
    "maintenance_during_build": ("bool", None, None), "work_hours_per_user_per_month": ("float", 0, 744),
    "realisation_rate": ("share", 0, 1), "benefit_lag_months": ("int", 0, 120),
    "ai_assisted_share_of_hours": ("share", 0, 1), "horizon_months": ("int", 6, 24),
}


def _check(name: str, v, spec: tuple) -> str | None:
    kind, lo, hi = spec
    if kind == "bool":
        return None if isinstance(v, bool) else f"{name} must be true or false (got {v!r})"
    if kind == "choice":
        return None if v in lo else f"{name} must be one of {list(lo)} (got {v!r})"
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return f"{name} must be a number (got {v!r})"
    if kind == "int" and float(v) != int(v):
        return f"{name} must be a whole number (got {v!r})"
    if lo is not None and v < lo:
        return f"{name} must be at least {lo} (got {v})" if kind != "share" else f"{name} must be between 0 and 1 (got {v})"
    if hi is not None and v > hi:
        return f"{name} must be at most {hi} (got {v})" if kind != "share" else f"{name} must be between 0 and 1 (got {v})"
    return None


def validate(inputs: dict) -> dict:
    """Return the plain-value inputs dict, or raise InputError with one line per problem."""
    flat = {k: (v["value"] if isinstance(v, dict) and "value" in v else v) for k, v in inputs.items()
            if not k.startswith("_")}
    problems = [f"missing required field '{k}'" for k in FIELDS if k not in flat]
    problems += [p for k, spec in FIELDS.items() if k in flat for p in [_check(k, flat[k], spec)] if p]
    if not problems and flat["adoption_target"] < flat["adoption_start"]:
        problems.append("adoption_target must be at least adoption_start (adoption only ramps up)")
    if problems:
        raise InputError("invalid company inputs:\n  - " + "\n  - ".join(problems))
    return {k: flat[k] for k in FIELDS}


def load_inputs(path: Path, overrides: dict | None = None) -> tuple[dict, dict]:
    """(validated plain values, raw file with notes) from a JSON inputs file plus overrides."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    merged = {**raw, **(overrides or {})}
    return validate(merged), raw


def is_illustrative(raw: dict) -> bool:
    """True if any field of the raw inputs file is flagged illustrative."""
    return any(isinstance(v, dict) and v.get("illustrative") for v in raw.values())


def reference_tokens_per_user(data_dir: Path, period: str = "month") -> float | None:
    """WildChat tokens per active user, converted to `period` ('month' = weeks x 52/12).

    Uses the mean of the last 12 complete weeks of wildchat_weekly.tokens_per_active_user.
    WildChat is consumer chat and its processed token counts are output (assistant) tokens only.
    """
    try:
        w = pd.read_parquet(Path(data_dir) / "wildchat_weekly.parquet")
    except Exception as exc:  # noqa: BLE001
        log.warning("reference tokens per user not available: %s", exc)
        return None
    if "tokens_per_active_user" not in w.columns:
        log.warning("wildchat_weekly has no tokens_per_active_user column")
        return None
    ok = w[~w.get("partial_week", False).astype(bool)].sort_values("week").tail(12)
    weekly = float(ok["tokens_per_active_user"].mean())
    factor = 52 / 12 if period == "month" else 1.0
    log.info("reference tokens per active user: %.0f per week (last %d complete WildChat weeks, output tokens "
             "only) x %.3f = %.0f per %s", weekly, len(ok), factor, weekly * factor, period)
    return weekly * factor
