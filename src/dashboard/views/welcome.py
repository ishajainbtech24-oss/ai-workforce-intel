"""Welcome: the promise in one sentence, a real chart of what happened and what we expect (hosting prices, from
the saved Phase 3 results), how it works in three steps, and three headline numbers of the example company."""
import html
import math
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard import charts_forecast as CF  # noqa: E402
from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import currency as CUR  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import explain as EX  # noqa: E402
from dashboard import logic  # noqa: E402
from dashboard import logic_forecasts as LF  # noqa: E402
from dashboard import theme as T  # noqa: E402


def _hero() -> None:
    # the headline lives in the 3D banner; a hidden copy keeps the page's main heading for screen readers
    st.markdown(f'<h1 class="welcome-title sr-only">{html.escape(C.HERO_TITLE)}</h1>', unsafe_allow_html=True)
    K.hero()
    with st.container(key="aiwi_cta", horizontal=True):
        st.page_link(K.PAGE_FILES["overview"], label=f"{C.WELCOME_CTA} →")
        st.markdown(f'<a class="aiwi-ghost" href="#how-it-works">{html.escape(C.WELCOME_HOW)}</a>', unsafe_allow_html=True)
    left, right = st.columns([1.6, 1], gap="large")
    with right:
        _steps()
    with left:
        try:
            d = LF.hosting_hero(D.processed(LF.HOSTING[0]), D.saved_forecast(LF.HOSTING[0]))
        except D.Missing:
            K.missing()
            return
        st.markdown(f'<div class="aiwi-chart-title">{html.escape(C.WELCOME_CHART_TITLE)}</div>', unsafe_allow_html=True)
        st.plotly_chart(CF.history_forecast(d, "", 340, C.AXIS_PRICE_LEVEL),
                        config=T.PLOT_CONFIG, width="stretch", theme=None)
        st.markdown(f'<div class="aiwi-chart-note">{html.escape(C.WELCOME_CHART_NOTE.format(value=LF.level(d["expected"][-1]), end=LF.month_year(d["fc_dates"][-1]), low=LF.level(d["low"][-1]), high=LF.level(d["high"][-1])))}</div>',
                    unsafe_allow_html=True)
        K.chart_guide(EX.welcome(d))


def _steps() -> None:
    st.markdown(f'<h2 class="aiwi-h2 steps-title" id="how-it-works">{html.escape(C.WELCOME_STEPS_TITLE)}</h2>',
                unsafe_allow_html=True)
    body = "".join(f'<div class="insight" style="--i:{n}"><div class="insight-icon">{n + 1}</div>'
                   f'<div class="insight-text"><b>{html.escape(t)}</b><br>{html.escape(s)}</div></div>'
                   for n, (t, s) in enumerate(C.WELCOME_STEPS))
    st.markdown(f'<div class="insight-grid stack">{body}</div>', unsafe_allow_html=True)


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
        K.missing()
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
