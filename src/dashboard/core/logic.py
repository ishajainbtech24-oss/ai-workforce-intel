"""Pure helpers behind the pages (no Streamlit calls), so the tests can check them directly.

- formatted KPI values for the Overview cards (from the saved tables),
- the three findings sentences and the levers takeaway, filled in from the real numbers,
- turning the 'Your company' form into engine inputs, with friendly messages instead of errors.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dashboard.ui import copy as C
from dashboard.core import currency as CUR
from dashboard.core import data as D
from dashboard.ui import theme as T

PCT_FIELDS = ("adoption_target", "realisation_rate")
# typed and shown in rupees on "Try your own numbers"; the engine takes dollars
MONEY_FIELDS = ("fixed_enablement_cost_per_month", "base_hourly_wage_staff", "base_hourly_wage_engineer",
                "fixed_token_price_per_mtok", "base_monthly_hosting_cost")


def words(name: str) -> str:
    """On-screen text that names whose figures these are: the example wording, the 'your figures' wording
    (copy.YOURS) while the visitor's own results are showing, or the preset wording (copy.PRESET_WORDS)."""
    if D.yours() is not None and name in C.YOURS:
        return C.YOURS[name]
    p = D.preset()
    if p in C.PRESET_WORDS and name in C.PRESET_WORDS[p]:
        return C.PRESET_WORDS[p][name]
    return getattr(C, name)


def sk(scenario: str | None = None, k: float | None = None) -> tuple[str, float]:
    """The outlook and caution level to show: as given, else the scenario bar's (expected, standard outside a run)."""
    from dashboard.core import state
    return scenario or state.get("outlook"), float(state.get("caution") if k is None else k)


def overview_cards(scenario: str | None = None, k: float | None = None) -> dict[str, str]:
    """Formatted values of the four Overview cards."""
    scenario, k = sk(scenario, k)
    v = D.overview_kpis(scenario, k)
    return {"cost": T.money(v["cost"]), "benefit": T.money(v["benefit"]), "balance": T.money(v["balance"]),
            "payback": T.month(v["payback"], v["T"])}


def year_end_balances(k: float = 1.0) -> list[dict]:
    """Values for the 3D 'money flow' columns: typical year-end running balance of each outlook."""
    out = []
    for sc in D.outlooks():
        v = float(D.row("totals_summary", sc, k)["cum_net_T_p50"])
        out.append({"key": sc, "label": C.OUTLOOK[sc], "value": v, "text": T.money(v)})
    return out


def cost_slices(shares: pd.DataFrame) -> list[dict]:
    """Values for the 3D donut: one slice per cost type (typical total over the year and its share)."""
    total = float(shares["p50_total"].sum())
    return [{"key": r.line, "label": C.LINE[r.line], "tag": C.TYPE_TAG[r.type], "value": float(r.p50_total),
             "text": T.money(float(r.p50_total)), "share": float(r.p50_total) / total if total else 0.0,
             "share_text": T.share(float(r.p50_total) / total if total else 0.0)}
            for r in shares.itertuples()]


def lever_swings(n: int = 6) -> list[dict]:
    """Values for the depth bars: the n choices with the widest gap between 20% lower and 20% higher."""
    s = D.sensitivity().sort_values("swing_cum_net_T", ascending=False).head(n)
    return [{"key": r.input, "label": C.LEVER.get(r.input, r.input), "value": float(r.swing_cum_net_T),
             "text": T.money(float(r.swing_cum_net_T))} for r in s.itertuples()]


def card_status(scenario: str | None = None, k: float | None = None) -> dict[str, tuple[str, str]]:
    """Status chip of each Overview card, chosen from the real results: (tone, plain words)."""
    scenario, k = sk(scenario, k)
    v = D.overview_kpis(scenario, k)
    b = D.table("cost_breakdown")
    b = b[(b["scenario"] == scenario) & np.isclose(b["multiplier"], k)].set_index("line")
    people = float(b.loc[["enablement", "integration"], "p50_share_of_cost"].sum()) >= 0.5
    ok = v["balance"] >= 0
    pays = math.isfinite(v["payback"])
    return {"cost": ("neutral", C.CHIP["people"]) if people else ("neutral", C.CHIP["estimate"]),
            "benefit": ("neutral", C.CHIP["estimate"]),
            "balance": ("good", C.CHIP["good"]) if ok else ("attention", C.CHIP["attention"]),
            "payback": ("good", C.CHIP["good"]) if pays else ("attention", C.CHIP["attention"])}


