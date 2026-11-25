"""Decision figures for the Money pages and the downloads: NPV, return on cost, cost per person using AI, a goal-seek
(how much time AI must save to give an even chance of paying back) and the scenario file (save / load a view).

Everything is worked out from the same engine and the same saved or cached results the pages show; money stays in
US dollars here (the engine's unit) and is converted to rupees only when shown."""
from __future__ import annotations

import json

import numpy as np
import streamlit as st

from dashboard.core import data as D

DISCOUNT_RATE = 0.10        # a year, for the net present value of the typical monthly flows
GOAL_CHANCE = 0.5           # goal-seek target: an even chance of paying back within the horizon
GOAL_DRAWS = 1000           # draws per goal-seek step (enough for a share near 50%)
SCENARIO_FORMAT, SCENARIO_VERSION = "aiwi-scenario", 1


def npv(monthly_net, annual_rate: float = DISCOUNT_RATE) -> float:
    """Net present value of monthly flows (first flow at the end of month 1)."""
    r = (1 + annual_rate) ** (1 / 12) - 1
    flows = np.asarray(monthly_net, float)
    return float(np.sum(flows / (1 + r) ** np.arange(1, len(flows) + 1)))


def active_users(inputs: dict) -> np.ndarray:
    from engine import model
    U, _, _ = model.adoption(inputs, int(inputs["horizon_months"]))
    return U


def metrics(scenario: str, k: float) -> dict:
    """Decision figures of one outlook and caution level, for the figures the Money pages show."""
    tot, be = D.row("totals_summary", scenario, k), D.row("break_even_summary", scenario, k)
    net = D.monthly(scenario, k, "value")["p50"].to_numpy() - D.monthly(scenario, k, "total_cost")["p50"].to_numpy()
    user_months = float(active_users(D.active_inputs()).sum())
    cost = float(tot["total_cost_p50"])
    return {"scenario": scenario, "k": float(k), "cost": cost, "benefit": float(tot["total_value_p50"]),
            "balance": float(tot["cum_net_T_p50"]), "balance_low": float(tot["cum_net_T_p10"]),
            "balance_high": float(tot["cum_net_T_p90"]), "chance": float(be["prob_break_even_within_T"]),
            "month": float(be["p50_month"]) if be["prob_break_even_within_T"] > 0 else float("nan"),
            "npv": npv(net), "roi": float(tot["cum_net_T_p50"]) / cost if cost else float("nan"),
            "cost_per_user_month": cost / user_months if user_months else float("nan"), "T": int(be["T"])}


def all_metrics(k: float) -> list[dict]:
    return [metrics(s, k) for s in D.outlooks()]


@st.cache_resource(show_spinner=False, max_entries=32)
def _goal_seek(frozen: tuple, scenario: str, root_str: str) -> dict:
    from engine.simulate import ScenarioSkipped, run_engine, scenario_fraction
    inputs = dict(frozen)
    T = int(inputs["horizon_months"])
    dr, sc = D.drivers(T), D.outlook_table()
    try:
        base, _ = scenario_fraction(sc, scenario, inputs)
    except ScenarioSkipped:
        return {"status": "skipped"}

    def chance(fraction: float) -> float:
        r = run_engine(inputs, scenario, 1.0, GOAL_DRAWS, D.SEED, dr, sc, time_saved_fraction=fraction)
        return float(np.isfinite(r.break_even).mean())

    now = chance(base)
    lo, hi = 0.0, max(base, 0.01)
    while chance(hi) < GOAL_CHANCE:
        hi *= 2
        if hi > 1.0:  # even saving all working time would not do it
            return {"status": "unreachable", "base": base, "chance_now": now}
    for _ in range(18):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if chance(mid) < GOAL_CHANCE else (lo, mid)
    return {"status": "ok", "base": base, "needed": hi, "chance_now": now}


def goal_seek(scenario: str = "expected") -> dict:
    """Time saved (share of work hours) that gives an even chance of paying back within the horizon, for the
    figures shown, with everything else as entered. Worked out once per server for each set of figures."""
    return _goal_seek(D._frozen(D.active_inputs()), scenario, str(D.root()))


# ---------------------------------------------------------------- scenario file (save and load a view)
def scenario_payload(view: dict, form: dict | None) -> bytes:
    """The scenario file: the view (company, outlook, caution) and, when present, the figures typed on Try your own
    numbers (as shown on the form, money in rupees). Stays on the visitor's computer; nothing is stored here."""
    doc = {"format": SCENARIO_FORMAT, "version": SCENARIO_VERSION, "view": view}
    if form:
        doc["figures"] = form
    return json.dumps(doc, indent=1, default=float).encode("utf-8")


def read_scenario(raw: bytes, fields: set[str]) -> tuple[dict | None, str | None]:
    """(document, None) for a valid scenario file, else (None, the problem in plain words)."""
    from dashboard.ui import copy as C
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, C.SCENARIO_BAD_FILE
    if not isinstance(doc, dict) or doc.get("format") != SCENARIO_FORMAT:
        return None, C.SCENARIO_BAD_FILE
    figs = doc.get("figures") or {}
    if not isinstance(figs, dict) or any(k not in fields for k in figs):
        return None, C.SCENARIO_BAD_FIELDS
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not np.isfinite(v) or v < 0 for v in figs.values()):
        return None, C.SCENARIO_BAD_VALUES
    return doc, None


def memo(scenario: str) -> dict:
    """Sentences and rows of the PDF decision memo, for the figures shown (standard caution level)."""
    from dashboard.core import logic
    from dashboard.ui import copy as C
    from engine.simulate import scenario_fraction
    rows = all_metrics(1.0)
    mine = next(r for r in rows if r["scenario"] == scenario)
    lines = [logic.verdict(mine["chance"], mine["month"], mine["T"])]
    if D.row("totals_summary", scenario, 1.0)["total_value_p90"] < 0:
        lines.append(C.NEGATIVE_BENEFIT.format(outlook=C.OUTLOOK[scenario].lower()))
    g = goal_seek("expected")
    if g.get("status") == "ok":
        pct = lambda f: f"{f:.1%}"  # noqa: E731
        base, sc = D.active_inputs(), D.outlook_table()
        lines.append(C.GOAL_LINE.format(months=mine["T"], needed=pct(g["needed"]),
                                        expected=pct(scenario_fraction(sc, "expected", base)[0]),
                                        optimistic=pct(scenario_fraction(sc, "optimistic", base)[0])))
    elif g.get("status") == "unreachable":
        lines.append(C.GOAL_UNREACHABLE.format(months=mine["T"]))
    return {"lines": lines, "rows": rows}
