"""Analyst mode: a global switch (off by default) and the technical sections it adds to the Data and Reliability pages.
Everything shown here is read from artifacts/ (src/build_artifacts.py); nothing is fitted on a page load."""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from dashboard.core import artifacts as A
from dashboard.core import data as D
from dashboard.ui import charts_analyst as CA
from dashboard.ui import components as K
from dashboard.ui import copy as C
from dashboard.ui import copy_technical as CT

KEY = "aiwi_analyst"


def toggle() -> None:
    """In the side panel on every page; shared across pages and mirrored to the address (?analyst=on)."""
    if KEY not in st.session_state:
        st.session_state[KEY] = st.query_params.get("analyst") == "on"

    def _sync():
        if st.session_state.get(KEY):
            st.query_params["analyst"] = "on"
        elif "analyst" in st.query_params:
            del st.query_params["analyst"]

    st.toggle(CT.ANALYST, key=KEY, help=CT.ANALYST_HELP, on_change=_sync)


def on() -> bool:
    return bool(st.session_state.get(KEY, False))


def _table(df: pd.DataFrame, cols: dict, key: str, filename: str) -> None:
    t = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    t = t.astype(object).where(t.notna(), "")  # blanks, not "None"
    st.dataframe(t, hide_index=True, width="stretch")
    st.download_button(C.DOWNLOAD_CSV, t.to_csv(index=False).encode("utf-8"), f"{filename}.csv", "text/csv",
                       key=f"{key}_dl", icon=":material/download:")


def data_section(name: str, dated: bool) -> None:
    """Data page: STL, stationarity verdict, ACF/PACF, subseries, break test, outliers."""
    try:
        d, stl = A.diagnostics(name), A.stl(name)
    except (D.Missing, KeyError):
        K.empty_state()
        return
    K.section_title(CT.ANALYST_DATA_TITLE, anchor="analyst")
    K.note(CT.STL_STRENGTH.format(trend=d["trend_strength"], season=d["seasonal_strength"]))
    K.chart(CA.stl_chart(stl, dated), f"an_stl_{name}", f"stl_{name}")
    s = d["stationarity"]
    K.chart_title(CT.STAT_TITLE)
    K.note(CT.STAT_LINE.format(adf=s["adf_p"], kpss=s["kpss_p"], verdict=s["verdict"]))
    c1, c2 = st.columns(2)
    with c1:
        K.chart(CA.correlogram(d["acf"], d["band"], CT.ACF_TITLE), f"an_acf_{name}", f"acf_{name}")
    with c2:
        K.chart(CA.correlogram(d["pacf"], d["band"], CT.PACF_TITLE, partial=True), f"an_pacf_{name}", f"pacf_{name}")
    K.chart_note(CT.BAND_NOTE.format(band=d["band"]))
    if int(d.get("period") or 1) > 1:
        K.chart(CA.subseries(stl, int(d["period"]), dated), f"an_sub_{name}", f"subseries_{name}")
    b = d["break"]
    if b.get("cusum_p") is not None and b["cusum_p"] < 0.05 and b.get("likely_shift_label") is not None:
        K.note(CT.BREAK_LINE.format(stat=b["cusum_stat"], p=b["cusum_p"], at=b["likely_shift_label"]))
    elif b.get("cusum_stat") is not None:
        K.note(CT.BREAK_NONE.format(stat=b["cusum_stat"], p=b["cusum_p"]))
    o = d["outliers"]
    K.note(CT.OUTLIER_LINE.format(n=o["count"], treatment=o["treatment"]))


def coverage_80(name: str) -> float | None:
    """Real share of values inside the calibrated 80% range in rolling-origin CV (None when unavailable)."""
    try:
        c = A.conformal(name)
    except (D.Missing, KeyError):
        return None
    v = c["coverage"].get("0.8")
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def reliability_section(name: str, chosen: str, labels: dict) -> None:
    """Reliability page: model cards, CV table with DM test, error by horizon, residual checks, coverage plot."""
    try:
        cards, cv, hz, dm = A.model_cards(name), A.cv_metrics(name), A.cv_horizon(name), A.dm_tests(name)
        res, conf = A.residuals(name), A.conformal(name)
    except (D.Missing, KeyError):
        K.empty_state()
        return
    labels = {"theta": "Theta", **labels}
    K.section_title(CT.ANALYST_REL_TITLE, anchor="analyst")
    K.chart_title(CT.CARDS_TITLE)
    _table(cards.round(3), CT.CARDS_COLS, f"an_cards_{name}", f"model_cards_{name}")
    K.chart_title(CT.CV_TITLE)
    K.note(CT.CV_SUB.format(folds=conf["folds"]))
    cv = cv.merge(dm[["model", "p_value"]].rename(columns={"p_value": "dm_p"}), on="model", how="left")
    cv = cv.sort_values("mase").assign(model=lambda t: t["model"].map(lambda m: labels.get(m, m)))
    _table(cv.round(3), CT.CV_COLS, f"an_cv_{name}", f"cross_validation_{name}")
    K.chart_note(CT.DM_NOTE)
    keep = set(  # best five by overall MASE, the chosen one and the yardstick
        A.cv_metrics(name).nsmallest(5, "mase")["model"]) | {chosen, "seasonal_naive"}
    K.chart(CA.horizon_chart(hz[hz["model"].isin(keep)], chosen, labels), f"an_hz_{name}", f"error_by_step_{name}")
    K.chart_note(CT.HORIZON_NOTE)
    c1, c2 = st.columns(2)
    with c1:
        K.chart(CA.residual_line(res["values"]), f"an_res_{name}", f"residuals_{name}")
    with c2:
        if "qq" in res:
            K.chart(CA.qq(res["qq"]), f"an_qq_{name}", f"qq_{name}")
        else:
            K.note(CT.RESID_FEW.format(n=res["n"]), tone="warm")
    p = res.get("ljung_box_p")
    if p is not None:
        K.note(CT.LJUNG_LINE.format(p=p, word=CT.LJUNG_OK if p >= 0.05 else CT.LJUNG_BAD))
    K.chart(CA.coverage_chart(conf["coverage"]), f"an_cov_{name}", f"coverage_{name}")
    K.note(CT.COVERAGE_LINE.format(folds=conf["scored_folds"], pts=conf["scored_points"], cov=conf["coverage"]["0.8"],
                                   boot=conf["coverage_bootstrap_80"], score=conf["interval_score_80"],
                                   score_b=conf["interval_score_80_bootstrap"]))
    if conf["scored_folds"] < 3:
        K.note(CT.COVERAGE_THIN.format(folds=conf["scored_folds"]), tone="warm")
