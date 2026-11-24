"""The data we used: the seven real public series behind every forecast. For the trend picked at the top: plain facts
(time span, number of points, unusual points, missing values), which part of the source was used and why, a plain
summary, every real value on a chart, the repeating pattern, and Phase 1's unusual points. Read only."""
import html
import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard import charts_forecast as CF  # noqa: E402
from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import explain as EX  # noqa: E402
from dashboard import copy_technical as CT  # noqa: E402
from dashboard import logic_forecasts as LF  # noqa: E402
from dashboard import theme as T  # noqa: E402

DEFAULT = "ppi_hosting_monthly"


def _pick(series: list[str]) -> str:
    first = DEFAULT if DEFAULT in series else series[0]
    name = st.pills(C.PICK_SERIES, series, selection_mode="single", default=first,
                    format_func=lambda s: C.SERIES[s][0], key="data_series", help=C.HINT["series"])
    return name or first


def _optional(phase: int, table: str):
    try:
        return D.phase_table(phase, table)
    except D.Missing:
        return None


def render() -> None:
    K.page_title(C.HEAD["data"], C.DATA_SUB, C.PAGES["data"][0])
    try:
        series = D.forecast_series()
        if not series:
            raise D.Missing("forecasts")
        name = _pick(series)
        g = LF.grain(D.saved_forecast(name))
        v = LF.data_view(name, D.history(name), g, D.source_points(name), _optional(1, "anomalies"),
                         _optional(1, "decomposition"))
    except D.Missing:
        K.missing()
        return
    notes = [C.SERIES[name][1], v["window"]] + ([C.NO_DATES] if not v["dated"] else []) + ([v["outage"]] if v["outage"] else [])
    st.markdown(f'<p class="aiwi-sub fc-desc">{html.escape(" ".join(notes))}</p>', unsafe_allow_html=True)
    K.kpi_row([K.kpi_card(label, value, meaning, i=n) for n, (label, value, meaning) in enumerate(v["tiles"])])
    st.markdown(f'<div class="verdict rel-verdict">{html.escape(v["summary"])}</div>', unsafe_allow_html=True)
    happened, pattern, unusual = st.tabs(list(C.DATA_TABS))
    with happened:
        st.plotly_chart(CF.data_chart(v["chart"]), config=T.PLOT_CONFIG, width="stretch", theme=None,
                        key=f"data_chart_{name}")
        K.chart_guide(EX.data_history(name, v, g))
        slug = re.sub(r"[^a-z0-9]+", "_", C.SERIES[name][0].lower()).strip("_")
        st.download_button(C.DOWNLOAD_DATA, v["download"].to_csv(index=False).encode("utf-8"),
                           file_name=f"data_{slug}.csv", mime="text/csv", icon=":material/download:", key="data_download")
    with pattern:
        st.markdown(f'<div class="aiwi-chart-title">{html.escape(v["pattern"]["title"])}</div>', unsafe_allow_html=True)
        st.plotly_chart(CF.pattern_chart(v["pattern"]), config=T.PLOT_CONFIG, width="stretch", theme=None,
                        key=f"data_pattern_{name}")
        K.chart_guide(EX.data_pattern(v, g))
        if v["pattern"]["note"]:
            st.markdown(f'<div class="note">{html.escape(v["pattern"]["note"])}</div>', unsafe_allow_html=True)
    with unusual:
        st.markdown(f'<div class="note">{html.escape(C.UNUSUAL_INTRO)}</div>', unsafe_allow_html=True)
        if v["unusual_n"]:
            top = v["unusual"].head(LF.TOP_UNUSUAL)
            if v["unusual_n"] > LF.TOP_UNUSUAL:
                st.markdown(f'<p class="aiwi-sub">{html.escape(C.UNUSUAL_TOP.format(k=LF.TOP_UNUSUAL, n=v["unusual_n"]))}</p>',
                            unsafe_allow_html=True)
            K.table(top)
        else:
            st.markdown(f'<p class="aiwi-sub">{html.escape(C.UNUSUAL_NONE)}</p>', unsafe_allow_html=True)
    t = CT.TERMS
    K.tech_details([t["stl"], (t["strength"][0], t["strength"][1].format(trend=_num(v["trend"]), pattern=_num(v["pattern_strength"]))),
                    t["zscore"]])


def _num(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "n/a"


render()
