"""Page 4, What matters most: which choices change the result most, and what could change the verdict."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard import charts, logic  # noqa: E402
from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import explain as EX  # noqa: E402
from dashboard import copy_technical as CT  # noqa: E402
from dashboard import theme as T  # noqa: E402


def render() -> None:
    K.page_title(logic.page_headline("levers"), C.SUB["levers"], C.PAGES["levers"][0])
    try:
        sens = D.table("sensitivity").sort_values("swing_cum_net_T", ascending=False)
        swings = logic.lever_swings(6)
        K.depth_bars(swings)
        K.chart_guide(EX.levers_depth(swings))
        st.plotly_chart(charts.levers(sens), config=T.PLOT_CONFIG, width="stretch", theme=None)
        K.chart_guide(EX.levers_chart(sens))
        a, b, c = (C.LEVER.get(x, x).lower() for x in sens["input"].head(3))
        st.markdown(f'<div class="note">{C.LEVER_TAKEAWAY.format(a=a, b=b, c=c)}</div>', unsafe_allow_html=True)
        be = D.row("break_even_summary", "expected", 1.0)
        if be["prob_break_even_within_T"] < 0.5:
            tot = D.row("totals_summary", "expected", 1.0)
            first, second = logic.lever_phrases(2)
            st.markdown(f"#### {C.NO_PAYBACK_BOX_TITLE}")
            st.markdown(f'<div class="verdict warm-box">{logic.words("NO_PAYBACK").format(months=int(be["T"]), balance=T.money(tot["cum_net_T_p50"]))}'
                        f'<span class="sub">{C.NO_PAYBACK_LEVERS.format(a=first, b=second)}</span></div>',
                        unsafe_allow_html=True)
        K.tech_details([CT.TERMS["sensitivity"]])
    except D.Missing:
        K.missing()


render()
