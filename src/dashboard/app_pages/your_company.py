"""Try your own numbers: a control panel that reruns the real engine on the visitor's figures.

Update runs every outlook and caution level plus the 'what matters most' runs (data.run_all, 5,000 futures each,
as the saved results). When the figures differ from the example company's, every results page switches to them
(data.YOURS_KEY in this browser session) until Reset to example, Back to the example in the side panel, or a page
refresh. Downloads: the month-by-month table (CSV, unchanged) and a PDF report with every chart (report_pdf)."""
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
from dashboard.core import currency as CUR  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.ui import copy_technical as CT  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

SLIDERS = {"adoption_target": (0, 100, 5), "realisation_rate": (0, 100, 5), "ramp_months": (1, 24, 1),
           "horizon_months": (6, 24, 1)}
LAYOUT = [("employees", "adoption_target", "ramp_months", "training_hours_per_new_user", "engineering_hours_build"),
          ("realisation_rate", "fixed_enablement_cost_per_month", "base_hourly_wage_staff", "base_hourly_wage_engineer"),
          ("tokens_per_active_user_per_month", "fixed_token_price_per_mtok", "base_monthly_hosting_cost", "horizon_months")]


# money boxes are in rupees: (step, display format); the steps feel natural for rupee amounts
MONEY_INPUTS = {"base_hourly_wage_staff": (50.0, "%.0f"), "base_hourly_wage_engineer": (50.0, "%.0f"),
                "fixed_enablement_cost_per_month": (5000.0, "%.0f"), "base_monthly_hosting_cost": (5000.0, "%.0f"),
                "fixed_token_price_per_mtok": (10.0, "%.2f")}


def _default(base: dict, f: str):
    if f in logic.PCT_FIELDS:
        return round(base[f] * 100)
    if f in logic.MONEY_FIELDS:  # the example company's dollar value, shown in rupees
        return round(float(CUR.to_inr(base[f])), 2)
    return base[f]


def _defaults(base: dict) -> dict:
    return {f: _default(base, f) for row in LAYOUT for f in row}


def _init(base: dict, reset: bool = False) -> None:
    for f, v in _defaults(base).items():
        if reset or f"co_{f}" not in st.session_state:
            st.session_state[f"co_{f}"] = v
    if reset or "co_outlook" not in st.session_state:
        st.session_state["co_outlook"] = C.OUTLOOK["expected"]


def _widget(f: str) -> None:
    label, unit, helptext = C.FIELDS[f]
    text = f"{label} ({unit})"
    if f in SLIDERS:
        lo, hi, step = SLIDERS[f]
        st.slider(text, lo, hi, step=step, key=f"co_{f}", help=helptext)
    elif f in MONEY_INPUTS:
        step, fmt = MONEY_INPUTS[f]
        st.number_input(text, key=f"co_{f}", help=helptext, min_value=0.0, step=step, format=fmt)
    else:
        cur = st.session_state[f"co_{f}"]
        whole = isinstance(cur, float) and float(cur).is_integer()
        st.number_input(text, key=f"co_{f}", help=helptext, step=1.0 if isinstance(cur, float) else 1,
                        format="%.0f" if whole else None)


def _form(outlooks: list[str]) -> bool:
    with st.form("company"):
        cols = st.columns(3)
        for col, fields in zip(cols, LAYOUT):
            with col:
                for f in fields:
                    _widget(f)
        st.selectbox(C.OUTLOOK_FIELD[0], [C.OUTLOOK[s] for s in outlooks], key="co_outlook", help=C.OUTLOOK_FIELD[1])
        return st.form_submit_button(C.UPDATE, type="primary", icon=":material/refresh:")


def _reset(base: dict) -> None:
    _init(base, reset=True)
    for key in ("co_result", "co_bundle", D.YOURS_KEY):
        st.session_state.pop(key, None)


def _same(a: dict, b: dict) -> bool:
    """True when the engine inputs equal the example company's (rupee rounding on the form allowed for)."""
    for k, v in b.items():
        w = a.get(k)
        if isinstance(v, (int, float)) and isinstance(w, (int, float)) and not isinstance(v, bool):
            if not np.isclose(float(v), float(w), rtol=1e-4, atol=1e-9):
                return False
        elif v != w:
            return False
    return True


