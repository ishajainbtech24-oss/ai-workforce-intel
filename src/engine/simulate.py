"""Monte Carlo engine: public API `run_engine` and `summarise`.

Each draw picks one Phase 3 path index per forecast-driven driver, INDEPENDENTLY across drivers
(their correlations are unknown) and the same index for every month of a driver (a path is one
whole possible future). Before use each driver is widened by the uncertainty multiplier k:
value = point + k x (path - point), clipped at 0. numpy default_rng(seed) makes runs repeatable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config_phase4 as P4
from engine import model
from engine.drivers import DriverPaths

ROLE_ORDER = ("token_demand", "wages", "hosting", "token_price")
LINE_DRIVERS = {"token_expenditure": ("token_demand", "token_price"), "hosting": ("hosting",),
                "enablement": ("wages",), "integration": ("wages",)}


class ScenarioSkipped(RuntimeError):
    """A scenario cannot be run (needs_review row, missing row or unknown unit)."""


@dataclass
class EngineResult:
    """All (n_draws, T) arrays of one run plus per-draw summaries and metadata."""
    lines: dict[str, np.ndarray]
    value: np.ndarray
    total_cost: np.ndarray
    net: np.ndarray
    cum_net: np.ndarray
    break_even: np.ndarray
    peak_investment: np.ndarray
    cum_net_T: np.ndarray
    meta: dict = field(default_factory=dict)


def scenario_fraction(table: pd.DataFrame, scenario: str, inputs: dict) -> tuple[float, dict]:
    """Time saved as a fraction of an active user's work hours, from scenario_tables.csv.

    pct_of_work_hours: value / 100. pct_change_in_task_time (METR, a time INCREASE on AI-assisted
    tasks): -(value / 100) x ai_assisted_share_of_hours, which is negative (a downside).
    """
    for param in P4.SCENARIO_ROWS.get(scenario, []):
        rows = table[(table["scenario"] == scenario) & (table["parameter"] == param)]
        if rows.empty:
            continue
        r = rows.iloc[0]
        if str(r.get("status", "")) == "needs_review":
            raise ScenarioSkipped(f"scenario '{scenario}' skipped: row '{param}' has status needs_review")
        v = float(r["value"])
        if r["unit"] == "pct_of_work_hours":
            return v / 100.0, {"parameter": param, "raw": v, "unit": r["unit"],
                               "conversion": f"{v:g}% of work hours / 100 = {v / 100:.5f}"}
        if r["unit"] == "pct_change_in_task_time":
            share = inputs["ai_assisted_share_of_hours"]
            f = -v / 100.0 * share
            return f, {"parameter": param, "raw": v, "unit": r["unit"],
                       "conversion": f"-({v:g}% / 100) x ai_assisted_share_of_hours {share:g} = {f:.5f}"}
        raise ScenarioSkipped(f"scenario '{scenario}': unknown unit '{r['unit']}'")
    raise ScenarioSkipped(f"scenario '{scenario}' has no usable row in scenario_tables.csv")


def widen(driver_values: np.ndarray, k: float) -> np.ndarray:
    """point + k x (path - point) for every path row, clipped at 0 (row 0 is the point)."""
    point = driver_values[0]
    return np.maximum(point + k * (driver_values[1:] - point), 0.0)


def _draw(drivers: DriverPaths, n: int, rng, k: float) -> dict[str, np.ndarray]:
    out = {}
    for role in ROLE_ORDER:
        paths = widen(drivers[role].values, k)
        out[role] = paths[rng.integers(0, paths.shape[0], size=n)]
    return out


def _extrapolation(lines: dict, drivers: DriverPaths) -> dict:
    """Share of total cost (mean over draws) in months where a feeding driver is extrapolated."""
    T = drivers.T
    total = sum(float(v.sum()) for v in lines.values())
    per_driver, mask_any = {}, {ln: np.zeros(T, bool) for ln in lines}
    for role in ROLE_ORDER:
        d = drivers[role]
        ext = np.arange(1, T + 1) > d.covered_months
        cost = sum(float(lines[ln][:, ext].sum()) for ln, roles in LINE_DRIVERS.items() if role in roles)
        per_driver[role] = {"driver": d.name, "covered": d.covered_months, "extrapolated": d.extrapolated_months,
                            "share_of_total_cost": cost / total if total > 0 else 0.0,
                            "used_fallback": d.used_fallback}
        for ln, roles in LINE_DRIVERS.items():
            if role in roles:
                mask_any[ln] |= ext
    any_share = sum(float(lines[ln][:, m].sum()) for ln, m in mask_any.items()) / total if total > 0 else 0.0
    return {"per_driver": per_driver, "share_any": any_share}


def run_engine(inputs: dict, scenario: str, multiplier: float = 1.0, n_draws: int = P4.N_DRAWS,
               seed: int = P4.SEED, drivers: DriverPaths | None = None, scenarios: pd.DataFrame | None = None,
               time_saved_fraction: float | None = None, input_spread: dict | None = None) -> EngineResult:
    """One Monte Carlo run (see module docstring). `drivers` must be loaded for inputs['horizon_months'].

    After the forecast paths, each draw also takes its own time saved, realisation rate, adoption target and
    training hours: the entered value times a PERT draw from `input_spread` (default config_phase4.INPUT_SPREAD;
    {} keeps them fixed). The forecast-path draws come first, so they are the same with or without the spread."""
    if drivers is None:
        raise ValueError("pass preloaded DriverPaths (engine.drivers.load_drivers)")
    T = int(inputs["horizon_months"])
    if drivers.T != T:
        raise ValueError(f"drivers were loaded for T={drivers.T}, inputs ask for T={T}")
    if time_saved_fraction is None:
        time_saved_fraction, sc_info = scenario_fraction(scenarios, scenario, inputs)
    else:
        sc_info = {"parameter": "given", "raw": time_saved_fraction, "conversion": "given directly"}
    rng = np.random.default_rng(seed)
    d = _draw(drivers, n_draws, rng, multiplier)
    staff = inputs["base_hourly_wage_staff"] * d["wages"]
    eng = inputs["base_hourly_wage_engineer"] * d["wages"]
    price = d["token_price"] * (inputs["fixed_token_price_per_mtok"] if drivers["token_price"].used_fallback
                                else inputs["price_multiplier_vs_frontier"])
    spread = P4.INPUT_SPREAD if input_spread is None else input_spread
    mult = {name: model.pert(rng, *spread[name], n_draws) if name in spread else None
            for name in ("time_saved", "realisation_rate", "adoption_target", "training_hours_per_new_user")}
    tsf = time_saved_fraction if mult["time_saved"] is None else time_saved_fraction * mult["time_saved"]
    rr = None if mult["realisation_rate"] is None else np.clip(inputs["realisation_rate"] * mult["realisation_rate"], 0, 1)
    tgt = None if mult["adoption_target"] is None else np.clip(
        inputs["adoption_target"] * mult["adoption_target"], inputs["adoption_start"], 1.0)
    trn = None if mult["training_hours_per_new_user"] is None else (
        inputs["training_hours_per_new_user"] * mult["training_hours_per_new_user"])
    U, N, U0 = model.adoption(inputs, T, tgt)
    E = model.effective_users(U0, N, int(inputs["benefit_lag_months"]))
    lines = {"token_expenditure": model.token_expenditure(U, inputs["tokens_per_active_user_per_month"],
                                                          d["token_demand"], price),
             "hosting": model.hosting(inputs["base_monthly_hosting_cost"], d["hosting"]),
             "enablement": model.enablement(inputs, U, N, staff, trn),
             "integration": model.integration(inputs, T, eng)}
    total = sum(lines.values())
    val = model.value(inputs, E, tsf, staff, rr)
    net = val - total
    cum = np.cumsum(net, axis=1)
    meta = {"scenario": scenario, "multiplier": multiplier, "n_draws": n_draws, "seed": seed, "T": T,
            "time_saved_fraction": time_saved_fraction, "scenario_info": sc_info,
            "U": U, "N": N, "U0": U0, "E": E, "input_spread": spread,
            "input_draws": {k: v for k, v in mult.items() if v is not None}, "extrapolation": _extrapolation(lines, drivers),
            "fallbacks": [r for r in ROLE_ORDER if drivers[r].used_fallback]}
    return EngineResult(lines=lines, value=val, total_cost=total, net=net, cum_net=cum,
                        break_even=model.break_even(cum), peak_investment=np.maximum(-cum.min(axis=1), 0.0),
                        cum_net_T=cum[:, -1], meta=meta)


def _q(x: np.ndarray) -> dict:
    p = np.nanpercentile(x, [10, 50, 90]) if np.isfinite(x).any() else [np.nan] * 3
    return {"p10": float(p[0]), "p50": float(p[1]), "p90": float(p[2])}


def summarise(res: EngineResult) -> dict:
    """P10/P50/P90 by month, break-even summary, totals, peak investment, extrapolation share."""
    monthly = []
    series = {**res.lines, "total_cost": res.total_cost, "value": res.value, "cumulative_net": res.cum_net}
    for name, arr in series.items():
        p = np.percentile(arr, [10, 50, 90], axis=0)
        for m in range(arr.shape[1]):
            monthly.append({"month": m + 1, "line": name, "p10": p[0, m], "p50": p[1, m], "p90": p[2, m]})
    be = res.break_even
    hit = np.isfinite(be)
    return {"monthly": pd.DataFrame(monthly),
            "break_even": {"prob_within_T": float(hit.mean()), "share_none": float(1 - hit.mean()),
                           **(_q(be[hit]) if hit.any() else {"p10": np.nan, "p50": np.nan, "p90": np.nan})},
            "total_cost": _q(res.total_cost.sum(axis=1)), "total_value": _q(res.value.sum(axis=1)),
            "peak_investment": _q(res.peak_investment), "cum_net_T": _q(res.cum_net_T),
            "line_totals_p50": {ln: float(np.median(v.sum(axis=1))) for ln, v in res.lines.items()},
            "extrapolation": res.meta["extrapolation"]}
