"""Pure helpers for the forecast views (no Streamlit calls), so the tests can check them directly.

The saved Phase 3 forecast tables hold, per series, a central line (`sample_id` -1) and 200 simulated futures
(`sample_id` 0 and up). The "likely range" shown on screen is where eight in ten of those futures land: the
10th to 90th percentile of the simulated values at each step. Each series has exactly one saved forecast length;
the "show the next ..." choices only ever cut that saved forecast shorter. Past checks come from Phase 2
(`holdout.csv`, `leaderboard.csv`, `chosen_models.csv`) and Phase 3 (`interval_check.csv`). Nothing here changes,
refits or extends a forecast.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dashboard.ui import copy as C
from dashboard.core import currency as CUR

LOW_Q, HIGH_Q = 0.10, 0.90
HOSTING = ("ppi_hosting_monthly", "ppi_hosting")  # (saved forecast name, column in data/processed)
HISTORY_MONTHS = 36
SERIES = tuple(s for group in C.SERIES_GROUPS.values() for s in group)  # page order
SHORTER = {"hour": (24, 72), "day": (7,), "month": (3, 6), "quarter": (4,)}  # cuts offered below the saved length


# ---------------------------------------------------------------- saved forecast and likely range
def expected_and_range(fc: pd.DataFrame, low: float = LOW_Q, high: float = HIGH_Q) -> pd.DataFrame:
    """One row per step ahead: period_index, calendar_month (may be empty), expected, low, high."""
    central = fc[fc["sample_id"] == -1].sort_values("period_index")
    sims = fc[fc["sample_id"] >= 0]
    if central.empty or sims.empty:
        raise ValueError("saved forecast has no central line or no simulated futures")
    q = sims.groupby("period_index")["value"].quantile([low, high]).unstack()
    out = pd.DataFrame({"period_index": central["period_index"].to_numpy(),
                        "calendar_month": central["calendar_month"].to_numpy(),
                        "expected": central["value"].to_numpy()})
    out["low"] = out["period_index"].map(q[low]).to_numpy()
    out["high"] = out["period_index"].map(q[high]).to_numpy()
    return out.reset_index(drop=True)


def grain(fc: pd.DataFrame) -> str:
    """'hour', 'day', 'month' or 'quarter', as saved with the forecast."""
    return str(fc["grain"].iloc[0])


def saved_horizon(fc: pd.DataFrame) -> int:
    """How many steps ahead the saved forecast goes (the only length that exists)."""
    return int(fc["period_index"].max())


def horizon_options(grain_: str, saved: int) -> list[int]:
    """'Show the next ...' lengths: a few shorter cuts of the saved forecast, then the saved length itself."""
    return [n for n in SHORTER.get(grain_, ()) if n < saved] + [int(saved)]


def cut(rng: pd.DataFrame, n: int) -> pd.DataFrame:
    """The first n steps of the expected line and range; never more than was saved."""
    if not 1 <= int(n) <= len(rng):
        raise ValueError(f"asked for {n} steps; the saved forecast has {len(rng)}")
    return rng.head(int(n)).reset_index(drop=True)


def future_x(last_x, rng: pd.DataFrame, grain_: str) -> list:
    """Positions of the future steps on the chart: calendar months/quarters as saved; days and hours counted on from
    the last real point (the saved calendar_month of a daily series holds only the month, not the day)."""
    steps = rng["period_index"].astype(int).tolist()
    if grain_ in ("month", "quarter"):
        return list(pd.to_datetime(rng["calendar_month"]))
    if isinstance(last_x, (pd.Timestamp, np.datetime64)) or hasattr(last_x, "year"):
        unit = pd.Timedelta(hours=1) if grain_ == "hour" else pd.Timedelta(days=1)
        return [pd.Timestamp(last_x) + k * unit for k in steps]
    return [int(last_x) + k for k in steps]


def has_dates(x) -> bool:
    return not isinstance(x, (int, np.integer))


def step_label(x, grain_: str) -> str:
    """'Day 12' / 'Hour 2,089' for sources without dates (counted from 1), else '3 Mar 2024', 'Oct 2026', 'Q3 2026'."""
    if not has_dates(x):
        return C.STEP.get(grain_, "{n}").format(n=CUR.group(int(x) + 1))
    t = pd.Timestamp(x)
    if grain_ == "quarter":
        return f"Q{t.quarter} {t.year}"
    if grain_ == "month":
        return t.strftime("%b %Y")
    if grain_ == "hour":
        return t.strftime("%d %b %Y, %H:00").lstrip("0")
    return t.strftime("%d %b %Y").lstrip("0")


# ---------------------------------------------------------------- the real series
def series_facts(hist: pd.DataFrame, name: str, grain_: str, anomalies: pd.DataFrame | None = None) -> dict:
    """Plain facts about a series: first and last point, how many points, unusual points flagged in Phase 1."""
    unusual = 0 if anomalies is None else len(unusual_points(anomalies, name))
    return {"start": step_label(hist["x"].iloc[0], grain_), "end": step_label(hist["x"].iloc[-1], grain_),
            "count": int(len(hist)), "unusual": unusual, "dated": has_dates(hist["x"].iloc[0]),
            "gaps": int(hist["value"].isna().sum())}


def amount(x: float, unit: str = "") -> str:
    """A count in the Indian style without a currency sign: 950, 12,345, 23.1 lakh, 3.45 crore; levels with one
    decimal ('points')."""
    if x is None or not math.isfinite(float(x)):
        return "Not available"
    if unit == "points":
        return f"{float(x):.1f}"
    a, sign = abs(float(x)), "-" if x < 0 else ""
    if round(a) < CUR.LAKH:
        return sign + CUR.group(round(a))
    if round(a / CUR.LAKH, 1) < 100:
        return f"{sign}{a / CUR.LAKH:.1f} lakh"
    cr = f"{a / CUR.CRORE:.2f}".rstrip("0").rstrip(".")
    return f"{sign}{cr} crore"


# ---------------------------------------------------------------- how close past predictions came
def chosen_approach(chosen: pd.DataFrame, name: str) -> str:
    r = chosen[chosen["driver"] == name]
    if r.empty:
        raise KeyError(name)
    return str(r["chosen_model"].iloc[0])


def approach_label(key: str, grain_: str) -> str:
    """Plain name of an approach (engine names never reach the screen)."""
    if grain_ in C.APPROACH_BY_GRAIN.get(key, {}):
        return C.APPROACH_BY_GRAIN[key][grain_]
    slot, cycle = C.CYCLE.get(grain_, ("period", "cycle"))
    return C.APPROACH.get(key, key).format(slot=slot, cycle=cycle)


def past_check(holdout: pd.DataFrame, name: str, approach: str) -> pd.DataFrame:
    """The final held-back stretch: what was predicted, what really happened and the range at the time."""
    h = holdout[(holdout["driver"] == name) & (holdout["model"] == approach)].sort_values("step_ahead")
    if h.empty:
        raise KeyError(f"{name}:{approach}")
    out = pd.DataFrame({"step": h["step_ahead"].astype(int).to_numpy(), "time": h["time"].to_numpy(),
                        "actual": h["actual"].to_numpy(float), "predicted": h["forecast"].to_numpy(float),
                        "low": h["lo80"].to_numpy(float), "high": h["hi80"].to_numpy(float)})
    out["inside"] = (out["actual"] >= out["low"]) & (out["actual"] <= out["high"])
    return out


def average_miss(pc: pd.DataFrame) -> float:
    return float((pc["actual"] - pc["predicted"]).abs().mean())


def range_hits(interval_check: pd.DataFrame, name: str) -> tuple[int, int]:
    """(points inside the likely range, points checked) on the held-back stretch after Phase 3 set the range."""
    r = interval_check[(interval_check["driver"] == name) & (interval_check["segment"] == "all")]
    if r.empty:
        raise KeyError(name)
    n = int(r["n_holdout_points"].iloc[0])
    return int(round(float(r["coverage_80_after"].iloc[0]) * n)), n


def ranking(leaderboard: pd.DataFrame, name: str, chosen: str, grain_: str) -> pd.DataFrame:
    """Approaches that ran for this series, closest first, by average miss over the earlier checks (cv_mae), with
    the simple reference marked and how much smaller each miss is than the reference's."""
    lb = leaderboard[(leaderboard["driver"] == name) & (leaderboard["status"] == "ok")].copy()
    lb = lb[np.isfinite(lb["cv_mae"].astype(float))].sort_values(["cv_mae", "model"]).reset_index(drop=True)
    ref = lb.loc[lb["model"] == C.REFERENCE_APPROACH, "cv_mae"]
    ref_mae = float(ref.iloc[0]) if len(ref) else float("nan")
    return pd.DataFrame({"approach": lb["model"], "label": [approach_label(m, grain_) for m in lb["model"]],
                         "average_miss": lb["cv_mae"].astype(float),
                         "chosen": lb["model"] == chosen, "reference": lb["model"] == C.REFERENCE_APPROACH,
                         "smaller_than_reference": 1 - lb["cv_mae"].astype(float) / ref_mae})