def findings() -> list[str]:
    """Three key-finding sentences from cost_breakdown.csv and sensitivity.csv (expected outlook, standard)."""
    b = D.table("cost_breakdown")
    b = b[(b["scenario"] == "expected") & np.isclose(b["multiplier"], 1.0)].set_index("line")
    s = D.sensitivity().sort_values("swing_cum_net_T", ascending=False)
    first, second = (C.LEVER.get(x, x).lower() for x in s["input"].head(2))
    swing = float(s["swing_cum_net_T"].iloc[0]) / 2
    tech = float(b.loc[["hosting", "token_expenditure"], "p50_share_of_cost"].sum())
    return [C.FINDING_COST.format(share=T.share(b.loc["enablement", "p50_share_of_cost"])),
            C.FINDING_LEVERS.format(first=first, second=second, swing=T.money(swing)),
            C.FINDING_TECH.format(share=T.share(tech))]


def lever_phrases(n: int) -> list[str]:
    """'raising time saved per person' / 'lowering training hours per new user' for the top n levers."""
    s = D.sensitivity().sort_values("swing_cum_net_T", ascending=False).head(n)
    out = []
    for r in s.itertuples():
        up = r.median_cum_net_T_high > r.median_cum_net_T_low
        out.append(f"{C.RAISE if up else C.LOWER} {C.LEVER.get(r.input, r.input).lower()}")
    return out


def verdict(prob: float, p50: float, horizon: int) -> str:
    if prob > 0 and math.isfinite(p50):
        return C.VERDICT_YES.format(share=T.share(prob), months=horizon, month=int(round(p50)))
    return C.VERDICT_NO.format(months=horizon)


def to_inputs(base: dict, form: dict) -> tuple[dict | None, list[str]]:
    """Form values (shares in %, money in rupees) -> validated engine inputs (money in dollars), or None and
    friendly messages."""
    msgs = []
    if form.get("employees", 0) < 0:
        msgs.append(C.ERRORS["employees"])
    for f in PCT_FIELDS:
        if f in form and not 0 <= form[f] <= 100:
            msgs.append(C.ERRORS["share"])
            break
    if msgs:
        return None, msgs
    inp = dict(base)
    for k, v in form.items():
        inp[k] = v / 100.0 if k in PCT_FIELDS else CUR.to_usd(float(v)) if k in MONEY_FIELDS else v
    inp["adoption_target"] = max(inp["adoption_target"], inp["adoption_start"])
    for k in ("employees", "ramp_months", "horizon_months"):
        inp[k] = int(inp[k])
    from engine.inputs import InputError, validate
    try:
        return validate(inp), []
    except InputError as exc:
        detail = "; ".join(line.strip(" -") for line in str(exc).splitlines()[1:])
        for f, (label, _, _) in C.FIELDS.items():
            detail = detail.replace(f, label)
        return None, [C.ERRORS["generic"].format(detail=detail)]


def submit(base: dict, form: dict, scenario: str, runner) -> tuple[object | None, list[str]]:
    """Validate, then call `runner(inputs, scenario)` only if the inputs are fine."""
    inputs, msgs = to_inputs(base, form)
    if inputs is None:
        return None, msgs
    return runner(inputs, scenario), []


def live_cards(res) -> dict[str, str]:
    """Formatted KPI values of a live run (typical case = middle of the futures)."""
    be = res.break_even
    hit = np.isfinite(be)
    pays = float(np.median(be[hit])) if hit.mean() >= 0.5 else float("nan")
    return {"cost": T.money(float(np.median(res.total_cost.sum(axis=1)))),
            "benefit": T.money(float(np.median(res.value.sum(axis=1)))),
            "balance": T.money(float(np.median(res.cum_net_T))), "payback": T.month(pays, res.meta["T"]),
            "prob": float(hit.mean()), "p50": float(np.median(be[hit])) if hit.any() else float("nan")}


def live_shares(res) -> pd.DataFrame:
    import config_phase4 as P4
    rows = [{"line": ln, "p50_total": float(np.median(v.sum(axis=1))), "type": P4.LINE_TYPE[ln]}
            for ln, v in res.lines.items()]
    return pd.DataFrame(rows)


