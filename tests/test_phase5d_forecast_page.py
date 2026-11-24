"""Phase 5D, step C: the 'What we expect next' page. Every number on it is recomputed here from the saved files;
the divider at the latest real value is drawn; the download holds exactly what the chart shows."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard import charts, charts_forecast  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, _page_text  # noqa: E402
from test_phase5d_loaders import FC_DIR, P3, SEVEN, needs  # noqa: E402

CASES = [(s, n) for s in SEVEN for n in {"eci_wages_quarterly": (4, 8), "ppi_hosting_monthly": (3, 6, 12),
                                          "burst_requests_hourly": (24, 72, 168)}.get(s, (7, 14))]


def _saved(name: str, n: int) -> tuple[float, float, float]:
    """Expected value and 10th / 90th percentile at step n, straight from the saved forecast file."""
    fc = pd.read_csv(FC_DIR / f"{name}.csv")
    step = fc[fc["period_index"] == n]
    sims = step.loc[step["sample_id"] >= 0, "value"].to_numpy()
    return float(step.loc[step["sample_id"] == -1, "value"].iloc[0]), float(np.quantile(sims, .1)), float(np.quantile(sims, .9))


def _view(name: str, n: int) -> dict:
    return LF.forecast_view(name, n, D.history(name), D.saved_forecast(name), pd.read_csv(P3 / "interval_check.csv"))


@needs
@pytest.mark.parametrize("name,n", CASES)
def test_numbers_in_words_are_the_saved_ones(name, n):
    v = _view(name, n)
    e, lo, hi = _saved(name, n)
    unit = C.SERIES[name][2]
    assert v["headline"].endswith(f"about {LF.amount(e, unit)} {unit}.")
    assert v["range"] == C.FORECAST_RANGE.format(low=LF.amount(lo, unit), high=LF.amount(hi, unit))
    last = float(D.history(name)["value"].iloc[-1])
    assert LF.amount(last, unit) in v["change"]
    assert LF.change_text(e / last - 1) in v["change"]
    t = v["table"]
    assert len(t) == n
    assert t[C.EXPECT_COLS["expected"]].iloc[-1] == pytest.approx(e, abs=0.01 if unit == "points" else 0.5)
    assert t[C.EXPECT_COLS["low"]].iloc[-1] == pytest.approx(lo, abs=0.01 if unit == "points" else 0.5)
    assert t[C.EXPECT_COLS["high"]].iloc[-1] == pytest.approx(hi, abs=0.01 if unit == "points" else 0.5)
    for s in (v["headline"], v["range"], v["change"], *t[C.EXPECT_COLS["when"]]):
        assert not BANNED_RE.search(s), s


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_chart_draws_saved_values_and_marks_the_latest_real_value(name):
    fc = pd.read_csv(FC_DIR / f"{name}.csv")
    n = int(fc["period_index"].max())
    v = _view(name, n)
    fig = charts_forecast.series_chart(v["chart"])
    lines = {tr.name: tr for tr in fig.data if tr.mode == "lines"}
    central = fc[fc["sample_id"] == -1].sort_values("period_index")["value"].to_numpy()
    assert np.allclose(np.asarray(lines[C.LEGEND_EXPECT].y[1:], float), central)
    hist = D.history(name)
    window = LF.HISTORY_WINDOW[LF.grain(fc)]
    assert np.allclose(np.asarray(lines[C.LEGEND_HAPPENED].y, float), hist["value"].tail(window).to_numpy())
    assert lines[C.LEGEND_EXPECT].y[0] == pytest.approx(hist["value"].iloc[-1])  # future grows out of the last value
    assert lines[C.LEGEND_EXPECT].line.dash == "dash"
    assert any(C.LAST_REAL in str(a.text) for a in fig.layout.annotations)
    assert fig.layout.shapes[0].x0 == lines[C.LEGEND_HAPPENED].x[-1]
    assert not BANNED_RE.search(charts.text_of(fig).replace("customdata", ""))
    tips = " ".join(str(x) for tr in fig.data for x in (tr.customdata if tr.customdata is not None else []))
    assert not BANNED_RE.search(tips)


@needs
def test_range_check_note_uses_phase3_counts():
    ic = pd.read_csv(P3 / "interval_check.csv")
    for name in SEVEN:
        v = _view(name, 7 if "daily" in name else 4 if "quarterly" in name else 3 if "monthly" in name else 24)
        row = ic[(ic["driver"] == name) & (ic["segment"] == "all")].iloc[0]
        assert v["hits"] == (int(round(row["coverage_80_after"] * row["n_holdout_points"])), int(row["n_holdout_points"]))
        assert v["flag"] is bool(row["flag"])


def _page(state: dict) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, val in state.items():
        at.session_state[k] = val
    at.run()
    at.switch_page("views/forecast.py")
    at.run()
    return at


@needs
@pytest.mark.parametrize("name,n", [("ppi_hosting_monthly", 12), ("burst_tokens_chat_daily", 7),
                                    ("wildchat_conversations_daily", 14), ("eci_wages_quarterly", 4)])
def test_page_shows_the_view_and_offers_the_same_numbers_to_download(name, n):
    at = _page({"fc_series": name, f"fc_len_{name}": n})
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("plotly_chart")) == 1
    v = _view(name, n)
    md = " ".join(str(m.value) for m in at.markdown)
    for s in (v["headline"], v["range"], v["change"], C.RANGE_NOTE):
        assert s in md, s
    inside, total = v["hits"]
    assert (C.RANGE_WARN if v["flag"] else C.RANGE_OK).format(inside=inside, n=total) in md
    if not v["dated"]:
        assert C.NO_DATES in md
    text = _page_text(at)
    hit = BANNED_RE.search(text)
    assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]
    dl = at.get("download_button")
    assert len(dl) == 1 and C.DOWNLOAD_EXPECT in str(dl[0].proto)


@needs
def test_default_trend_matches_the_welcome_chart():
    at = _page({})
    md = " ".join(str(m.value) for m in at.markdown)
    d = LF.hosting_hero(D.processed(LF.HOSTING[0]), D.saved_forecast(LF.HOSTING[0]))
    assert f"By Oct 2027 we expect about {LF.level(d['expected'][-1])} points." in md
    assert C.FORECAST_RANGE.format(low=LF.level(d["low"][-1]), high=LF.level(d["high"][-1])) in md


def test_change_words():
    assert LF.change_text(0.0147) == "+1.5%" and LF.change_text(-0.31) == "-31%"
    assert LF.change_text(0.001) == C.SAME and LF.change_text(float("nan")) == C.SAME
