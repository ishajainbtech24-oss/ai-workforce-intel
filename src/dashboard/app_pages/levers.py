"""Page 4, What matters most: which choices change the result most, and what could change the verdict."""
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
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.ui import copy_technical as CT  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402
from dashboard.core import decision as X  # noqa: E402


def render() -> None:
    K.page_header(logic.page_headline("levers"), C.SUB["levers"], C.PAGES["levers"][0])
    try:
        scenario, k = K.scenario_bar(D.outlooks(), D.cautions())
        sens = D.sensitivity(scenario, k).sort_values("swing_cum_net_T", ascending=False)
        swings = logic.lever_swings(6)
        K.depth_bars(swings)
        K.insight_row(*EX.levers_depth(swings))
        K.chart(charts.levers(sens), "levers_tornado", "what_matters_most")
        K.insight_row(*EX.levers_chart(sens))
        a, b, c = (C.LEVER.get(x, x).lower() for x in sens["input"].head(3))
        K.note(C.LEVER_TAKEAWAY.format(a=a, b=b, c=c))
        be = D.row("break_even_summary", scenario, k)
        if be["prob_break_even_within_T"] < 0.5:
            tot = D.row("totals_summary", scenario, k)
            first, second = logic.lever_phrases(2)
            K.section_title(C.NO_PAYBACK_BOX_TITLE)
            K.verdict(logic.words("NO_PAYBACK").format(months=int(be["T"]), balance=T.money(tot["cum_net_T_p50"]),
                                                       outlook=C.OUTLOOK[scenario].lower()),
                      C.NO_PAYBACK_LEVERS.format(a=first, b=second), tone="warm")
        _goal(int(be["T"]))
        K.tech_details([CT.TERMS["sensitivity"]])
    except D.Missing:
        K.empty_state()


def _goal(months: int) -> None:
    """Goal-seek: the time saved that gives an even chance of paying for itself within the horizon."""
    with st.spinner(C.WORKING):
        g = X.goal_seek("expected")
    if g.get("status") == "skipped":
        return
    K.section_title(C.GOAL_TITLE)
    if g["status"] == "unreachable":
        K.verdict(C.GOAL_UNREACHABLE.format(months=months), tone="warm")
        return
    from engine.simulate import scenario_fraction
    base = D.active_inputs()
    pct = lambda f: f"{f:.1%}"  # noqa: E731
    K.verdict(C.GOAL_LINE.format(months=months, needed=pct(g["needed"]),
                                 expected=pct(scenario_fraction(D.outlook_table(), "expected", base)[0]),
                                 optimistic=pct(scenario_fraction(D.outlook_table(), "optimistic", base)[0])), tone="card")


render()
