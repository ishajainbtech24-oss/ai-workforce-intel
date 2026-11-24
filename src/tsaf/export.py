"""The standard Phase 3 forecast table (the hand-over contract for Phase 4).

Long format, one row per (period, sample), columns in this exact order:
driver, period_index, calendar_month, sample_id, value, unit, model, source, grain, kind.
sample_id -1 is the point forecast, 0..199 are the simulated paths. calendar_month is the
first day of the month of each step for dated sources (the month AFTER the data end, which
may lie in the past) and empty for BurstGPT, which has no calendar dates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase3 as P3
from tsaf.models.base import future_index


def standard_unit(cfg_unit: str) -> str:
    """Map a driver config unit ('tokens per day') to a standard unit ('tokens')."""
    u = (cfg_unit or "").lower()
    for key, std in sorted(P3.UNIT_MAP.items(), key=lambda kv: -len(kv[0])):
        if u.startswith(key):
            return std
    raise ValueError(f"no standard unit for config unit '{cfg_unit}'")


def calendar_months(train_index: pd.Index, h: int, grain: str) -> list[str]:
    """ISO first-of-month date per future step (dated sources) or '' (integer-indexed BurstGPT)."""
    idx = future_index(train_index, h, grain)
    if not isinstance(idx, pd.DatetimeIndex):
        return [""] * h
    return [d.strftime("%Y-%m-01") for d in idx]


def build_table(driver: str, point: np.ndarray, paths: np.ndarray, months: list[str], unit: str,
                model: str, source: str, grain: str, kind: str = "forecast") -> pd.DataFrame:
    """Long table: the point forecast (sample_id -1) then every path (0..n-1)."""
    h = len(point)
    vals = np.vstack([np.asarray(point, dtype=float)[None, :], np.asarray(paths, dtype=float)])
    sample = np.repeat(np.arange(-1, len(paths)), h)
    df = pd.DataFrame({"driver": driver, "period_index": np.tile(np.arange(1, h + 1), len(paths) + 1),
                       "calendar_month": np.tile(np.asarray(months, dtype=object), len(paths) + 1),
                       "sample_id": sample, "value": vals.reshape(-1), "unit": unit, "model": model,
                       "source": source, "grain": P3.GRAIN_NAME.get(grain, grain), "kind": kind})
    return enforce_types(df)


def enforce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Stable column types: int64 indices, float64 value, plain strings elsewhere."""
    df = df[P3.COLUMNS].copy()
    df["period_index"] = df["period_index"].astype("int64")
    df["sample_id"] = df["sample_id"].astype("int64")
    df["value"] = df["value"].astype("float64")
    for c in ("driver", "calendar_month", "unit", "model", "source", "grain", "kind"):
        df[c] = df[c].fillna("").astype(str).astype(object)
    return df


def write_table(df: pd.DataFrame, folder, driver: str) -> tuple:
    """Write <driver>.parquet and <driver>.csv; returns both paths."""
    folder.mkdir(parents=True, exist_ok=True)
    pq, csv = folder / f"{driver}.parquet", folder / f"{driver}.csv"
    df.to_parquet(pq, index=False)
    df.to_csv(csv, index=False)
    return pq, csv


def run_rate(paths: np.ndarray, point: np.ndarray, driver: str) -> pd.DataFrame:
    """30-day run-rate per path: sum of the 14 simulated days + 16 x mean of the last 7 (extrapolated)."""
    rr = P3.RUN_RATE
    extra = rr["days"] - rr["forecast_days"]
    vals = np.vstack([np.asarray(point)[None, :], paths])[:, : rr["forecast_days"]]
    total = vals.sum(axis=1) + extra * vals[:, -rr["tail_days"]:].mean(axis=1)
    return pd.DataFrame({"driver": driver, "sample_id": np.arange(-1, len(paths)),
                         "run_rate_30d": total, "extrapolated": True})


def run_rate_summary(rr: pd.DataFrame) -> pd.DataFrame:
    """P10, P50, P90 of the simulated run-rates (point forecast row excluded) per driver."""
    s = rr[rr["sample_id"] >= 0]
    rows = []
    for d, g in s.groupby("driver", sort=False):
        q = np.percentile(g["run_rate_30d"], [10, 50, 90])
        point = float(rr[(rr["driver"] == d) & (rr["sample_id"] == -1)]["run_rate_30d"].iloc[0])
        rows.append({"driver": d, "p10": q[0], "p50": q[1], "p90": q[2], "point_forecast": point,
                     "n_samples": len(g), "extrapolated_days": P3.RUN_RATE["days"] - P3.RUN_RATE["forecast_days"]})
    return pd.DataFrame(rows)
