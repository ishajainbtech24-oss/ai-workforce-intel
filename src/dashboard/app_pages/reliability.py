"""How reliable it is: for one of the seven real trends, how close the chosen approach came on the most recent real values
that were held back (Phase 2), how often real values landed inside the likely range (Phase 2 and Phase 3), and how
every approach that ran compares. Plain names only; every number comes from the saved Phase 2 and 3 tables."""
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

DEFAULT = "ppi_hosting_monthly"


def _pick(series: list[str]) -> str:
    return K.trend_picker(series)


def _tiles(v: dict) -> None:
    icons = ("benefit", "balance", "payback")
    warm = (False, v["flag"] is True, v["vs_reference"] < 0)
    K.kpi_row([K.kpi_card(label, value, meaning, tone="warm" if w else "", icon_name=ic, i=n)
               for n, ((label, value, meaning), ic, w) in enumerate(zip(v["tiles"], icons, warm))])


def render() -> None:
    K.page_header(C.HEAD["reliable"], C.RELIABLE_SUB, C.PAGES["reliable"][0])
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
        K.empty_state()
        return
    desc = C.SERIES[name][1] + ("" if v["dated"] else " " + C.NO_DATES)
    K.lede(desc)
    K.verdict(v["verdict"], tone="rel")
    _tiles(v)
    K.chart_title(C.PAST_CHART_TITLE)
    K.chart(CF.past_check_chart(v["chart"]), f"rel_past_{name}", f"past_check_{name}")
    K.insight_row(*EX.past(v))
    if v["flag"] and v["hits"]:
        K.note(C.RANGE_WARN.format(inside=v["hits"][0], n=v["hits"][1]), tone="warm")
    K.section_title(C.RANK_TITLE, C.RANK_SUB)
    _ranking(name, v)
    for note in v["notes"]:
        K.note(note)
    _technical(name, v)


@st.fragment  # "show all" redraws the ranking only
def _ranking(name: str, v: dict) -> None:
    show_all = (st.toggle(C.RANK_SHOW_ALL, value=False, key=f"rel_all_{name}", help=C.HINT["show_all"])
                if len(v["ranking"]) > CF.RANK_ROWS + 1 else True)
    K.chart(CF.ranking_chart(v["ranking"], v["unit"], show_all), f"rel_rank_{name}_{show_all}", f"ranking_{name}")
    K.insight_row(*EX.ranking(v))


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
