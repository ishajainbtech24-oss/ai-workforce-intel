"""Page 2, Where the money goes: monthly cost by type, cost shares, benefit versus cost."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard import charts, logic  # noqa: E402
from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import explain as EX  # noqa: E402
from dashboard import copy_technical as CT  # noqa: E402
from dashboard import theme as T  # noqa: E402

LINES = ("token_expenditure", "hosting", "enablement", "integration")


def render() -> None:
    K.page_title(logic.page_headline("costs"), C.SUB["costs"], C.PAGES["costs"][0])
    try:
        scenario, k = K.pickers("costs", D.outlooks(), D.cautions())
        K.tags(list(LINES))
        stack = charts.cost_stack({ln: D.monthly(scenario, k, ln) for ln in LINES})
        st.plotly_chart(stack, config=T.PLOT_CONFIG, width="stretch", theme=None)
        K.chart_guide(EX.cost_stack(D.monthly(scenario, k, "total_cost")))
        b = D.table("cost_breakdown")
        b = b[(b["scenario"] == scenario) & np.isclose(b["multiplier"], k)]
        c1, c2 = st.columns(2)
        with c1:
            view = C.DONUT_VIEW[1]
            if K.motion_on():
                view = st.segmented_control(C.DONUT_VIEW_LABEL, list(C.DONUT_VIEW), default=C.DONUT_VIEW[0],
                                            key="costs_donut_view", label_visibility="collapsed",
                                            help=C.HINT["donut_view"]) or C.DONUT_VIEW[0]
            if view == C.DONUT_VIEW[0]:
                K.donut_3d(logic.cost_slices(b))
            else:
                st.plotly_chart(charts.donut(b), config=T.PLOT_CONFIG, width="stretch", theme=None)
            K.chart_guide(EX.donut(b), stacked=True)
        with c2:
            fig = charts.benefit_vs_cost(D.monthly(scenario, k, "total_cost"), D.monthly(scenario, k, "value"),
                                         T.outlook_color(scenario))
            st.plotly_chart(fig, config=T.PLOT_CONFIG, width="stretch", theme=None)
            K.chart_guide(EX.benefit_cost(D.monthly(scenario, k, "total_cost"), D.monthly(scenario, k, "value")), stacked=True)
        with st.expander(C.INCLUDED_TITLE, icon=":material/list:"):
            for ln in LINES:
                st.markdown(f"**{C.LINE[ln]}** ({C.LINE_TAG[ln]}): {C.INCLUDED[ln]}")
    except D.Missing:
        K.missing()


render()
