"""Page 3, When it pays for itself: verdict, month distribution, the three outlooks side by side."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard import charts, logic  # noqa: E402
from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import explain as EX  # noqa: E402
from dashboard import copy_technical as CT  # noqa: E402
from dashboard import theme as T  # noqa: E402

NARROW = 0.10  # likely range of the year-end balance under 10% of total cost counts as narrow


def _compare(k: float, horizon: int) -> pd.DataFrame:
    rows = []
    for sc in D.outlooks():
        be, tot = D.row("break_even_summary", sc, k), D.row("totals_summary", sc, k)
        typical = be["p50_month"] if be["prob_break_even_within_T"] > 0 else float("nan")
        rows.append(dict(zip(C.COMPARE_COLS, [C.OUTLOOK[sc], T.share(be["prob_break_even_within_T"]),
                                              T.month(typical, horizon),
                                              f"{T.money(tot['cum_net_T_p10'])} to {T.money(tot['cum_net_T_p90'])}",
                                              T.money(tot["peak_investment_p50"])])))
    return pd.DataFrame(rows)


def render() -> None:
    K.page_title(logic.page_headline("timing"), C.SUB["timing"], C.PAGES["timing"][0])
    try:
        scenario, k = K.pickers("timing", D.outlooks(), D.cautions())
        horizon = D.horizon()
        be, tot = D.row("break_even_summary", scenario, k), D.row("totals_summary", scenario, k)
        st.markdown(f'<div class="verdict">{logic.verdict(be["prob_break_even_within_T"], be["p50_month"], horizon)}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="aiwi-chart-title">{C.TIMING_DOTS_TITLE}</div>', unsafe_allow_html=True)
        dots = logic.payback_dots(k)
        st.plotly_chart(charts.payback_dots(dots), config=T.PLOT_CONFIG, width="stretch", theme=None,
                        key=f"timing_dots_{k}")
        K.chart_guide(EX.timing_dots(dots))
        with st.spinner(C.WORKING):
            counts, none, total = D.payback_counts(scenario, k)
        st.plotly_chart(charts.payback_bars(counts, none, total, horizon, T.outlook_color(scenario)),
                        config=T.PLOT_CONFIG, width="stretch", theme=None)
        K.chart_guide(EX.timing_bars(counts, none, total, horizon))
        if (tot["cum_net_T_p90"] - tot["cum_net_T_p10"]) / tot["total_cost_p50"] < NARROW:
            st.markdown(f'<div class="note">{C.NARROW_NOTE}</div>', unsafe_allow_html=True)
        st.markdown(f"#### {C.COMPARE_TITLE}")
        K.table(_compare(k, horizon), dots=[T.outlook_color(sc) for sc in D.outlooks()])
        t = CT.TERMS
        K.tech_details([(t["monte_carlo"][0], t["monte_carlo"][1].format(n=f"{total:,}")), t["caution"]])
    except D.Missing:
        K.missing()


render()