def _pdf_module():
    """The PDF report module, loaded only here: a drawing library that cannot load must never stop the page (the
    form, results and table download all work without it)."""
    try:
        from dashboard.ui import report_pdf
        return report_pdf
    except Exception:  # noqa: BLE001 - any import failure only removes the PDF button
        import logging
        logging.getLogger(__name__).exception("PDF report unavailable")
        return None


def _runner(inputs: dict, scenario: str) -> dict:
    return D.run_all(inputs)


def _reset_button(base: dict) -> None:
    # a callback runs before the next run draws the form, so the form's values can still be changed
    st.button(C.RESET, icon=":material/restart_alt:", key="reset_btn", on_click=_reset, args=(base,))


def _show(res, scenario: str) -> None:
    v = logic.live_cards(res)
    labels = C.KPI_YOURS
    bal = np.median(res.cum_net, axis=0)
    spark = {"cost": K.sparkline_svg(np.median(res.total_cost, axis=0), T.tok("accent")),
             "benefit": K.sparkline_svg(np.median(res.value, axis=0), T.tok("accent-2")),
             "balance": K.sparkline_svg(bal, T.tok("warm") if bal[-1] < 0 else T.tok("good"), zero=True), "payback": ""}
    K.kpi_row([K.kpi_card(labels[k], v[k], C.KPI_YOURS_MEANING[k], spark[k], icon_name=k, i=n,
                          tone="warm" if k == "balance" and bal[-1] < 0 else "")
               for n, k in enumerate(("cost", "benefit", "balance", "payback"))])
    K.verdict(logic.verdict(v["prob"], v["p50"], res.meta["T"]))
    c1, c2 = st.columns([3, 2])
    with c1:
        K.chart(charts.balance_band(res.cum_net, T.outlook_color(scenario), C.OUTLOOK_CHART_TITLE_YOURS),
                "company_balance", "my_running_balance")
        K.insight_row(*EX.company_balance(v, res.meta["T"], float(bal[-1])), stacked=True)
    with c2:
        shares = logic.live_shares(res)
        K.chart(charts.donut(shares), "company_donut", "my_cost_split")
        K.insight_row(*EX.donut(shares, "company_donut"), stacked=True)
    bundle, yours = st.session_state.get("co_bundle"), D.yours() is not None
    with st.container(horizontal=True, key="co_downloads"):
        st.download_button(C.DOWNLOAD, D.monthly_result_table(res).to_csv(index=False).encode("utf-8-sig"),
                           file_name="my_results.csv", mime="text/csv", icon=":material/download:")
        pdf = _pdf_module() if bundle is not None else None
        if pdf is not None:
            # made only when clicked (on its own thread), from the values captured here
            st.download_button(C.PDF_DOWNLOAD, lambda: pdf.build(res, scenario, bundle, yours),
                               file_name="my_results_report.pdf", mime="application/pdf",
                               icon=":material/picture_as_pdf:", key="pdf_btn", on_click="ignore")
        elif bundle is not None:
            st.caption(C.PDF_UNAVAILABLE)


def render() -> None:
    K.page_header(C.HEAD["company"], C.COMPANY_NOTE, C.PAGES["company"][0])
    try:
        base, _ = D.example_inputs()
        outlooks = D.outlooks()
    except D.Missing:
        K.empty_state()
        return
    _init(base)
    pressed = _form(outlooks)
    _reset_button(base)
    if pressed or "co_result" not in st.session_state:
        form = {f: st.session_state[f"co_{f}"] for row in LAYOUT for f in row}
        scenario = next(s for s in outlooks if C.OUTLOOK[s] == st.session_state["co_outlook"])
        try:
            with st.spinner(C.WORKING):
                bundle, msgs = logic.submit(base, form, scenario, _runner)
        except D.Missing:
            bundle, msgs = None, [C.MISSING]
        if bundle is None:
            for m in msgs:
                st.warning(m, icon=":material/edit:")
        else:
            st.session_state["co_result"] = (bundle["runs"][(scenario, 1.0)], scenario)
            slim = {k: bundle[k] for k in ("tables", "payback", "inputs")}
            st.session_state["co_bundle"] = slim
            was = D.yours() is not None
            mine = pressed and not _same(bundle["inputs"], base)
            if mine:
                st.session_state[D.YOURS_KEY] = slim
            else:
                st.session_state.pop(D.YOURS_KEY, None)
            if mine or was:
                st.rerun()  # redraw the banner, the side panel and the headline for the new figures
    if "co_result" in st.session_state:
        _show(*st.session_state["co_result"])


render()
