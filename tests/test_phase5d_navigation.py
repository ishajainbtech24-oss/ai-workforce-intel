"""Phase 5D, step A: Welcome page, menu groups and "Next" cards. Numbers on the Welcome page come from the saved
files; the likely range is the 10th to 90th percentile of the saved simulated futures; wording stays plain."""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from dashboard.ui import charts, charts_forecast, components  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import BANNED_RE, TABLES, _money, _page_text, _run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "outputs" / "phase3" / "forecasts" / "ppi_hosting_monthly.csv"
HIST = ROOT / "data" / "processed" / "ppi_hosting_monthly.csv"
needs_files = pytest.mark.skipif(not (FC.exists() and HIST.exists() and (TABLES / "totals_summary.csv").exists()),
                                 reason="saved forecast, processed series or Phase 4 tables missing")


def _hero() -> dict:
    return LF.hosting_hero(pd.read_csv(HIST), pd.read_csv(FC))


@needs_files
def test_likely_range_is_the_10th_to_90th_percentile_of_the_saved_futures():
    fc = pd.read_csv(FC)
    got = LF.expected_and_range(fc)
    sims = fc[fc["sample_id"] >= 0]
    assert sims["sample_id"].nunique() == 200
    for step, row in got.set_index("period_index").iterrows():
        v = sims.loc[sims["period_index"] == step, "value"].to_numpy()
        assert row["low"] == pytest.approx(np.quantile(v, 0.10))
        assert row["high"] == pytest.approx(np.quantile(v, 0.90))
    central = fc[fc["sample_id"] == -1].sort_values("period_index")["value"].to_numpy()
    assert np.allclose(got["expected"].to_numpy(), central)
    assert len(got) == 12  # the one saved length for this series; nothing longer is invented


@needs_files
def test_welcome_chart_draws_the_saved_values():
    d = _hero()
    h = pd.read_csv(HIST).dropna(subset=["ppi_hosting"]).tail(36)
    assert d["hist_values"] == pytest.approx(list(h["ppi_hosting"]))
    fig = charts_forecast.history_forecast(d, C.WELCOME_CHART_TITLE)  # title is optional; the page shows it as text
    by_name = {tr.name: tr for tr in fig.data if tr.mode == "lines"}
    assert list(by_name[C.LEGEND_EXPECT].y[1:]) == pytest.approx(d["expected"])
    assert list(by_name[C.LEGEND_HAPPENED].y) == pytest.approx(d["hist_values"])
    assert by_name[C.LEGEND_EXPECT].line.dash == "dash"
    assert any(C.TODAY in str(a.text) for a in fig.layout.annotations)
    assert d["fc_dates"][0] > d["hist_dates"][-1]  # the future starts after the last real value
    assert not BANNED_RE.search(charts.text_of(fig).replace("customdata", ""))
    assert not BANNED_RE.search(" ".join(str(x) for x in by_name[C.LEGEND_EXPECT].customdata))


@needs_files
def test_welcome_page_shows_real_numbers_and_plain_words():
    at = _run()  # Welcome is the first page
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("plotly_chart")) == 1
    html = " ".join(str(m.value) for m in at.markdown)
    assert C.BANNER in html and "welcome-title" in html and C.WELCOME_CHART_TITLE in html
    tot = pd.read_csv(TABLES / "totals_summary.csv").query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    for v in (_money(tot["total_cost_p50"]), _money(tot["total_value_p50"])):
        assert v in html, v
    be = pd.read_csv(TABLES / "break_even_summary.csv").query("multiplier == 1.0").set_index("scenario")
    if be.loc["expected", "prob_break_even_within_T"] < 0.5:
        assert f"Not within {int(be.loc['expected', 'T'])} months" in html
        if be.loc["optimistic", "prob_break_even_within_T"] >= 0.5:
            assert C.WELCOME_PAYS_NOTE.format(month=int(be.loc["optimistic", "p50_month"])) in html
    d = _hero()
    note = C.WELCOME_CHART_NOTE.format(value=f"{d['expected'][-1]:.1f}", end=pd.Timestamp(d["fc_dates"][-1]).strftime("%b %Y"),
                                       low=f"{d['low'][-1]:.1f}", high=f"{d['high'][-1]:.1f}")
    assert note in html
    text = _page_text(at)
    hit = BANNED_RE.search(text)
    assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]
    assert not re.search(r"\b(nan|None)\b", text)


def test_next_cards_walk_every_page_in_order():
    order, key = [], "welcome"
    while key in C.NEXT:
        order.append(key)
        key = C.NEXT[key][0]
    order.append(key)
    assert order == ["welcome", "overview", "data", "forecast", "reliable", "costs", "timing", "levers", "company"]
    assert set(order) == set(components.PAGE_FILES) == set(C.PAGES)
    for k, path in components.PAGE_FILES.items():
        assert (ROOT / "src" / "dashboard" / path).exists(), path
    for _, line in C.NEXT.values():
        assert not BANNED_RE.search(line)


def test_menu_groups_are_declared_in_the_app():
    app = (ROOT / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert 'C.SECTION_MONEY: ["costs", "timing", "levers"]' in app and 'C.SECTION_FORECASTS: ["data", "forecast", "reliable"]' in app
    assert 'default=(key == "welcome")' in app


def test_missing_forecast_file_gives_the_friendly_message(tmp_path, monkeypatch):
    monkeypatch.setenv("TSAF_DASH_ROOT", str(tmp_path))
    with pytest.raises(D.Missing):
        D.saved_forecast("ppi_hosting_monthly")
    with pytest.raises(D.Missing):
        D.processed("ppi_hosting_monthly")


def test_no_pages_folder_next_to_the_app():
    """A folder called `pages` beside app.py switches Streamlit into its old page-folder mode: the first visitor who
    opens a page address directly (before anyone opens /) gets that page alone, without the styles, the banner, the
    top bar or the Next card. The page files therefore live in `app_pages/`."""
    here = ROOT / "src" / "dashboard"
    assert not (here / "pages").exists()
    assert all(path.startswith("app_pages/") for path in components.PAGE_FILES.values())