# ---------------------------------------------------------------- What we expect next (step C)
HISTORY_WINDOW = {"hour": 336, "day": 56, "month": 36, "quarter": 24}  # recent real points shown before the future


def change_text(c: float) -> str:
    if not math.isfinite(c) or abs(c) < 0.005:
        return C.SAME
    return f"{c:+.1%}" if abs(c) < 0.1 else f"{c:+.0%}"


def _plot_x(x, dated: bool):
    return pd.Timestamp(x) if dated else int(x) + 1  # step numbers are shown counted from 1


def calibrated(rng: pd.DataFrame, cal: dict | None) -> pd.DataFrame:
    """Swap the saved range for the calibrated (conformal) 80% range and add the 50% range, when available."""
    if not cal or cal.get("fan") is None:
        return rng
    f = cal["fan"].set_index("period_index")
    out = rng.copy()
    idx = out["period_index"] if "period_index" in out else pd.Series(range(1, len(out) + 1))
    for col, src in (("low", "lo80"), ("high", "hi80"), ("low50", "lo50"), ("high50", "hi50")):
        out[col] = f[src].reindex(idx.to_numpy()).to_numpy()
    return out


def coverage_note(cal: dict | None) -> tuple[str, bool] | None:
    """(sentence, warn) on how often the calibrated range held in the rolling check, or None."""
    if not cal or cal.get("coverage") is None:
        return None
    cov, pts = float(cal["coverage"]), int(cal["points"])
    warn = not (0.7 <= cov <= 0.9)
    return C.RANGE_CAL.format(share=pct(cov), pts=pts), warn


