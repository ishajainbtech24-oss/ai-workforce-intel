"""The big picture: a compact title (the promise itself is on Welcome), four KPI cards (expected outlook), the running
balance next to 'What needs a decision', the trends behind the costs with how close past predictions came, key
findings, and the year-end balance in 3D inside a panel that opens on request."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard.ui import charts  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import currency as CUR  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402


ICON = {"cost": "cost", "benefit": "benefit", "balance": "balance", "payback": "payback"}


def _cards(sc: str, k: float) -> None:
    v, f, chips = D.overview_kpis(sc, k), logic.overview_cards(sc, k), logic.card_status(sc, k)
    spark = {"cost": K.sparkline_svg(D.monthly(sc, k, "total_cost")["p50"], T.tok("accent")),
             "benefit": K.sparkline_svg(D.monthly(sc, k, "value")["p50"], T.tok("accent-2")),
             "balance": K.sparkline_svg(D.monthly(sc, k, "cumulative_net")["p50"], T.tok("warm"), zero=True),
             "payback": K.sparkline_svg(D.monthly(sc, k, "value")["p50"].to_numpy()
                                        - D.monthly(sc, k, "total_cost")["p50"].to_numpy(), T.tok("warm"), zero=True)}
    cards = [K.kpi_card(C.KPI[k][0], f[k], C.KPI[k][1], spark[k], count=None if k == "payback" else CUR.to_inr(v[k]),
                        tone=("warm" if k in ("balance", "payback") and v["balance"] < 0 else "") + (" key" if k == "balance" else ""),
                        icon_name=ICON[k], chip=chips[k], i=n)
             for n, k in enumerate(("balance", "cost", "benefit", "payback"))]
    K.eyebrow(C.OUTLOOK[sc])
    K.kpi_row(cards, lead=True)


@st.fragment  # the view switch redraws this chart only
def _chart(sc: str, k: float) -> None:
    view = st.segmented_control("View", [C.VIEW_RANGE, C.VIEW_TYPICAL], default=C.VIEW_RANGE,
                                label_visibility="collapsed", key="overview_view", help=C.HINT["view"])
    series, paybacks = {}, {}
    for o in D.outlooks():
        series[o] = D.monthly(o, k, "cumulative_net")
        be = D.row("break_even_summary", o, k)
        paybacks[o] = be["p50_month"] if be["prob_break_even_within_T"] >= 0.5 else None
    fig = charts.running_balance(series, view != C.VIEW_TYPICAL, D.horizon(), paybacks, focus=sc)
    K.chart(fig, "overview_balance", "running_balance")
    K.insight_row(*EX.balance(series, paybacks, D.horizon()))


def _decide() -> None:
    K.numbered_card(C.DECIDE_TITLE, C.DECIDE_SUB, [(it["label"], it["gap"], it["helps"]) for it in logic.decide_items(3)])
    st.page_link(K.PAGE_FILES["levers"], label=f'{C.PAGES["levers"][0]} →', icon=C.PAGES["levers"][1])


def _strip() -> None:
    """The cost trends behind the money, and how close past predictions came (saved Phase 2 and 3 results)."""
    try:
        cards = []
        for name in LF.STRIP_SERIES:
            change, end, when = LF.expected_change(D.history(name), D.saved_forecast(name))
            cards.append((C.SERIES[name][0], C.STRIP_CHANGE.format(change=LF.change_text(change), end=end),
                          C.STRIP_MEANING.format(when=when)))
        hold, chosen = D.phase_table(2, "holdout"), D.phase_table(2, "chosen_models")
        usage = [LF.miss_share(hold, chosen, s) for s in LF.USAGE_SERIES if s in D.forecast_series()]
        reliable = C.STRIP_RELIABLE.format(pay=LF.pct(LF.miss_share(hold, chosen, LF.STRIP_SERIES[0])),
                                           host=LF.pct(LF.miss_share(hold, chosen, LF.STRIP_SERIES[1])),
                                           lo=LF.pct(min(usage)), hi=LF.pct(max(usage)))
    except (D.Missing, KeyError, ValueError):
        return  # the money results still show; the forecast pages say what is missing
    K.section_title(C.STRIP_TITLE)
    K.card_grid([K.kpi_card(t, v, m, i=n) for n, (t, v, m) in enumerate(cards)]
                + [K.kpi_card(C.STRIP_RELIABLE_TITLE, "", reliable, tone="text strip-reliable", i=2)])
    with st.container(horizontal=True, key="overview_strip_links"):
        st.page_link(K.PAGE_FILES["forecast"], label=f"{C.STRIP_LINK_EXPECT} →", icon=C.PAGES["forecast"][1])
        st.page_link(K.PAGE_FILES["reliable"], label=f"{C.STRIP_LINK_RELIABLE} →", icon=C.PAGES["reliable"][1])


def _insights() -> None:
    """Facts from the results, then suggestions clearly labelled as suggestions."""
    K.section_title(C.INSIGHTS_DATA_TITLE)
    K.insight_cards(list(zip(("1", "2", "3"), logic.findings())))
    K.section_title(C.INSIGHTS_IDEAS_TITLE, C.INSIGHTS_IDEAS_NOTE)
    K.insight_cards([("→", t) for t in logic.ideas()], kind="idea")


def _flow() -> None:
    items = logic.year_end_balances(logic.sk()[1])
    with st.expander(C.SEE_3D, icon=":material/view_in_ar:"):
        c1, c2 = st.columns([3, 2])
        with c1:
            K.money_flow(items)
        with c2:
            K.chart(charts.year_end_bars(items), "overview_year_end", "year_end_balance")
        K.insight_row(*EX.year_end(items, D.horizon()))


def render() -> None:
    K.page_header(logic.page_headline("overview"), logic.words("OVERVIEW_SUB"), C.PAGES["overview"][0])
    try:
        sc, k = K.scenario_bar(D.outlooks(), D.cautions())
        _cards(sc, k)
        left, right = st.columns([2.3, 1], gap="medium")
        with left:
            _chart(sc, k)
        with right:
            _decide()
        _strip()
        _insights()
        _flow()
    except D.Missing:
        K.empty_state()


render()
