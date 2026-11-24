"""One-at-a-time sensitivity (tornado): each main input at -20% and +20%, same seed and draws.

The +-20% range is an ILLUSTRATIVE STRESS RANGE, not a measured uncertainty. Shares are capped
at 1. A median break-even month is reported as 'beyond T months' when fewer than half of the
draws break even within the horizon.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase4 as P4
from engine.simulate import run_engine

WAGE_FIELDS = ("base_hourly_wage_staff", "base_hourly_wage_engineer")
SHARES = ("adoption_target", "realisation_rate")


def median_break_even(be: np.ndarray) -> float:
    """Median break-even month with 'no break-even' counted as later than T (inf if the median has none)."""
    return float(np.median(np.where(np.isfinite(be), be, np.inf)))


def _scaled(inputs: dict, name: str, factor: float) -> dict:
    out = dict(inputs)
    fields = WAGE_FIELDS if name == "base_wages" else (name,)
    for f in fields:
        v = inputs[f] * factor
        out[f] = min(v, 1.0) if f in SHARES else (int(round(v)) if f == "employees" else v)
    out["adoption_target"] = max(out["adoption_target"], out["adoption_start"])
    return out


def tornado(inputs: dict, drivers, scenarios: pd.DataFrame, scenario: str = "expected", multiplier: float = 1.0,
            n_draws: int = P4.N_DRAWS, seed: int = P4.SEED, step: float = P4.SENSITIVITY_STEP) -> pd.DataFrame:
    """Median break-even and median cumulative net at T for each input at -step and +step."""
    base = run_engine(inputs, scenario, multiplier, n_draws, seed, drivers, scenarios)
    base_frac = base.meta["time_saved_fraction"]
    rows = []
    for name in P4.SENSITIVITY_INPUTS:
        rec = {"input": name, "base_median_break_even": median_break_even(base.break_even),
               "base_median_cum_net_T": float(np.median(base.cum_net_T))}
        for tag, factor in (("low", 1 - step), ("high", 1 + step)):
            if name == "time_saved_parameter":
                r = run_engine(inputs, scenario, multiplier, n_draws, seed, drivers, scenarios,
                               time_saved_fraction=base_frac * factor)
                rec[tag] = base_frac * factor
            else:
                sc = _scaled(inputs, name, factor)
                r = run_engine(sc, scenario, multiplier, n_draws, seed, drivers, scenarios)
                rec[tag] = sc[WAGE_FIELDS[0]] if name == "base_wages" else sc[name]
            rec[f"median_break_even_{tag}"] = median_break_even(r.break_even)
            rec[f"median_cum_net_T_{tag}"] = float(np.median(r.cum_net_T))
        rec["swing_cum_net_T"] = abs(rec["median_cum_net_T_high"] - rec["median_cum_net_T_low"])
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("swing_cum_net_T", ascending=False).reset_index(drop=True)
