"""Schema checks for the Phase 3 forecast files and the scenario table.

`check_forecast_table` and `check_scenarios` return a list of problems (empty = PASS); they
never raise, so one failing driver is reported without stopping the others.
"""
from __future__ import annotations

import pandas as pd

import config_phase3 as P3

SCENARIO_COLUMNS = ["scenario", "parameter", "value", "unit", "source", "derivation", "status", "kind"]


def check_forecast_table(df: pd.DataFrame, horizon: int, n_samples: int = P3.N_SAMPLES) -> list[str]:
    """Problems with one driver's forecast table (see module docstring)."""
    probs: list[str] = []
    if list(df.columns) != P3.COLUMNS:
        missing = [c for c in P3.COLUMNS if c not in df.columns]
        probs.append(f"missing columns {missing}" if missing else f"column order {list(df.columns)}")
        if missing:
            return probs
    if df["value"].isna().any():
        probs.append(f"{int(df['value'].isna().sum())} missing values")
    neg = df["unit"].isin(P3.NON_NEGATIVE_UNITS) & (df["value"] < 0)
    if neg.any():
        probs.append(f"{int(neg.sum())} negative values for a volume/price unit")
    sims = df.loc[df["sample_id"] >= 0, "sample_id"].nunique()
    if sims != n_samples or not (df["sample_id"] == P3.POINT_SAMPLE_ID).any():
        probs.append(f"{sims} simulated paths (expected {n_samples}) plus the point forecast")
    if sorted(df["period_index"].unique()) != list(range(1, horizon + 1)):
        probs.append(f"periods {df['period_index'].min()}-{df['period_index'].max()} (expected 1-{horizon})")
    dup = df.duplicated(["driver", "period_index", "sample_id"]).sum()
    if dup:
        probs.append(f"{int(dup)} duplicate (driver, period_index, sample_id) rows")
    for c in ("unit", "model"):
        if (df[c].astype(str).str.strip() == "").any():
            probs.append(f"empty {c}")
    if not (df["kind"] == "forecast").all():
        probs.append("kind is not 'forecast' everywhere")
    if not pd.api.types.is_integer_dtype(df["period_index"]) or not pd.api.types.is_integer_dtype(df["sample_id"]):
        probs.append("period_index / sample_id are not integers")
    return probs


def check_scenarios(df: pd.DataFrame) -> list[str]:
    """Problems with scenario_tables.csv (kind column, values, source and derivation on every row)."""
    probs: list[str] = []
    missing = [c for c in SCENARIO_COLUMNS if c not in df.columns]
    if missing:
        return [f"missing columns {missing}"]
    if not (df["kind"] == "assumption").all():
        probs.append("kind is not 'assumption' everywhere")
    if df["value"].isna().any():
        probs.append(f"{int(df['value'].isna().sum())} missing values")
    for c in ("source", "derivation"):
        empty = df[c].isna() | (df[c].astype(str).str.strip() == "")
        if empty.any():
            probs.append(f"{int(empty.sum())} row(s) without {c}")
    return probs


def result_row(name: str, problems: list[str]) -> dict:
    return {"file": name, "status": "PASS" if not problems else "FAIL", "problems": "; ".join(problems)}
