"""Phase 5D, step E: 'The data we used'. Tiles equal Phase 1's summary table; the day-number note shows for sources
without dates; unusual points, the known outage, the repeating pattern and the plain summary are recomputed here
from the saved files; the page stays plain."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import charts, charts_forecast  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, _page_text  # noqa: E402
from test_phase5d_loaders import FC_DIR, P1, SEVEN, needs  # noqa: E402
from test_phase5d_reliability import TECH_RE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UNDATED = ["burst_tokens_total_daily", "burst_tokens_api_daily", "burst_tokens_chat_daily", "burst_requests_hourly"]


def _view(name: str) -> dict:
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    return LF.data_view(name, D.history(name), g, D.source_points(name), pd.read_csv(P1 / "anomalies.csv"),
                        pd.read_csv(P1 / "decomposition.csv"))


def _label(raw, grain: str) -> str:
    """Independent label of a Phase 1 start/end value."""
    s = str(raw)
    if s.isdigit():
        return {"day": "Day {}", "hour": "Hour {}"}[grain].format(f"{int(s) + 1:,}")
    t = pd.Timestamp(s)
    return {"quarter": f"Q{t.quarter} {t.year}", "month": t.strftime("%b %Y"),
            "day": f"{t.day} {t.strftime('%b %Y')}"}[grain]


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_tiles_equal_phase1_summary(name):
    stats = pd.read_csv(P1 / "summary_stats.csv").set_index("driver").loc[name]
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    v = _view(name)
    span, count, unusual, missing = (t[1] for t in v["tiles"])
    assert span == f"{_label(stats['start'], g)} to {_label(stats['end'], g)}"
    one, many = C.GRAIN_WORD[g]
    assert count == f"{int(stats['n']):,} {many}"
    an = pd.read_csv(P1 / "anomalies.csv")
    k = int(((an["driver"] == name) & an["value"].notna()).sum())
    assert unusual == (f"{k:,}" if k else C.NONE)
    assert missing == (C.NONE if int(stats["n_nan"]) == 0 else f"{int(stats['n_nan']):,}")


@needs
def test_check_notes_are_not_counted_as_unusual_points():
    v = _view("burst_tokens_total_daily")  # Phase 1 holds only a note about its day-77 check for this series
    assert v["unusual_n"] == 0 and v["tiles"][2][1] == C.NONE
    assert LF.series_facts(D.history("burst_tokens_total_daily"), "burst_tokens_total_daily", "day",
                           pd.read_csv(P1 / "anomalies.csv"))["unusual"] == 0


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_page_shows_the_notes_and_stays_plain(name):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["trend"] = name
    at.run()
    at.switch_page("app_pages/data_used.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    page_dl = [b for b in at.get("download_button") if C.DOWNLOAD_CSV not in str(b.proto)]  # charts add their own
    chart_dl = [b for b in at.get("download_button") if C.DOWNLOAD_CSV in str(b.proto)]
    assert len(at.get("plotly_chart")) == 2 and len(at.tabs) == 3 and len(page_dl) == 1 and len(chart_dl) == 2
    v = _view(name)
    md = " ".join(str(m.value) for m in at.markdown)
    assert (C.NO_DATES in md) == (name in UNDATED)  # the day-number note for sources without dates
    assert v["window"] in md and v["summary"] in md
    if name.startswith("burst"):
        assert v["outage"] and v["outage"] in md
    for label, value, _ in v["tiles"]:
        assert label in md and value in md
    text = _page_text(at)
    for regex in (BANNED_RE, TECH_RE):
        hit = regex.search(text)
        assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]


@needs
def test_window_notes_use_the_real_counts():
    wide = pd.read_csv(ROOT / "data" / "processed" / "burstgpt_daily_wide.csv")
    assert D.source_points("burst_tokens_total_daily") == int(wide["total_tokens"].notna().sum())
    v = _view("burst_tokens_total_daily")
    assert v["window"] == C.WINDOW_NOTE["burst"].format(n=87, source=f"{int(wide['total_tokens'].notna().sum()):,}", grains="days")
    for name in ("eci_wages_quarterly", "ppi_hosting_monthly"):  # dated official series: every value is used
        assert D.source_points(name) == len(D.history(name))
        assert _view(name)["window"] == C.WINDOW_NOTE["full"].format(n=f"{len(D.history(name)):,}")
    for name in UNDATED + ["wildchat_conversations_daily"]:
        assert D.source_points(name) > len(D.history(name))


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_chart_pattern_and_summary_are_recomputed(name):
    h = D.history(name)
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    v = _view(name)
    fig = charts_forecast.data_chart(v["chart"])
    by = {tr.name: tr for tr in fig.data}
    assert np.allclose(np.asarray(by[C.LEGEND_HAPPENED].y, float), h["value"])
    an = pd.read_csv(P1 / "anomalies.csv")
    an = an[(an["driver"] == name) & an["value"].notna()]
    if len(an):
        assert np.allclose(np.asarray(by[C.MARK_UNUSUAL].y, float), an["value"].astype(float))
    else:
        assert C.MARK_UNUSUAL not in by
    if name.startswith("burst"):
        assert C.MARK_OUTAGE in by  # the known one-day outage (preprocessing flag) is marked
    s = LF.SEASON[g]
    first, last = h["value"].head(s).mean(), h["value"].tail(s).mean()
    unit = C.SERIES[name][2]
    assert f"about {LF.amount(first, unit)} {unit}" in v["summary"] and f"about {LF.amount(last, unit)} {unit}" in v["summary"]
    d = pd.read_csv(P1 / "decomposition.csv").set_index("driver").loc[name]
    word = lambda x: "strong" if x >= 0.6 else "some" if x >= 0.3 else "little"  # noqa: E731
    assert f"Long-term trend: {word(d['trend_strength'])}." in v["summary"]
    assert v["summary"].endswith(f"pattern: {word(d['seasonal_strength'])}.")
    # repeating pattern: plain averages of the real values per place in the cycle
    if LF.has_dates(h["x"].iloc[0]):
        t = pd.to_datetime(h["x"])
        key = {"month": t.dt.month, "quarter": t.dt.quarter, "day": t.dt.weekday}[g]
    else:
        key = h["x"].astype(int) % s
    want = h.groupby(key.to_numpy())["value"].mean().sort_index()
    assert np.allclose(v["pattern"]["values"], want.to_numpy())
    pfig = charts_forecast.pattern_chart(v["pattern"])
    for text in [charts.text_of(fig), charts.text_of(pfig), *pfig.data[0].customdata, *v["pattern"]["labels"]]:
        assert not BANNED_RE.search(text) and not TECH_RE.search(text), text
    dl = v["download"]
    assert len(dl) == len(h) and np.allclose(dl[C.DATA_COLS["value"]], h["value"])


@needs
def test_unusual_table_lists_the_most_unusual_first():
    v = _view("burst_requests_hourly")
    assert v["unusual_n"] == 394
    an = pd.read_csv(P1 / "anomalies.csv").query("driver == 'burst_requests_hourly'")
    top = an.reindex(an["robust_z"].abs().sort_values(ascending=False).index).iloc[0]
    assert v["unusual"].iloc[0][C.UNUSUAL_COLS["when"]] == f"Hour {int(float(top['time'])) + 1:,}"
    assert v["unusual"].iloc[0][C.UNUSUAL_COLS["side"]] == (C.UNUSUAL_SIDE["high"] if top["robust_z"] > 0 else C.UNUSUAL_SIDE["low"])


def test_strength_words():
    assert [LF.strength_word(x) for x in (0.99, 0.6, 0.45, 0.3, 0.1, 0.0, float("nan"), None)] == \
           ["strong", "strong", "some", "some", "little", "little", "little", "little"]