def forecast_view(name: str, n: int, hist: pd.DataFrame, fc: pd.DataFrame,
                  interval_check: pd.DataFrame | None = None, cal: dict | None = None) -> dict:
    """Everything the 'What we expect next' page shows for one series and one length, from the saved files.
    `cal` (from artifacts/): calibrated ranges ('fan') and their rolling-check coverage ('coverage', 'points')."""
    g, unit = grain(fc), C.SERIES[name][2]
    rng = calibrated(cut(expected_and_range(fc), n), cal)
    last_x, last_y = hist["x"].iloc[-1], float(hist["value"].iloc[-1])
    dated = has_dates(last_x)
    fx = future_x(last_x, rng, g)
    h = hist.tail(HISTORY_WINDOW.get(g, len(hist)))
    labels_h = [step_label(x, g) for x in h["x"]]
    labels_f = [step_label(x, g) for x in fx]
    exp, lo, hi = (rng[c].astype(float).tolist() for c in ("expected", "low", "high"))
    fc_tips = [f"{lab}: " + C.HOVER_EXPECT.format(value=amount(e, unit), low=amount(a, unit), high=amount(b, unit))
               for lab, e, a, b in zip(labels_f, exp, lo, hi)]
    hits = range_hits(interval_check, name) if interval_check is not None else None
    flag = None
    if interval_check is not None:
        r = interval_check[(interval_check["driver"] == name) & (interval_check["segment"] == "all")]
        flag = bool(r["flag"].iloc[0]) if len(r) else None
    cov = coverage_note(cal)
    if cov is not None:  # the calibrated range replaces the old one, so its own check replaces the old check
        hits, flag = None, cov[1]
    digits = 2 if unit == "points" else 0
    table = pd.DataFrame({C.EXPECT_COLS["when"]: labels_f,
                          C.EXPECT_COLS["expected"]: np.round(exp, digits), C.EXPECT_COLS["low"]: np.round(lo, digits),
                          C.EXPECT_COLS["high"]: np.round(hi, digits)})
    return {
        "grain": g, "unit": unit, "dated": dated, "n": int(n),
        "chart": {"hist_x": [_plot_x(x, dated) for x in h["x"]], "hist_y": h["value"].astype(float).tolist(),
                  "fc_x": [_plot_x(x, dated) for x in fx], "expected": exp, "low": lo, "high": hi, "unit": unit,
                  "y_title": C.SERIES[name][3], "x_title": None if dated else C.AXIS_STEP.get(g),
                  "divider": C.LAST_REAL, "hist_tips": [f"{lab}: {amount(y, unit)}" for lab, y in zip(labels_h, h["value"])],
                  "fc_tips": fc_tips, "dated": dated, "grain": g,
                  "low50": rng["low50"].astype(float).tolist() if "low50" in rng else None,
                  "high50": rng["high50"].astype(float).tolist() if "high50" in rng else None,
                  "tickformat": {"quarter": "%Y", "month": "%b %Y", "day": "%d %b", "hour": "%d %b %H:00"}.get(g)},
        "headline": C.FORECAST_HEADLINE.format(end=labels_f[-1], value=amount(exp[-1], unit), unit=unit),
        "range": C.FORECAST_RANGE.format(low=amount(lo[-1], unit), high=amount(hi[-1], unit)),
        "change": C.FORECAST_CHANGE.format(change=change_text(exp[-1] / last_y - 1 if last_y else float("nan")),
                                           last=amount(last_y, unit), when=step_label(last_x, g)),
        "hits": hits, "flag": flag, "table": table, "coverage": cov,
    }


