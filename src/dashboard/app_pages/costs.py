"""Page 2, Where the money goes: monthly cost by type, cost shares, benefit versus cost."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.ui import charts  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.ui import copy_technical as CT  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

LINES = ("token_expenditure", "hosting", "enablement", "integration")


@st.fragment  # the flat / 3D switch redraws the donut only
def _donut(b, scenario: str, k: float) -> None:
    view = C.DONUT_VIEW[1]
    if K.motion_on():
        view = st.segmented_control(C.DONUT_VIEW_LABEL, list(C.DONUT_VIEW), default=C.DONUT_VIEW[1],
                                    key="costs_donut_view", label_visibility="collapsed",
                                    help=C.HINT["donut_view"]) or C.DONUT_VIEW[1]  # flat first, 3D optional
    if view == C.DONUT_VIEW[0]:
        K.donut_3d(logic.cost_slices(b))
    else:
        K.chart(charts.donut(b), f"costs_donut_{scenario}_{k}", "cost_split")
    K.insight_row(*EX.donut(b), stacked=True)


def render() -> None:
    K.page_header(logic.page_headline("costs"), C.SUB["costs"], C.PAGES["costs"][0])
    try:
        scenario, k = K.scenario_bar(D.outlooks(), D.cautions())
        K.tags(list(LINES))
        stack = charts.cost_stack({ln: D.monthly(scenario, k, ln) for ln in LINES})
        K.chart(stack, f"costs_stack_{scenario}_{k}", "monthly_cost_by_type")
        K.insight_row(*EX.cost_stack(D.monthly(scenario, k, "total_cost")))
        b = D.table("cost_breakdown")
        b = b[(b["scenario"] == scenario) & np.isclose(b["multiplier"], k)]
        c1, c2 = st.columns(2)
        with c1:
            _donut(b, scenario, k)
        with c2:
            fig = charts.benefit_vs_cost(D.monthly(scenario, k, "total_cost"), D.monthly(scenario, k, "value"),
                                         T.outlook_color(scenario))
            K.chart(fig, f"costs_benefit_{scenario}_{k}", "benefit_and_cost")
            K.insight_row(*EX.benefit_cost(D.monthly(scenario, k, "total_cost"), D.monthly(scenario, k, "value")), stacked=True)
        with st.expander(C.INCLUDED_TITLE, icon=":material/list:"):
            for ln in LINES:
                st.markdown(f"**{C.LINE[ln]}** ({C.LINE_TAG[ln]}): {C.INCLUDED[ln]}")
    except D.Missing:
        K.empty_state()


render()
