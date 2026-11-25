"""Analyst mode (off by default) adds the technical sections to the Data and Reliability pages for every trend,
read from artifacts/; with it off, the pages stay plain."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.ui import copy_technical as CT

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "src" / "dashboard" / "app.py")
SEVEN = ["eci_wages_quarterly", "ppi_hosting_monthly", "burst_tokens_total_daily", "burst_tokens_api_daily",
         "burst_tokens_chat_daily", "burst_requests_hourly", "wildchat_conversations_daily"]
needs = pytest.mark.skipif(not (ROOT / "artifacts" / "conformal.json").exists(), reason="artifacts/ not built")


def _run(page: str, name: str, analyst: bool) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["trend"] = name
    at.session_state["aiwi_analyst"] = analyst
    at.run()
    at.switch_page(page)
    at.run()
    return at


def _text(at) -> str:
    return " ".join(str(m.value) for m in at.markdown)


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_data_page_analyst_section(name):
    at = _run("app_pages/data_used.py", name, True)
    assert not at.exception, [e.value for e in at.exception]
    t = _text(at)
    assert CT.ANALYST_DATA_TITLE in t and "ADF p =" in t and "Unusual points" in t


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_reliability_page_analyst_section(name):
    at = _run("app_pages/reliability.py", name, True)
    assert not at.exception, [e.value for e in at.exception]
    t = _text(at)
    assert CT.ANALYST_REL_TITLE in t and "the 80% range held" in t
    assert len(at.dataframe) >= 2  # model cards and the cross-validation table


@needs
def test_off_by_default():
    at = _run("app_pages/reliability.py", "ppi_hosting_monthly", False)
    assert CT.ANALYST_REL_TITLE not in _text(at)


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_rolling_origin_coverage_of_the_80_range_is_honest(name):
    import json
    c = json.loads((ROOT / "artifacts" / "conformal.json").read_text(encoding="utf-8"))[name]
    assert 0.70 <= c["coverage"]["0.8"] <= 0.90, c["coverage"]["0.8"]