# ---- Phase 5D step F ----
def decide_items(n: int = 3) -> list[dict]:
    """'What needs a decision' on The big picture: the n choices with the widest gap between 20% lower and 20% higher
    (sensitivity.csv), with that gap and which direction helps."""
    swings, phrases = lever_swings(n), lever_phrases(n)
    return [{"key": s["key"], "label": s["label"], "gap": C.DECIDE_GAP.format(swing=s["text"]),
             "helps": C.DECIDE_HELPS.format(phrase=p), "value": s["value"]} for s, p in zip(swings, phrases)]


def payback_dots(k: float = 1.0) -> list[dict]:
    """One row per outlook for the 'when each outlook pays for itself' strip (break_even_summary.csv): the typical
    month when it pays for itself in at least half of the futures, else 'not within'."""
    out = []
    for sc in D.outlooks():
        be = D.row("break_even_summary", sc, k)
        T_ = int(be["T"])
        prob = float(be["prob_break_even_within_T"])
        month = float(be["p50_month"]) if prob >= 0.5 and math.isfinite(float(be["p50_month"])) else None
        tip = (C.DOT_TIP_YES.format(outlook=C.OUTLOOK[sc], month=int(round(month)), share=T.share(prob), months=T_)
               if month is not None else C.DOT_TIP_NO.format(outlook=C.OUTLOOK[sc], months=T_, share=T.share(1 - prob)))
        out.append({"key": sc, "label": C.OUTLOOK[sc], "month": month, "prob": prob, "horizon": T_, "tip": tip})
    return out


# ---- Beginner pass ----
def ideas() -> list[str]:
    """'Ideas to consider' on The big picture: suggestions, each tied to a number in the saved results."""
    top = lever_swings(1)[0]
    scenario, k = sk()
    b = D.table("cost_breakdown")
    b = b[(b["scenario"] == scenario) & np.isclose(b["multiplier"], k)].set_index("line")
    tot = D.row("totals_summary", scenario, k)
    be = D.row("break_even_summary", scenario, k)
    out = [C.IDEA_LEVER.format(lever=top["label"].lower(), swing=top["text"]),
           C.IDEA_TRAINING.format(share=T.share(float(b.loc["enablement", "p50_share_of_cost"]))),
           C.IDEA_CASH.format(peak=T.money(float(tot["peak_investment_p50"])))]
    if float(be["prob_break_even_within_T"]) < 0.5:
        out.append(C.IDEA_LONGER)
    return out


# ---- UI v3: page headlines that make the point ----
def page_headline(key: str) -> str:
    """The headline of a page: a statement filled in from the saved results where it carries a number. Without the
    saved results the page name stands in, and the page itself shows the friendly 'missing' note."""
    try:
        return _headline(key)
    except (D.Missing, KeyError, IndexError, ValueError):
        return C.PAGES.get(key, ("",))[0]


def _headline(key: str) -> str:
    scenario, k = sk()
    if key == "overview":
        be = D.row("break_even_summary", scenario, k)
        head = C.HEAD_YOURS if D.yours() is not None else C.HEAD
        if float(be["prob_break_even_within_T"]) >= 0.5 and math.isfinite(float(be["p50_month"])):
            return head["overview_yes"].format(month=int(round(float(be["p50_month"]))))
        return head["overview_no"].format(months=int(be["T"]))
    if key == "costs":
        b = D.table("cost_breakdown")
        b = b[(b["scenario"] == scenario) & np.isclose(b["multiplier"], k)].set_index("line")
        if float(b.loc[["enablement", "integration"], "p50_share_of_cost"].sum()) >= 0.5:
            return C.HEAD["costs_people"]
        return C.HEAD["costs_other"].format(line=C.LINE[str(b["p50_share_of_cost"].idxmax())])
    if key == "timing":
        rows = payback_dots(k)
        pays = [r for r in rows if r["month"] is not None]
        months = rows[0]["horizon"] if rows else 12
        if any(r["key"] == "expected" for r in pays):
            return C.HEAD["timing_expected"].format(month=int(round(next(r["month"] for r in pays if r["key"] == "expected"))))
        if len(pays) == 1:
            return C.HEAD["timing_some"].format(names=pays[0]["label"].lower(), months=months)
        return C.HEAD["timing_none"].format(months=months)
    if key == "levers":
        s = lever_swings(2)
        if len(s) > 1 and math.isclose(s[0]["value"], s[1]["value"], rel_tol=1e-6):
            return C.HEAD["levers_two"].format(a=s[0]["label"], b=s[1]["label"].lower())
        return C.HEAD["levers_one"].format(a=s[0]["label"])
    return C.HEAD.get(key, C.PAGES.get(key, ("",))[0])
