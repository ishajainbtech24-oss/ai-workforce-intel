"""Welcome: the promise in one sentence, a real chart of what happened and what we expect (hosting prices, from
the saved Phase 3 results), how it works in three steps, and three headline numbers of the example company."""
import math
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard.ui import charts_forecast as CF  # noqa: E402
from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import currency as CUR  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import artifacts as A  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402


def _hero() -> None:
    # the headline lives in the 3D banner; a hidden copy keeps the page's main heading for screen readers
    K.hidden_heading(C.HERO_TITLE)
    K.hero()
    with st.container(key="aiwi_cta", horizontal=True):
        st.page_link(K.PAGE_FILES["overview"], label=f"{C.WELCOME_CTA} →")
        K.anchor_link(C.WELCOME_HOW, "how-it-works")
    left, right = st.columns([1.6, 1], gap="large")
    with right:
        _steps()
    with left:
        try:
            d = LF.hosting_hero(D.processed(LF.HOSTING[0]), D.saved_forecast(LF.HOSTING[0]), cal=A.cal("ppi_hosting_monthly"))
        except D.Missing:
            K.empty_state()
            return
        K.chart_title(C.WELCOME_CHART_TITLE)
        K.chart(CF.history_forecast(d, "", 340, C.AXIS_PRICE_LEVEL), "welcome_hosting", "hosting_prices")
        K.chart_note(C.WELCOME_CHART_NOTE.format(value=LF.level(d["expected"][-1]), end=LF.month_year(d["fc_dates"][-1]),
                                                 low=LF.level(d["low"][-1]), high=LF.level(d["high"][-1])))
        K.insight_row(*EX.welcome(d))


def _steps() -> None:
    K.steps(C.WELCOME_STEPS, C.WELCOME_STEPS_TITLE, "how-it-works")


def _payback_note(horizon: int) -> str:
    for sc in ("expected", "optimistic"):
        be = D.row("break_even_summary", sc, 1.0)
        if be["prob_break_even_within_T"] >= 0.5 and math.isfinite(be["p50_month"]):
            return (C.WELCOME_PAYS_NOTE if sc == "optimistic" else C.KPI["payback"][1]).format(month=int(be["p50_month"]))
    return C.WELCOME_PAYS_NONE.format(months=horizon)


def _numbers() -> None:
    try:
        v, f = D.overview_kpis("expected", 1.0), logic.overview_cards("expected", 1.0)
        note = _payback_note(v["T"])
    except D.Missing:
        K.empty_state()
        return
    K.eyebrow(logic.words("WELCOME_NUMBERS_TITLE"))
    tone = "warm" if not math.isfinite(v["payback"]) else ""
    K.kpi_row([K.kpi_card(C.KPI["cost"][0], f["cost"], C.OUTLOOK["expected"], count=CUR.to_inr(v["cost"]),
                          icon_name="cost", i=0),
               K.kpi_card(C.KPI["benefit"][0], f["benefit"], C.KPI["benefit"][1], count=CUR.to_inr(v["benefit"]),
                          icon_name="benefit", i=1),
               K.kpi_card(C.KPI["payback"][0], f["payback"], note, tone=tone, icon_name="payback", i=2)])


def render() -> None:
    _hero()
    _numbers()


render()
