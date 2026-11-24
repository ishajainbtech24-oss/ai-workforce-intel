"""PHASE4_SUMMARY.md sections: sanity checks, review talking points, limitations, deviations."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase4 as P4


def _usd(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"${x:,.0f}"


def _pct(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.0%}"


def sanity_checks(runs: dict) -> list[dict]:
    """The four required checks, each with pass/fail and the numbers behind it."""
    out = []
    diff = max(float(np.max(np.abs(res.total_cost - sum(res.lines.values())))) for res, _ in runs.values())
    out.append({"check": "total cost = sum of the four lines (every draw and month)", "passed": diff < 1e-6,
                "detail": f"largest difference {diff:.2e} USD"})
    s = {sc: summ for (sc, k), (_, summ) in runs.items() if k == 1.0}
    if {"expected", "downside"} <= set(s):
        ev, dv = s["expected"]["total_value"]["p50"], s["downside"]["total_value"]["p50"]
        out.append({"check": "expected median value > 0 and downside below expected", "passed": ev > 0 and dv < ev,
                    "detail": f"expected {_usd(ev)}, downside {_usd(dv)}"})
    order = [sc for sc in ("optimistic", "expected", "downside") if sc in s]
    probs = [s[sc]["break_even"]["prob_within_T"] for sc in order]
    out.append({"check": "P(break-even): optimistic >= expected >= downside",
                "passed": all(a >= b for a, b in zip(probs, probs[1:])),
                "detail": ", ".join(f"{sc} {_pct(p)}" for sc, p in zip(order, probs))})
    ks = sorted(k for sc, k in runs if sc == "expected")
    if len(ks) >= 2:
        lo, hi = runs[("expected", ks[0])][1], runs[("expected", ks[-1])][1]
        def width(x):
            b = x["break_even"]
            return (b["p90"] - b["p10"]) if x["break_even"]["prob_within_T"] > 0 else None
        wl, wh = width(lo), width(hi)
        if wl is None or wh is None:
            wl, wh = (lo["cum_net_T"]["p90"] - lo["cum_net_T"]["p10"]), (hi["cum_net_T"]["p90"] - hi["cum_net_T"]["p10"])
            what = "no break-even in the expected scenario, so the cumulative-net-at-T P10-P90 width is compared"
        else:
            what = "break-even month P10-P90 width"
        out.append({"check": f"k = {ks[-1]:g} gives a range at least as wide as k = {ks[0]:g} (expected)",
                    "passed": wh >= wl - 1e-9, "detail": f"{what}: {wl:,.2f} at k = {ks[0]:g}, {wh:,.2f} at k = {ks[-1]:g}"})
    return out


def sanity_section(ctx) -> list[str]:
    rows = pd.DataFrame([{"check": c["check"], "result": "PASS" if c["passed"] else "FAIL", "detail": c["detail"]}
                         for c in ctx["sanity"]])
    head = "| " + " | ".join(rows.columns) + " |"
    body = ["| " + " | ".join(map(str, r)) + " |" for r in rows.itertuples(index=False)]
    return ["## Sanity checks", "", head, "|---|---|---|", *body, ""]


def review(ctx, t: dict) -> list[str]:
    be, tot = t["break_even"].set_index(["scenario", "multiplier"]), t["totals"].set_index(["scenario", "multiplier"])
    T = int(t["break_even"]["T"].iloc[0])
    s = ["The engine turns the Phase 3 forecast paths and a company's own inputs into monthly cost, value and "
         f"break-even over {T} months, with {ctx['n_draws']:,} Monte Carlo draws per run."]
    if ctx["illustrative"]:
        s.append("All company numbers here belong to an illustrative example company and must be replaced with real ones.")
    for sc in ("expected", "optimistic", "downside"):
        if (sc, 1.0) in be.index:
            b, x = be.loc[(sc, 1.0)], tot.loc[(sc, 1.0)]
            when = (f"breaks even within {T} months in {_pct(b['prob_break_even_within_T'])} of draws (median month "
                    f"{b['p50_month']:.0f})" if b["prob_break_even_within_T"] > 0 else f"does not break even within {T} months")
            s.append(f"In the {sc} scenario the programme {when}; median total cost {_usd(x['total_cost_p50'])} against "
                     f"median value {_usd(x['total_value_p50'])}.")
    bd = t["breakdown"]
    b1 = bd[(bd["scenario"] == "expected") & (bd["multiplier"] == 1.0)].sort_values("p50_share_of_cost", ascending=False)
    if len(b1):
        s.append(f"The largest cost line is {b1.iloc[0]['line']} ({_pct(b1.iloc[0]['p50_share_of_cost'])}), an "
                 f"{b1.iloc[0]['type'].lower()}; forecast-driven lines are "
                 f"{_pct(b1[b1['type'] == 'Forecast-driven']['p50_share_of_cost'].sum())} of cost.")
    sens = t.get("sensitivity")
    if sens is not None and len(sens):
        s.append(f"The tornado shows {sens['input'].iloc[0]} and {sens['input'].iloc[1]} move the result most.")
    s.append("No public data links AI use to a company's outcomes, so value is a scenario projection, not a forecast.")
    s.append("Uncertainty from the forecasts is widened by k = 1.5 and 2.0 because Phase 3 found its intervals too narrow.")
    return ["## 8. What to say in the review", "", " ".join(s[:10]), ""]


def limitations(ctx) -> list[str]:
    share = ctx.get("input_token_share")
    return ["## 9. Limitations", "",
            "- Drivers are drawn independently; their correlations are unknown.",
            "- Months beyond a driver's forecast horizon are extrapolated flat (section 7).",
            "- BurstGPT is one provider's trace; only its relative variation is used as a demand factor.",
            "- Tokens per active user comes from WildChat consumer chats and counts output tokens only; it is not an "
            "enterprise measurement.",
            "- The time-saved scenarios come from survey (FRED GenAI tracker) and trial (METR) evidence; the downside "
            "applies METR's task-time increase to the illustrative share of AI-assisted hours.",
            "- Phase 3 found the forecast intervals under-cover on the holdout; the multipliers 1.5 and 2.0 are a "
            "sensitivity response, not a calibration.",
            "- Engine month 1 is the first forecast month of each driver; the drivers' data end at different dates.",
            "- The example company's inputs are illustrative." + (f" The measured input-token share is {_pct(share)}."
                                                                   if share is not None else ""), ""]


def deviations(ctx) -> list[str]:
    share = ctx.get("input_token_share")
    items = [
        "There is no Epoch price forecast in Phase 3, so token_price uses the flat fixed_token_price_per_mtok input "
        "(flagged used_fallback); price_multiplier_vs_frontier is kept but has no effect.",
        f"The prompt says input tokens are 83% of the blended price; the measured BurstGPT share in inputs_for_phase4.json "
        f"is {_pct(share)}. It is recorded only; there is no Epoch blended price to weight." if share is not None else
        "The input-token share was not available.",
        "The downside row is a task-time CHANGE (METR), not a share of work hours. It is converted with an extra "
        "illustrative input, ai_assisted_share_of_hours: fraction = -(value / 100) x that share.",
        "The token-demand run-rate covers month 1 only; months 2..T of token demand are flat-extrapolated.",
        "Extra input maintenance_during_build (bool) makes the 'during the build, if the user sets it' rule explicit.",
        "Sensitivity on 'base wages' scales staff and engineer wages together; adoption_target and realisation_rate "
        "are capped at 1.",
        "The data contract lists the forecast files from manifest.json and the engine role mapping with found/missing status.",
    ]
    if ctx["fast"]:
        items.append("--fast: 1,000 draws and no tornado chart (the sensitivity table is still written).")
    items += [f"Scenario skipped: {m}" for m in ctx["skipped"]]
    return ["## 10. Deviations from the Phase 4 prompt", ""] + [f"- {i}" for i in items] + [""]
