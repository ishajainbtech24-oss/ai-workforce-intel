"""The three-line guide under every chart: What you see, What it means, Why it matters.

Pure functions (no Streamlit calls). 'What it means' is always filled in from the same numbers the chart draws, so a
test can recompute it; nothing here guesses or adds facts the results do not hold.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dashboard import copy as C
from dashboard import logic_forecasts as LF
from dashboard import theme as T

FLAT = 0.005  # changes under half a percent read as 'about the same'


def _direction(change: float) -> str:
    if not math.isfinite(change) or abs(change) < FLAT:
        return "flat"
    return "up" if change > 0 else "down"


def _guide(key: str, **kw) -> tuple[str, str, str]:
    see, means, why = C.GUIDE[key]
    return see.format(**kw), means.format(**kw), why.format(**kw)


# ---------------------------------------------------------------- Welcome
def welcome(d: dict) -> tuple[str, str, str]:
    """Hosting prices (index December 2000 = 100, as in the source)."""
    change = d["expected"][-1] / d["hist_values"][-1] - 1
    above = d["expected"][-1] / 100.0 - 1
    direction = _direction(change)
    return _guide("welcome", direction=C.DIRECTION_VERB[direction], change=f"by {LF.pct(abs(change))}"
                  if direction != "flat" else "", n=len(d["expected"]),
                  pct_base=C.PCT_ABOVE_BASE["above" if above >= 0 else "below"].format(pct=LF.pct(abs(above))))


# ---------------------------------------------------------------- money pages
def balance(series: dict, paybacks: dict, horizon: int) -> tuple[str, str, str]:
    """Running balance by outlook. series: outlook -> DataFrame(month, p50); paybacks: outlook -> month or None."""
    e = series["expected"]
    if paybacks.get("expected"):
        story = C.STORY_BALANCE_PAYS.format(month=int(paybacks["expected"]), end=T.money(float(e["p50"].iloc[-1])))
    else:
        i = int(np.argmin(e["p50"].to_numpy()))
        story = C.STORY_BALANCE.format(lowest=T.money(float(e["p50"].iloc[i])), low_month=int(e["month"].iloc[i]),
                                       end=T.money(float(e["p50"].iloc[-1])))
        if paybacks.get("optimistic"):
            story += C.STORY_OTHERS_PAY.format(month=int(paybacks["optimistic"]))
        elif not any(paybacks.values()):
            story += C.STORY_NONE_PAY.format(months=horizon)
    return _guide("balance", story=story)


def year_end(items: list[dict], months: int) -> tuple[str, str, str]:
    vals = [it["value"] for it in items]
    return _guide("year_end", months=months, good=sum(v >= 0 for v in vals), gap=T.money(max(vals) - min(vals)))


def cost_stack(total: pd.DataFrame) -> tuple[str, str, str]:
    """total: DataFrame(month, p50) of the total monthly cost."""
    i = int(np.argmax(total["p50"].to_numpy()))
    return _guide("cost_stack", peak=T.money(float(total["p50"].iloc[i])), peak_month=int(total["month"].iloc[i]),
                  late=T.money(float(total["p50"].iloc[-1])))


def donut(shares: pd.DataFrame, key: str = "donut") -> tuple[str, str, str]:
    """shares: line, p50_total."""
    tot = float(shares["p50_total"].sum())
    top = shares.loc[shares["p50_total"].idxmax()]
    return _guide(key, biggest=C.LINE[top["line"]], share=T.share(float(top["p50_total"]) / tot if tot else 0.0))


def benefit_cost(cost: pd.DataFrame, value: pd.DataFrame) -> tuple[str, str, str]:
    above = (value["p50"].to_numpy() > cost["p50"].to_numpy())
    story = (C.STORY_BENEFIT_ABOVE.format(month=int(cost["month"].to_numpy()[np.argmax(above)])) if above.any()
             else C.STORY_BENEFIT_BELOW)
    return _guide("benefit_cost", story=story)


def _names(labels: list[str]) -> str:
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]


def timing_dots(rows: list[dict]) -> tuple[str, str, str]:
    months = rows[0]["horizon"] if rows else 12
    parts = []
    for templates, names in ((C.STORY_DOTS_PAYS, [r["label"] for r in rows if r["month"] is not None]),
                             (C.STORY_DOTS_NONE, [r["label"] for r in rows if r["month"] is None])):
        if names:
            parts.append(templates[len(names) > 1].format(names=_names(names), months=months))
    return _guide("timing_dots", story=". ".join(parts) + ".")


def timing_bars(counts: list[int], none: int, runs: int, months: int) -> tuple[str, str, str]:
    """counts[m-1]: futures that pay for themselves in month m; none: futures that do not within the horizon."""
    story = C.STORY_BARS.format(none=T.share(none / runs if runs else 0.0), months=months)
    if sum(counts):
        story += C.STORY_BARS_MODE.format(month=int(np.argmax(counts)) + 1)
    return _guide("timing_bars", story=story, runs=f"{runs:,}", months=months)


def levers_depth(swings: list[dict]) -> tuple[str, str, str]:
    a, b = swings[0], swings[1]
    return _guide("levers_depth", a=a["label"], b=b["label"].lower(), swing=a["text"])


def levers_chart(sens: pd.DataFrame) -> tuple[str, str, str]:
    """sens sorted with the biggest swing first."""
    r = sens.iloc[0]
    up = r["median_cum_net_T_high"] > r["median_cum_net_T_low"]
    better = r["median_cum_net_T_high"] if up else r["median_cum_net_T_low"]
    phrase = f"{C.RAISE if up else C.LOWER} {C.LEVER.get(r['input'], r['input']).lower()}"
    return _guide("levers_chart", phrase=phrase[0].upper() + phrase[1:], base=T.money(float(r["base_median_cum_net_T"])),
                  better=T.money(float(better)))


def company_balance(cards: dict, horizon: int, end: float) -> tuple[str, str, str]:
    pays = math.isfinite(cards["p50"]) and cards["prob"] >= 0.5
    story = (C.STORY_COMPANY_PAYS.format(month=int(round(cards["p50"])), end=T.money(end)) if pays
             else C.STORY_COMPANY_NOT.format(months=horizon, end=T.money(end)))
    return _guide("company_balance", story=story)


# ---------------------------------------------------------------- forecast pages
def data_history(name: str, v: dict, grain: str) -> tuple[str, str, str]:
    one, many = C.GRAIN_WORD.get(grain, ("step", "steps"))
    return _guide("data_history", n=f"{v['n']:,}", grains=many, direction=C.DIRECTION[v["direction"]],
                  trend=C.ADJ[LF.strength_word(v["trend"])])


def _place(label: str, grain: str, dated: bool) -> str:
    if dated:
        return label
    return f"{C.AXIS_STEP.get(grain, '').lower()} {label}"


def data_pattern(v: dict, grain: str) -> tuple[str, str, str]:
    vals, labels = np.asarray(v["pattern"]["values"], float), v["pattern"]["labels"]
    hi, lo = int(np.argmax(vals)), int(np.argmin(vals))
    slot = {"hour": ("hour of the day", "hours"), "day": ("day of the week", "days"), "month": ("month", "months"),
            "quarter": ("quarter", "quarters")}.get(grain, ("place in the cycle", "places"))
    return _guide("data_pattern", slot=slot[0], slots=slot[1], hi_label=_place(labels[hi], grain, v["dated"]),
                  lo_label=_place(labels[lo], grain, v["dated"]),
                  gap=LF.pct(1 - vals[lo] / vals[hi]) if vals[hi] else "0%",
                  strength=C.ADJ[LF.strength_word(v["pattern_strength"])])


def range_width(expected: float, low: float, high: float) -> tuple[str, float]:
    """('narrow' | 'moderate' | 'wide', half-width as a share of the expected value)."""
    spread = (high - low) / 2 / abs(expected) if expected else float("inf")
    return ("narrow" if spread < 0.05 else "moderate" if spread < 0.25 else "wide" if spread <= 1 else "very wide"), spread


def forecast(name: str, v: dict, last_value: float) -> tuple[str, str, str]:
    one, many = C.GRAIN_WORD.get(v["grain"], ("step", "steps"))
    exp, lo, hi = v["chart"]["expected"][-1], v["chart"]["low"][-1], v["chart"]["high"][-1]
    change = exp / last_value - 1 if last_value else float("nan")
    width, spread = range_width(exp, lo, hi)
    words = C.DIRECTION_WORDS[_direction(change)].format(change=LF.pct(abs(change)))
    spread_text = C.SPREAD["over"] if spread > 1 else C.SPREAD["share"].format(pct=LF.pct(spread))
    return _guide("forecast", name=C.SERIES[name][0], direction_words=words, n=v["n"], grains=one if v["n"] == 1 else many,
                  width=C.WIDTH[width], spread=spread_text, feeds=C.FEEDS.get(name, C.FEEDS["other"]))


def past(rv: dict) -> tuple[str, str, str]:
    one, many = C.GRAIN_WORD.get(rv["grain"], ("step", "steps"))
    ch = rv["chart"]
    act = np.asarray(ch["real_y"][ch["n_pre"]:], float)
    pred = np.asarray(ch["pred_y"], float)
    low_share = float((act > pred).mean()) if len(act) else 0.5
    bias = "low" if low_share >= 2 / 3 else "high" if low_share <= 1 / 3 else "mixed"
    return _guide("past", n=rv["n"], grains=one if rv["n"] == 1 else many, inside=rv["first_inside"], bias=C.BIAS[bias])


def ranking(rv: dict) -> tuple[str, str, str]:
    size = 1 - rv["vs_reference"] if math.isfinite(rv["vs_reference"]) else float("nan")
    close = C.CLOSE_NOTE.format(k=rv["close"]) if rv["close"] >= 3 else ""
    return _guide("ranking", size=LF.size_words(size), close=close)