# ---------------------------------------------------------------- How reliable it is (step D)
CLOSE_WITHIN = 0.05  # approaches whose average miss is within 5% of the closest count as 'almost the same'


def size_words(r: float) -> str:
    """A ratio of two sizes in words: 0.33 -> 'a third', 0.5 -> 'half'."""
    if r is None or not math.isfinite(float(r)):
        return "about the same as"
    for limit, words in C.SIZE_WORDS:
        if r <= limit:
            return words
    return "larger than"


def pct(x: float) -> str:
    """A share as shown on screen: one decimal under 10%, whole above."""
    if x is None or not math.isfinite(float(x)):
        return "Not available"
    return f"{x:.1%}" if abs(x) < 0.1 else f"{x:.0%}"


def reliability_view(name: str, hist: pd.DataFrame, grain_: str, chosen: pd.DataFrame, holdout: pd.DataFrame,
                     interval_check: pd.DataFrame | None, leaderboard: pd.DataFrame, cal: dict | None = None) -> dict:
    """Everything the 'How reliable it is' page shows for one series, from the saved Phase 2 and 3 tables."""
    unit = C.SERIES[name][2]
    one, many = C.GRAIN_WORD.get(grain_, ("step", "steps"))
    ap = chosen_approach(chosen, name)
    pc = past_check(holdout, name, ap)
    n = len(pc)
    miss, level = average_miss(pc), float(pc["actual"].mean())
    first_inside = int(pc["inside"].sum())
    hits = range_hits(interval_check, name) if interval_check is not None else None
    flag = None
    if interval_check is not None:
        r = interval_check[(interval_check["driver"] == name) & (interval_check["segment"] == "all")]
        flag = bool(r["flag"].iloc[0]) if len(r) else None
    cov = coverage_note(cal)
    if cov is not None:
        flag = cov[1]
    rk = ranking(leaderboard, name, ap, grain_)
    mine = rk[rk["chosen"]].iloc[0]
    ref = rk[rk["reference"]]
    vs = float(mine["smaller_than_reference"]) if len(ref) else float("nan")
    best = float(rk["average_miss"].iloc[0])
    close = int((rk["average_miss"] <= best * (1 + CLOSE_WITHIN)).sum())
    notes = []
    if close >= 3:
        notes.append(C.RANK_CLOSE.format(k=close))
    if not bool(rk["chosen"].iloc[0]):
        notes.append(C.RANK_NOT_FIRST.format(chosen=mine["label"], gap=pct(float(mine["average_miss"]) / best - 1)))
    lb = leaderboard[leaderboard["driver"] == name]
    skipped = int((lb["status"] != "ok").sum())
    if skipped:
        notes.append(C.RANK_SKIPPED.format(k=skipped))

    dated = has_dates(hist["x"].iloc[0])
    to_x = (lambda t: pd.Timestamp(t)) if dated else (lambda t: int(t))
    times = [to_x(t) for t in pc["time"]]
    pre = hist[hist["x"] < times[0]].tail(max(2 * n, 12))
    plot = (lambda x: pd.Timestamp(x)) if dated else (lambda x: int(x) + 1)
    real_x = [plot(x) for x in pre["x"]] + [plot(t) for t in times]
    real_y = pre["value"].astype(float).tolist() + pc["actual"].tolist()
    labels = [step_label(t, grain_) for t in times]
    tips_real = [f"{step_label(x, grain_)}: {amount(y, unit)}" for x, y in zip(pre["x"], pre["value"])] + \
                [C.HOVER_PAST.format(when=lab, predicted=amount(p, unit), actual=amount(a, unit))
                 for lab, p, a in zip(labels, pc["predicted"], pc["actual"])]
    ref_label = ref["label"].iloc[0] if len(ref) else ""
    vs_value = (C.VALUE_SMALLER if vs >= 0 else C.VALUE_LARGER).format(share=pct(abs(vs)))
    return {
        "approach": ap, "approach_label": mine["label"], "grain": grain_, "n": n, "miss": miss, "level": level, "unit": unit,
        "first_inside": first_inside, "hits": None if cov is not None else hits, "flag": flag, "coverage": cov, "vs_reference": vs, "close": close,
        "skipped": skipped, "ranking": rk, "notes": notes, "dated": dated,
        "verdict": C.RELIABLE_VERDICT.format(n=n, grains=one if n == 1 else many, miss=amount(miss, unit), unit=unit,
                                             share=pct(miss / level if level else float("nan"))),
        "tiles": [
            (C.TILE_MISS[0], f"{amount(miss, unit)} {unit}",
             C.TILE_MISS[1].format(n=n, grains=one if n == 1 else many, level=f"{amount(level, unit)} {unit}")),
            (C.TILE_INSIDE[0], pct(float(cal["coverage"])), C.TILE_INSIDE_CAL.format(pts=int(cal["points"])))
            if cov is not None else
            (C.TILE_INSIDE[0], C.VALUE_OF.format(inside=hits[0], n=hits[1]) if hits else C.VALUE_OF.format(inside=first_inside, n=n),
             C.TILE_INSIDE[1].format(first=first_inside, n=n)),
            (C.TILE_VS[0], vs_value, C.TILE_VS[1].format(size=size_words(1 - vs), reference=ref_label)),
        ],
        "chart": {"real_x": real_x, "real_y": real_y, "real_tips": tips_real, "n_pre": len(pre),
                  "pred_x": [plot(t) for t in times], "pred_y": pc["predicted"].tolist(),
                  "low": pc["low"].tolist(), "high": pc["high"].tolist(), "inside": pc["inside"].tolist(),
                  "unit": unit, "y_title": C.SERIES[name][3], "x_title": None if dated else C.AXIS_STEP.get(grain_),
                  "dated": dated, "tickformat": {"quarter": "%Y", "month": "%b %Y", "day": "%d %b", "hour": "%d %b %H:00"}.get(grain_)},
    }


