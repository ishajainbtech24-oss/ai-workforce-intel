"""PHASE4_SUMMARY.md, written from the run results (no hard-coded numbers, no placeholders)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase4 as P4
from tsaf.report import fmt, md_table


def _usd(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"${x:,.0f}"


def _month(x) -> str:
    return "none" if x is None or not np.isfinite(x) else f"{x:.0f}"


def _pct(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.0%}"


def s1_inputs(ctx) -> list[str]:
    a = ctx["assumptions"]["inputs"]
    t = pd.DataFrame([{"input": k, "value": str(v["value"]), "unit": v["unit"], "type": v["evidence_type"],
                       "note": v["note"]} for k, v in a.items()])
    head = ("**All inputs below describe an illustrative example company (made-up values, flagged "
            "`illustrative`), not a real organisation.**" if ctx["illustrative"] else "Inputs supplied by the user.")
    return ["## 1. Inputs used", "", head, "", md_table(t), ""]


def s2_types(ctx) -> list[str]:
    fb = ctx["fallbacks"]
    rows = [("Token expenditure", "Forecast-driven", "BurstGPT demand factor x tokens per user x price"
             + (" (price: flat fixed input, no Epoch forecast)" if "token_price" in fb else "")),
            ("Infrastructure / hosting", "Forecast-driven", "base hosting cost x PPI hosting paths"),
            ("Workforce enablement", "Estimate", "training hours from the inputs x ECI wage paths"),
            ("Integration", "Estimate", "engineering hours from the inputs x ECI wage paths"),
            ("Business outcomes (value)", "Projection", "scenario time saved x hours x realisation x wages")]
    return ["## 2. The four outputs and their evidence types", "",
            md_table(pd.DataFrame(rows, columns=["output", "type", "built from"])), ""]


def s3_results(t: dict) -> list[str]:
    be, tot = t["break_even"], t["totals"]
    j = be.merge(tot, on=["scenario", "multiplier"])
    rows = [{"scenario": r.scenario, "k": f"{r.multiplier:g}", "P(break-even)": _pct(r.prob_break_even_within_T),
             "month P10/P50/P90": f"{_month(r.p10_month)} / {_month(r.p50_month)} / {_month(r.p90_month)}",
             "total cost P50": _usd(r.total_cost_p50), "total value P50": _usd(r.total_value_p50),
             "peak investment P50": _usd(r.peak_investment_p50), "cum. net at T P50": _usd(r.cum_net_T_p50)}
            for r in j.itertuples()]
    T = int(be["T"].iloc[0])
    return [f"## 3. Results per scenario and uncertainty multiplier (horizon {T} months)", "",
            md_table(pd.DataFrame(rows)), "", "Break-even months are counted among the draws that break even "
            f"within {T} months; 'none' means no draw broke even within {T} months.", ""]


def s4_breakdown(t: dict) -> list[str]:
    b = t["breakdown"]
    b1 = b[(b["scenario"] == "expected") & (b["multiplier"] == 1.0)] if len(b[b["scenario"] == "expected"]) else b
    b1 = b1.sort_values("p50_share_of_cost", ascending=False)
    top = b1.iloc[0]
    by_type = b1.groupby("type")["p50_share_of_cost"].sum()
    rows = b1[["line", "type", "p50_total", "p50_share_of_cost"]].assign(
        p50_total=lambda d: d["p50_total"].map(_usd), p50_share_of_cost=lambda d: d["p50_share_of_cost"].map(_pct))
    return ["## 4. Cost breakdown (expected scenario, k = 1)", "", md_table(rows), "",
            f"The largest line is **{top['line']}** ({_pct(top['p50_share_of_cost'])} of cost, {top['type']}). "
            f"Forecast-driven lines are {_pct(by_type.get('Forecast-driven', 0.0))} of cost and estimated lines "
            f"{_pct(by_type.get('Estimate', 0.0))}, so most of the cost rests on the company's own inputs, not on "
            "the forecasts.", ""]


def s5_multiplier(t: dict) -> list[str]:
    tot = t["totals"]
    out = ["## 5. Effect of the uncertainty multiplier", ""]
    for sc, g in tot.groupby("scenario", sort=False):
        w = {r.multiplier: r.cum_net_T_p90 - r.cum_net_T_p10 for r in g.itertuples()}
        out.append(f"- {sc}: P10-P90 spread of cumulative net at T is " +
                   ", ".join(f"{_usd(v)} at k = {k:g}" for k, v in sorted(w.items())) + ".")
    kmax = tot["multiplier"].max()
    g = tot[tot["multiplier"] == kmax]
    rel = float(((g["cum_net_T_p90"] - g["cum_net_T_p10"]) / g["total_cost_p50"]).max())
    out += ["", f"At k = {kmax:g} the widest P10-P90 spread of cumulative net at T is {_pct(rel)} of the median total "
            "cost. " + ("That is small: the forecast-driven drivers (wages, hosting, token demand) move only a little "
                        "around their point forecasts, and the large cost lines are estimates from the inputs, so "
                        "widening the forecast uncertainty barely changes the answer; the inputs matter far more "
                        "(section 6)." if rel < 0.10 else
                        "That is material: the forecast uncertainty changes the answer noticeably."), ""]
    return out


def s6_tornado(t: dict) -> list[str]:
    s = t.get("sensitivity")
    if s is None or s.empty:
        return ["## 6. Which inputs matter (tornado)", "", "Sensitivity not run.", ""]
    rows = s[["input", "median_cum_net_T_low", "median_cum_net_T_high", "median_break_even_low",
              "median_break_even_high"]].copy()
    for c in ("median_cum_net_T_low", "median_cum_net_T_high"):
        rows[c] = rows[c].map(_usd)
    for c in ("median_break_even_low", "median_break_even_high"):
        rows[c] = rows[c].map(lambda x: "beyond T" if not np.isfinite(x) else f"{x:.0f}")
    top = ", ".join(f"`{x}`" for x in s["input"].head(3))
    return ["## 6. Which inputs matter (tornado, expected scenario, k = 1)", "",
            "Each input moved by -20% and +20% (an illustrative stress range, not a measured uncertainty).", "",
            md_table(rows), "", f"The three inputs with the largest swing in cumulative net at T: {top}.", ""]


def s7_extrapolation(t: dict) -> list[str]:
    e = t["extrapolation"]
    p1 = lambda x: f"{x:.1%}"  # noqa: E731 - one decimal: these shares can be small
    n = lambda x: "-" if not np.isfinite(x) else str(int(x))  # noqa: E731
    rows = pd.DataFrame({"role": e["role"], "driver": e["driver"],
                         "months covered": e["months_covered_by_forecast"].map(n),
                         "months extrapolated": e["months_extrapolated"].map(n),
                         "fallback": e["used_fallback"].map({True: "yes", False: "no"}),
                         "share of total cost in extrapolated months":
                             e["share_of_total_cost_in_extrapolated_months"].map(p1)})
    anyr = e[e["role"] == "any"]["share_of_total_cost_in_extrapolated_months"].iloc[0]
    return ["## 7. Extrapolation", "", md_table(rows), "",
            f"{p1(anyr)} of total cost falls in months where at least one driver feeding that cost line is "
            "extrapolated flat beyond its forecast horizon.", ""]


def write_summary(path, ctx: dict, t: dict) -> None:
    from engine.summary_text import deviations, limitations, review, sanity_section
    parts = (["# Phase 4 summary: Monte Carlo cost and value engine", "",
              f"Generated by `python src/run_phase4.py{' --fast' if ctx['fast'] else ''}`"
              + (" for an **illustrative example company**" if ctx["illustrative"] else "")
              + f"; {ctx['n_draws']:,} draws per run, seed {ctx['seed']}. Every number comes from this run.", ""]
             + s1_inputs(ctx) + s2_types(ctx) + s3_results(t) + s4_breakdown(t) + s5_multiplier(t)
             + s6_tornado(t) + s7_extrapolation(t) + sanity_section(ctx) + review(ctx, t) + limitations(ctx)
             + deviations(ctx))
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
