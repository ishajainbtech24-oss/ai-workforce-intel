"""Page 3, When it pays for itself: verdict, month distribution, the three outlooks side by side."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402
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
    K.page_header(logic.page_headline("timing"), C.SUB["timing"], C.PAGES["timing"][0])
    try:
        scenario, k = K.scenario_bar(D.outlooks(), D.cautions())
        horizon = D.horizon()
        be, tot = D.row("break_even_summary", scenario, k), D.row("totals_summary", scenario, k)
        K.verdict(logic.verdict(be["prob_break_even_within_T"], be["p50_month"], horizon))
        if tot["total_value_p90"] < 0:
            K.note(C.NEGATIVE_BENEFIT.format(outlook=C.OUTLOOK[scenario].lower()), tone="warm")
        K.chart_title(C.TIMING_DOTS_TITLE)
        dots = logic.payback_dots(k)
        K.chart(charts.payback_dots(dots), f"timing_dots_{k}", "payback_by_outlook")
        K.insight_row(*EX.timing_dots(dots))
        with st.spinner(C.WORKING):
            counts, none, total = D.payback_counts(scenario, k)
        K.chart(charts.payback_bars(counts, none, total, horizon, T.outlook_color(scenario)),
                f"timing_bars_{scenario}_{k}", "payback_month")
        K.insight_row(*EX.timing_bars(counts, none, total, horizon))
        if (tot["cum_net_T_p90"] - tot["cum_net_T_p10"]) / tot["total_cost_p50"] < NARROW:
            K.note(C.NARROW_NOTE, trusted_html=True)
        K.section_title(C.COMPARE_TITLE)
        K.table(_compare(k, horizon), dots=[T.outlook_color(sc) for sc in D.outlooks()])
        _decision(scenario, k)
        t = CT.TERMS
        K.tech_details([(t["monte_carlo"][0], t["monte_carlo"][1].format(n=f"{total:,}")), t["caution"]])
    except D.Missing:
        K.empty_state()


def _decision(scenario: str, k: float) -> None:
    m = X.metrics(scenario, k)
    K.section_title(C.DECISION_TITLE, C.DECISION_SUB)
    cards = {"npv": T.money(m["npv"]), "roi": f"{m['roi']:+.0%}",
             "per_user": C.PER_MONTH.format(value=T.money(m["cost_per_user_month"]))}
    K.kpi_row([K.kpi_card(C.DECISION_KPI[key][0], value, C.DECISION_KPI[key][1], i=n,
                          tone="warm" if key != "per_user" and m["npv" if key == "npv" else "roi"] < 0 else "")
               for n, (key, value) in enumerate(cards.items())])


render()