# ---------------------------------------------------------------- The big picture strip (step F)
STRIP_SERIES = ("eci_wages_quarterly", "ppi_hosting_monthly")  # the cost trends shown on The big picture
USAGE_SERIES = ("burst_tokens_total_daily", "burst_tokens_api_daily", "burst_tokens_chat_daily", "burst_requests_hourly",
                "wildchat_conversations_daily")


def expected_change(hist: pd.DataFrame, fc: pd.DataFrame) -> tuple[float, str, str]:
    """(change from the latest real value to the end of the saved forecast, end label, label of the latest value)."""
    g = grain(fc)
    rng = expected_and_range(fc)
    last_x, last_y = hist["x"].iloc[-1], float(hist["value"].iloc[-1])
    end = future_x(last_x, rng, g)[-1]
    return float(rng["expected"].iloc[-1]) / last_y - 1, step_label(end, g), step_label(last_x, g)


def miss_share(holdout: pd.DataFrame, chosen: pd.DataFrame, name: str) -> float:
    """Average miss on the held-back stretch as a share of the typical level there."""
    pc = past_check(holdout, name, chosen_approach(chosen, name))
    return average_miss(pc) / float(pc["actual"].mean())


# ---------------------------------------------------------------- The data we used (step E)
SEASON = {"hour": 24, "day": 7, "month": 12, "quarter": 4}
WINDOW_KIND = {"eci_wages_quarterly": "full", "ppi_hosting_monthly": "full", "wildchat_conversations_daily": "wildchat",
               "burst_tokens_total_daily": "burst", "burst_tokens_api_daily": "burst",
               "burst_tokens_chat_daily": "burst", "burst_requests_hourly": "burst"}
TOP_UNUSUAL = 10


