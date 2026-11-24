"""How reliable it is: for one of the seven real trends, how close the chosen approach came on the most recent real values
that were held back (Phase 2), how often real values landed inside the likely range (Phase 2 and Phase 3), and how
every approach that ran compares. Plain names only; every number comes from the saved Phase 2 and 3 tables."""
import html
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
                    format_func=lambda s: C.SERIES[s][0], key="rel_series", help=C.HINT["series"])
    return name or first


def _tiles(v: dict) -> None:
    icons = ("benefit", "balance", "payback")
    warm = (False, v["flag"] is True, v["vs_reference"] < 0)
    K.kpi_row([K.kpi_card(label, value, meaning, tone="warm" if w else "", icon_name=ic, i=n)
               for n, ((label, value, meaning), ic, w) in enumerate(zip(v["tiles"], icons, warm))])


def render() -> None:
    K.page_title(C.HEAD["reliable"], C.RELIABLE_SUB, C.PAGES["reliable"][0])
    try:
        series = D.forecast_series()
        if not series:
            raise D.Missing("forecasts")
        name = _pick(series)
        g = LF.grain(D.saved_forecast(name))
        try:
            ic = D.phase_table(3, "interval_check")
        except D.Missing:
            ic = None
        v = LF.reliability_view(name, D.history(name), g, D.phase_table(2, "chosen_models"),
                                D.phase_table(2, "holdout"), ic, D.phase_table(2, "leaderboard"))
    except (D.Missing, KeyError):
        K.missing()
        return
    desc = C.SERIES[name][1] + ("" if v["dated"] else " " + C.NO_DATES)
    st.markdown(f'<p class="aiwi-sub fc-desc">{html.escape(desc)}</p>'
                f'<div class="verdict rel-verdict">{html.escape(v["verdict"])}</div>', unsafe_allow_html=True)
    _tiles(v)
    st.markdown(f'<div class="aiwi-chart-title">{html.escape(C.PAST_CHART_TITLE)}</div>', unsafe_allow_html=True)
    st.plotly_chart(CF.past_check_chart(v["chart"]), config=T.PLOT_CONFIG, width="stretch", theme=None,
                    key=f"rel_past_{name}")
    K.chart_guide(EX.past(v))
    if v["flag"] and v["hits"]:
        st.markdown(f'<div class="note warm-note">{html.escape(C.RANGE_WARN.format(inside=v["hits"][0], n=v["hits"][1]))}</div>',
                    unsafe_allow_html=True)
    st.markdown(f'<h2 class="aiwi-h2">{html.escape(C.RANK_TITLE)}</h2><p class="aiwi-sub">{html.escape(C.RANK_SUB)}</p>',
                unsafe_allow_html=True)
    show_all = (st.toggle(C.RANK_SHOW_ALL, value=False, key=f"rel_all_{name}", help=C.HINT["show_all"])
                if len(v["ranking"]) > CF.RANK_ROWS + 1 else True)
    st.plotly_chart(CF.ranking_chart(v["ranking"], v["unit"], show_all), config=T.PLOT_CONFIG, width="stretch",
                    theme=None, key=f"rel_rank_{name}_{show_all}")
    K.chart_guide(EX.ranking(v))
    for note in v["notes"]:
        st.markdown(f'<div class="note">{html.escape(note)}</div>', unsafe_allow_html=True)
    _technical(name, v)


def _technical(name: str, v: dict) -> None:
    import pandas as pd
    one, many = C.GRAIN_WORD.get(v["grain"], ("step", "steps"))
    lb = D.phase_table(2, "leaderboard")
    lb = lb[(lb["driver"] == name) & (lb["status"] == "ok")].set_index("model")
    mase = lb["cv_mase"].get(v["approach"], float("nan"))
    t = CT.TERMS
    rows = [(t["approach"][0], t["approach"][1].format(plain=v["approach_label"], tech=CT.TECH_NAME.get(v["approach"], v["approach"]))),
            t["mae"], t["cv"], (t["holdout"][0], t["holdout"][1].format(n=v["n"], grains=one if v["n"] == 1 else many)),
            (t["mase"][0], t["mase"][1].format(value=f"{mase:.2f}")), t["seasonal_naive"], t["interval"]]
    rk = v["ranking"]
    table = pd.DataFrame({CT.RANK_TABLE_COLS[0]: rk["label"], CT.RANK_TABLE_COLS[1]: [CT.TECH_NAME.get(a, a) for a in rk["approach"]],
                          CT.RANK_TABLE_COLS[2]: [LF.amount(x, v["unit"]) if v["unit"] != "points" else f"{x:.3f}" for x in rk["average_miss"]],
                          CT.RANK_TABLE_COLS[3]: [f"{lb['cv_mase'].get(a, float('nan')):.2f}" for a in rk["approach"]]})
    K.tech_details(rows, table)


render()
