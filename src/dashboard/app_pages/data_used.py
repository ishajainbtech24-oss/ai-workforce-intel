"""The data we used: the seven real public series behind every forecast. For the trend picked at the top: plain facts
(time span, number of points, unusual points, missing values), which part of the source was used and why, a plain
summary, every real value on a chart, the repeating pattern, and Phase 1's unusual points. Read only."""
import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard.ui import charts_forecast as CF  # noqa: E402
from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.ui import copy_technical as CT  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402
from dashboard.ui import analyst as AN  # noqa: E402

DEFAULT = "ppi_hosting_monthly"


def _pick(series: list[str]) -> str:
    return K.trend_picker(series)


def _optional(phase: int, table: str):
    try:
        return D.phase_table(phase, table)
    except D.Missing:
        return None


def render() -> None:
    K.page_header(C.HEAD["data"], C.DATA_SUB, C.PAGES["data"][0])
    try:
        series = D.forecast_series()
        if not series:
            raise D.Missing("forecasts")
        name = _pick(series)
        g = LF.grain(D.saved_forecast(name))
        v = LF.data_view(name, D.history(name), g, D.source_points(name), _optional(1, "anomalies"),
                         _optional(1, "decomposition"))
    except D.Missing:
        K.empty_state()
        return
    notes = [C.SERIES[name][1], v["window"]] + ([C.NO_DATES] if not v["dated"] else []) + ([v["outage"]] if v["outage"] else [])
    K.lede(" ".join(notes))
    K.kpi_row([K.kpi_card(label, value, meaning, i=n) for n, (label, value, meaning) in enumerate(v["tiles"])])
    K.verdict(v["summary"], tone="rel")
    happened, pattern, unusual = st.tabs(list(C.DATA_TABS))
    with happened:
        K.chart(CF.data_chart(v["chart"]), f"data_chart_{name}", f"history_{name}")
        K.insight_row(*EX.data_history(name, v, g))
        slug = re.sub(r"[^a-z0-9]+", "_", C.SERIES[name][0].lower()).strip("_")
        st.download_button(C.DOWNLOAD_DATA, v["download"].to_csv(index=False).encode("utf-8"),
                           file_name=f"data_{slug}.csv", mime="text/csv", icon=":material/download:", key="data_download")
    with pattern:
        K.chart_title(v["pattern"]["title"])
        K.chart(CF.pattern_chart(v["pattern"]), f"data_pattern_{name}", f"pattern_{name}")
        K.insight_row(*EX.data_pattern(v, g))
        if v["pattern"]["note"]:
            K.note(v["pattern"]["note"])
    with unusual:
        K.note(C.UNUSUAL_INTRO)
        if v["unusual_n"]:
            top = v["unusual"].head(LF.TOP_UNUSUAL)
            if v["unusual_n"] > LF.TOP_UNUSUAL:
                K.lede(C.UNUSUAL_TOP.format(k=LF.TOP_UNUSUAL, n=v["unusual_n"]))
            K.table(top)
        else:
            K.lede(C.UNUSUAL_NONE)
    t = CT.TERMS
    K.tech_details([t["stl"], (t["strength"][0], t["strength"][1].format(trend=_num(v["trend"]), pattern=_num(v["pattern_strength"]))),
                    t["zscore"]])
    if AN.on():
        AN.data_section(name, v["dated"])


def _num(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "n/a"


render()