def unusual_points(anomalies: pd.DataFrame, name: str) -> pd.DataFrame:
    """Values Phase 1 flagged as unusual for this series. Rows without a value are notes about a check (for example
    the day-77 check of AI usage per day), not flagged values, and are left out."""
    a = anomalies[(anomalies["driver"] == name) & anomalies["value"].notna()]
    return a.reset_index(drop=True)


def strength_word(x) -> str:
    """Plain word for a 0-to-1 strength from Phase 1: strong (0.6 and up), some (0.3 and up), little."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return C.STRENGTH["little"]
    if not math.isfinite(v):
        return C.STRENGTH["little"]
    return C.STRENGTH["strong"] if v >= 0.6 else C.STRENGTH["some"] if v >= 0.3 else C.STRENGTH["little"]


def position(x, grain_: str) -> tuple[int, str]:
    """(sort key, label) of a point's place in its repeating cycle: month of year, quarter, day of week, hour of day.
    Sources without dates count from their first point, so days and hours are numbered, not named."""
    if has_dates(x):
        t = pd.Timestamp(x)
        if grain_ == "month":
            return t.month, t.strftime("%b")
        if grain_ == "quarter":
            return t.quarter, f"Q{t.quarter}"
        if grain_ == "day":
            return t.weekday(), C.WEEKDAYS[t.weekday()]
        return t.hour, f"{t.hour:02d}:00"
    k = int(x) % SEASON.get(grain_, 1)
    return k, C.POSITION.get(grain_, "{k}").format(k=k + 1)


def data_view(name: str, hist: pd.DataFrame, grain_: str, source_n: int, anomalies: pd.DataFrame | None,
              decomposition: pd.DataFrame | None) -> dict:
    """Everything the 'The data we used' page shows for one series, from the real data and the Phase 1 tables."""
    unit = C.SERIES[name][2]
    one, many = C.GRAIN_WORD.get(grain_, ("step", "steps"))
    n = len(hist)
    dated = has_dates(hist["x"].iloc[0])
    un = unusual_points(anomalies, name) if anomalies is not None else pd.DataFrame(columns=["time", "value", "robust_z"])
    missing = int(hist["value"].isna().sum())
    facts = series_facts(hist, name, grain_, anomalies)
    kind = WINDOW_KIND.get(name, "full")
    window = C.WINDOW_NOTE[kind].format(n=CUR.group(n), source=CUR.group(source_n), grains=many)
    known = (hist["known_outage"].astype(bool) if "known_outage" in hist else pd.Series(False, index=hist.index))
    outage = [step_label(x, grain_) for x in hist.loc[known, "x"]]
    if grain_ == "hour" and outage:  # an outage day marks all its hours; name the day once
        outage = [C.STEP["day"].format(n=int(hist.loc[known, "x"].iloc[0]) // 24 + 1)]
    # plain summary: change between the first and the last full cycle, Phase 1 strengths as words
    s = SEASON.get(grain_, 1)
    first, last = float(hist["value"].head(s).mean()), float(hist["value"].tail(s).mean())
    change = last / first - 1 if first else float("nan")
    direction = "up" if change > 0.02 else "down" if change < -0.02 else "flat"
    trend = pattern = float("nan")
    if decomposition is not None:
        r = decomposition[decomposition["driver"] == name]
        if len(r):
            trend, pattern = r["trend_strength"].iloc[0], r["seasonal_strength"].iloc[0]
    summary = C.PLAIN_SUMMARY.format(s=s, grains=many, first=amount(first, unit), last=amount(last, unit), unit=unit,
                                     direction=C.DIRECTION[direction],
                                     trend=strength_word(trend), cycle=C.CYCLE_NAME.get(grain_, ""),
                                     pattern=strength_word(pattern))
    # chart: every real value used, unusual points and the known outage marked
    to_x = (lambda x: pd.Timestamp(x)) if dated else (lambda x: int(x) + 1)
    vals = hist.set_index("x")["value"]
    times = [pd.Timestamp(t) if dated else int(float(t)) for t in un["time"]]
    marks = [(to_x(t), float(vals.get(t, np.nan))) for t in times]
    out_rows = hist[known]
    # repeating pattern: average of the real values in each place of the cycle
    pos = [position(x, grain_) for x in hist["x"]]
    pat = (pd.DataFrame({"k": [p[0] for p in pos], "label": [p[1] for p in pos], "value": hist["value"].to_numpy()})
           .groupby(["k", "label"], as_index=False)["value"].mean().sort_values("k"))
    # unusual table: most unusual first
    if len(un):
        u = un.assign(t=times, z=un["robust_z"].astype(float)).reindex(un["robust_z"].abs().sort_values(ascending=False).index)
        table = pd.DataFrame({C.UNUSUAL_COLS["when"]: [step_label(t, grain_) for t in u["t"]],
                              C.UNUSUAL_COLS["value"]: [f"{amount(v, unit)} {unit}" for v in u["value"]],
                              C.UNUSUAL_COLS["how"]: [C.UNUSUAL_HOW["very" if abs(z) >= 5 else "some"] for z in u["z"]],
                              C.UNUSUAL_COLS["side"]: [C.UNUSUAL_SIDE["high" if z > 0 else "low"] for z in u["z"]]})
    else:
        table = pd.DataFrame(columns=list(C.UNUSUAL_COLS.values()))
    download = pd.DataFrame({C.DATA_COLS["when"]: [step_label(x, grain_) for x in hist["x"]],
                             C.DATA_COLS["value"]: hist["value"].to_numpy()})
    t = C.DATA_TILES
    return {
        "unit": unit, "dated": dated, "n": n, "facts": facts, "window": window,
        "outage": C.OUTAGE_NOTE.format(when=outage[0]) if outage else "",
        "summary": summary, "change": change, "direction": direction, "trend": trend, "pattern_strength": pattern,
        "tiles": [(t["span"][0], t["span"][1].format(start=facts["start"], end=facts["end"]), C.DATA_TILE_MEANING["span"]),
                  (t["count"][0], t["count"][1].format(n=CUR.group(n), grains=one if n == 1 else many),
                   C.DATA_TILE_MEANING["count"].format(grain=one)),
                  (t["unusual"][0], t["unusual"][1].format(k=CUR.group(len(un))) if len(un) else C.NONE,
                   C.DATA_TILE_MEANING["unusual"]),
                  (t["missing"][0], CUR.group(missing) if missing else C.NONE, C.DATA_TILE_MEANING["missing"])],
        "chart": {"x": [to_x(x) for x in hist["x"]], "y": hist["value"].astype(float).tolist(),
                  "tips": [f"{step_label(x, grain_)}: {amount(y, unit)}" for x, y in zip(hist["x"], hist["value"])],
                  "unusual_x": [m[0] for m in marks], "unusual_y": [m[1] for m in marks],
                  "unusual_tips": [f"{step_label(tt, grain_)}: {amount(v, unit)}" for tt, (_, v) in zip(times, marks)],
                  "outage_x": [to_x(x) for x in out_rows["x"]], "outage_y": out_rows["value"].astype(float).tolist(),
                  "unit": unit, "y_title": C.SERIES[name][3], "x_title": None if dated else C.AXIS_STEP.get(grain_),
                  "dated": dated, "grain": grain_},
        "pattern": {"labels": pat["label"].tolist(), "values": pat["value"].astype(float).tolist(),
                    "title": C.PATTERN_TITLE.get(grain_, ""), "unit": unit,
                    "x_title": None if dated else C.POSITION_AXIS.get(grain_),
                    "note": "" if dated else C.PATTERN_NOTE_UNDATED},
        "unusual": table, "unusual_n": len(un), "download": download,
    }


# ---------------------------------------------------------------- Welcome chart (step A)
def hosting_hero(history: pd.DataFrame, fc: pd.DataFrame, months: int = HISTORY_MONTHS, cal: dict | None = None) -> dict:
    """Data of the Welcome chart: the last `months` real values of hosting prices and the saved forecast."""
    col = HOSTING[1]
    h = history.dropna(subset=[col]).copy()
    h["date"] = pd.to_datetime(h["date"])
    h = h.sort_values("date").tail(months)
    f = calibrated(expected_and_range(fc), cal)
    f["date"] = pd.to_datetime(f["calendar_month"])
    return {"hist_dates": list(h["date"]), "hist_values": [float(v) for v in h[col]],
            "fc_dates": list(f["date"]), "expected": [float(v) for v in f["expected"]],
            "low": [float(v) for v in f["low"]], "high": [float(v) for v in f["high"]]}


def level(x: float) -> str:
    """A price level as shown on screen: one decimal."""
    return f"{float(x):.1f}"


def month_year(d) -> str:
    return pd.Timestamp(d).strftime("%b %Y")
