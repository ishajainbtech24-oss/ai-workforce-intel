"""The visitor's own figures across the site, and the PDF report.

- data.run_all builds the same tables Phase 4 saved (same engine, futures and settings): with the example company's
  inputs it gives the saved tables back;
- after Update with different figures, every results page reads the visitor's tables (numbers, headline, banner,
  side-panel note); 'Back to the example', 'Reset to example' and a new session (a page refresh) bring the example
  back; Update with the example's own figures changes nothing;
- the PDF report is a real five-page PDF built from the same run, for the example and for other figures.
"""
import datetime
import re

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("matplotlib")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.ui import report_pdf as PDF  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

from test_phase5_dashboard import APP, TABLES  # noqa: E402
from test_phase5d_loaders import needs  # noqa: E402

OTHER = {"employees": 1200, "realisation_rate": 0.7}  # a company that pays back within the year


def _inputs(**change) -> dict:
    base, _ = D.example_inputs()
    return {**base, **change}


@needs
def test_run_all_with_the_example_gives_the_saved_tables_back():
    got = D.run_all(_inputs())["tables"]
    for name, keys in (("totals_summary", ["scenario", "multiplier"]), ("break_even_summary", ["scenario", "multiplier"]),
                       ("cost_breakdown", ["scenario", "multiplier", "line"]),
                       ("monthly_summary", ["scenario", "multiplier", "line", "month"]), ("sensitivity", ["input"])):
        saved = pd.read_csv(TABLES / f"{name}.csv").sort_values(keys).reset_index(drop=True)
        mine = got[name].sort_values(keys).reset_index(drop=True)
        assert list(mine.columns) == list(saved.columns), name
        num = [c for c in saved.columns if pd.api.types.is_numeric_dtype(saved[c])]
        assert np.allclose(mine[num].to_numpy(float), saved[num].to_numpy(float), rtol=1e-6, equal_nan=True), name


@needs
def test_payback_counts_follow_the_runs():
    b = D.run_all(_inputs(**OTHER))
    counts, none, total = b["payback"][("expected", 1.0)]
    be = b["tables"]["break_even_summary"].query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    assert total == 5000 and sum(counts) + none == total
    assert sum(counts) / total == pytest.approx(be["prob_break_even_within_T"])


def _company(at: AppTest, **change) -> AppTest:
    at.switch_page("app_pages/your_company.py")
    at.run()
    for f, v in change.items():
        box = at.slider(key=f"co_{f}") if f in ("realisation_rate", "adoption_target") else at.number_input(key=f"co_{f}")
        box.set_value(round(v * 100) if f in logic.PCT_FIELDS else v)
    next(b for b in at.button if b.label == C.UPDATE).click()
    at.run()
    return at


def _text(at: AppTest) -> str:
    return " ".join(str(m.value) for m in at.markdown)


@needs
def test_own_figures_show_on_every_results_page_until_back_to_the_example():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    _company(at, **OTHER)
    assert not at.exception, [e.value for e in at.exception]
    mine = D.run_all(_inputs(**OTHER))["tables"]
    tot = mine["totals_summary"].query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    saved = pd.read_csv(TABLES / "totals_summary.csv").query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    assert T.money(tot["total_cost_p50"]) != T.money(saved["total_cost_p50"])
    for page in ("app_pages/welcome.py", "app_pages/overview.py", "app_pages/costs.py", "app_pages/timing.py", "app_pages/levers.py"):
        at.switch_page(page)
        at.run()
        assert not at.exception, (page, [e.value for e in at.exception])
        text = _text(at)
        assert C.YOURS["BANNER"] in text and C.YOURS["EXAMPLE_PILL"] in text and C.BANNER not in text, page
        assert C.SIDE_YOURS in text, page
    at.switch_page("app_pages/overview.py")
    at.run()
    text = _text(at)
    assert T.money(tot["total_cost_p50"]) in text and T.money(tot["cum_net_T_p50"]) in text
    assert "At your figures" in text
    # Back to the example (side panel): the example everywhere again
    at.button(key="yours_back").click().run()
    text = _text(at)
    assert C.BANNER in text and C.SIDE_YOURS not in text
    assert T.money(saved["total_cost_p50"]) in text and "At the example figures" in text
    assert D.YOURS_KEY not in at.session_state


@needs
def test_reset_and_a_new_session_bring_the_example_back():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    _company(at, **OTHER)
    assert C.YOURS["BANNER"] in _text(at)
    at.button(key="reset_btn").click().run()
    assert C.BANNER in _text(at) and D.YOURS_KEY not in at.session_state
    _company(at, **OTHER)
    fresh = AppTest.from_file(APP, default_timeout=240)  # a page refresh starts a new session
    fresh.switch_page("app_pages/overview.py")
    fresh.run()
    assert C.BANNER in _text(fresh) and C.YOURS["BANNER"] not in _text(fresh)


@needs
def test_update_with_the_example_figures_keeps_the_example():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    _company(at)
    assert not at.exception, [e.value for e in at.exception]
    assert D.YOURS_KEY not in at.session_state and C.BANNER in _text(at)


@needs
def test_company_page_offers_the_table_and_the_pdf():
    at = AppTest.from_file(APP, default_timeout=240)
    at.switch_page("app_pages/your_company.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [b.proto.label for b in at.get("download_button") if b.proto.label != C.DOWNLOAD_CSV]  # charts add their own
    assert labels == [C.DOWNLOAD, C.PDF_DOWNLOAD, C.DOWNLOAD_XLSX, C.SCENARIO_SAVE]


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf))


@needs
@pytest.mark.parametrize("change,yours", [({}, False), (dict(OTHER, horizon_months=18), True)])
def test_pdf_report_is_a_five_page_pdf(change, yours):
    b = D.run_all(_inputs(**change))
    res = b["runs"][("expected", 1.0)]
    pdf = PDF.build(res, "expected", b, yours, datetime.date(2026, 11, 24))
    assert pdf.startswith(b"%PDF") and pdf.rstrip().endswith(b"%%EOF")
    assert _pages(pdf) == PDF.PAGES == 5
    assert 20_000 < len(pdf) < 2_000_000
    assert C.PDF_FOR["yours" if yours else "example"].split(" (")[0].encode() in pdf  # subject line (PDF escapes brackets)


def test_wording_falls_back_to_the_example_outside_a_session():
    assert logic.words("BANNER") == C.BANNER and logic.words("PRODUCT") == C.PRODUCT
    assert set(C.YOURS) <= set(vars(C))
