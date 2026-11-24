"""What we expect next: pick one of the seven real trends and a length (only up to the saved forecast); the chart shows
what really happened, the latest real value, what we expect and the likely range; a side card says it in words.
Every number comes from the saved Phase 1 to 3 files through dashboard.data and dashboard.logic_forecasts."""
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

DEFAULT = "ppi_hosting_monthly"  # the same trend the Welcome page shows


def _pick(series: list[str]) -> str:
    name = st.pills(C.PICK_SERIES, series, selection_mode="single", default=DEFAULT if DEFAULT in series else series[0],
                    format_func=lambda s: C.SERIES[s][0], key="fc_series", help=C.HINT["series"])
    return name or (DEFAULT if DEFAULT in series else series[0])


def _length(name: str, g: str, saved: int) -> int:
    opts = LF.horizon_options(g, saved)
    one, many = C.GRAIN_WORD.get(g, ("step", "steps"))
    n = st.segmented_control(C.PICK_LENGTH, opts, default=opts[-1], key=f"fc_len_{name}",
                             format_func=lambda k: f"{k} {one if k == 1 else many}", help=C.HINT["length"])
    return int(n or opts[-1])


def _side(v: dict) -> None:
    st.markdown(f'<div class="verdict fc-card"><span class="fc-headline">{html.escape(v["headline"])}</span>'
                f'<span class="sub">{html.escape(v["range"])}</span>'
                f'<span class="sub">{html.escape(v["change"])}</span>'
                f'<span class="fc-small">{html.escape(C.RANGE_NOTE)}</span></div>', unsafe_allow_html=True)
    if v["hits"]:
        inside, n = v["hits"]
        warn = v["flag"] is True
        text = (C.RANGE_WARN if warn else C.RANGE_OK).format(inside=inside, n=n)
        st.markdown(f'<div class="note{" warm-note" if warn else ""}">{html.escape(text)}</div>', unsafe_allow_html=True)


def render() -> None:
    K.page_title(C.HEAD["forecast"], C.FORECAST_SUB, C.PAGES["forecast"][0])
    try:
        series = D.forecast_series()
        if not series:
            raise D.Missing("forecasts")
        name = _pick(series)
        fc = D.saved_forecast(name)
        g, saved = LF.grain(fc), LF.saved_horizon(fc)
        hist = D.history(name)
        try:
            ic = D.phase_table(3, "interval_check")
        except D.Missing:
            ic = None
        n = _length(name, g, saved)
        v = LF.forecast_view(name, n, hist, fc, ic)
    except D.Missing:
        K.missing()
        return
    desc = C.SERIES[name][1] + ("" if v["dated"] else " " + C.NO_DATES)
    st.markdown(f'<p class="aiwi-sub fc-desc">{html.escape(desc)}</p>', unsafe_allow_html=True)
    left, right = st.columns([2.3, 1], gap="medium")
    with left:
        st.plotly_chart(CF.series_chart(v["chart"]), config=T.PLOT_CONFIG, width="stretch", theme=None,
                        key=f"fc_chart_{name}_{n}")
        K.chart_guide(EX.forecast(name, v, float(hist["value"].iloc[-1])))
    with right:
        _side(v)
        slug = re.sub(r"[^a-z0-9]+", "_", C.SERIES[name][0].lower()).strip("_")
        st.download_button(C.DOWNLOAD_EXPECT, v["table"].to_csv(index=False).encode("utf-8"),
                           file_name=f"what_we_expect_{slug}_{n}.csv", mime="text/csv",
                           icon=":material/download:", key="fc_download")
    _technical(name, fc, n, g, saved)


def _technical(name: str, fc, n: int, g: str, saved: int) -> None:
    one, many = C.GRAIN_WORD.get(g, ("step", "steps"))
    try:
        ap = LF.chosen_approach(D.phase_table(2, "chosen_models"), name)
    except (D.Missing, KeyError):
        ap = str(fc["model"].iloc[0])
    sims = int(fc.loc[fc["sample_id"] >= 0, "sample_id"].nunique())
    t = CT.TERMS
    K.tech_details([(t["approach"][0], t["approach"][1].format(plain=LF.approach_label(ap, g), tech=CT.TECH_NAME.get(ap, ap))),
                    (t["simulation"][0], t["simulation"][1].format(n=sims)),
                    (t["percentile"][0], t["percentile"][1]), (t["interval"][0], t["interval"][1]),
                    (t["horizon"][0], t["horizon"][1].format(h=saved, grains=one if saved == 1 else many))])


render()
