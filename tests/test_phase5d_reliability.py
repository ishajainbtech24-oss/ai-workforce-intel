"""Phase 5D, step D: 'How reliable it is'. The ranking follows the saved leaderboard (approaches that ran, by average
miss over the earlier checks); every number is recomputed from the saved Phase 2 and 3 tables; no approach name,
metric abbreviation or other technical word reaches the screen."""
import html
import re

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import charts, charts_forecast  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import artifacts as A  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, _page_text  # noqa: E402
from test_phase5d_loaders import FC_DIR, P2, P3, SEVEN, needs  # noqa: E402

TECH = ["arima", "sarima", "sarimax", "holt", "damped_holt", "hw_additive", "hw_multiplicative", "ensemble", "naive",
        "seasonal_naive", "seasonal_ma3", "moving_average", "prophet", "lstm", "xgboost", "ridge", "random_forest",
        "ses", "drift", "mae", "rmse", "mape", "smape", "mase", "cv", "holdout", "backtest", "leaderboard",
        "confidence interval", "seasonality", "stationarity", "p10", "p90", "quantile", "fold"]
TECH_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in TECH) + r")\b", re.IGNORECASE)


def _view(name: str) -> dict:
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    return LF.reliability_view(name, D.history(name), g, pd.read_csv(P2 / "chosen_models.csv"),
                               pd.read_csv(P2 / "holdout.csv"), pd.read_csv(P3 / "interval_check.csv"),
                               pd.read_csv(P2 / "leaderboard.csv"), A.cal(name))


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_ranking_follows_the_saved_leaderboard(name):
    lb = pd.read_csv(P2 / "leaderboard.csv")
    ok = lb[(lb["driver"] == name) & (lb["status"] == "ok")].sort_values(["cv_mae", "model"])
    v = _view(name)
    assert list(v["ranking"]["approach"]) == list(ok["model"])
    assert np.allclose(v["ranking"]["average_miss"], ok["cv_mae"])
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    fig = charts_forecast.ranking_chart(v["ranking"], v["unit"], show_all=True)
    bar = fig.data[0]
    assert [y.replace("<br>", " ") for y in bar.y] == [
        LF.approach_label(m, g) + (f" ({C.RANK_USED})" if m == v["approach"] else f" ({C.RANK_REFERENCE})"
                                   if m == C.REFERENCE_APPROACH else "") for m in ok["model"]]
    assert np.allclose(bar.x, ok["cv_mae"])
    assert fig.layout.yaxis.autorange == "reversed"  # closest at the top
    short = charts_forecast.ranking_chart(v["ranking"], v["unit"], show_all=False)
    ys = [y.replace("<br>", " ") for y in short.data[0].y]
    assert len(ys) <= charts_forecast.RANK_ROWS + 2
    assert any(f"({C.RANK_REFERENCE})" in y for y in ys) and any(f"({C.RANK_USED})" in y for y in ys)
    skipped = int(((lb["driver"] == name) & (lb["status"] != "ok")).sum())
    assert (C.RANK_SKIPPED.format(k=skipped) in v["notes"]) == (skipped > 0)
    for text in ys + list(bar.customdata) + [charts.text_of(fig)]:
        assert not TECH_RE.search(text) and not BANNED_RE.search(text), text


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_numbers_are_the_saved_ones(name):
    chosen = pd.read_csv(P2 / "chosen_models.csv").set_index("driver").loc[name, "chosen_model"]
    hold = pd.read_csv(P2 / "holdout.csv")
    h = hold[(hold["driver"] == name) & (hold["model"] == chosen)]
    v = _view(name)
    assert v["approach"] == chosen
    assert v["miss"] == pytest.approx(float(h["holdout_mae"].iloc[0]), rel=1e-6)
    assert v["level"] == pytest.approx(float(h["actual"].mean()))
    assert v["first_inside"] == int(((h["actual"] >= h["lo80"]) & (h["actual"] <= h["hi80"])).sum())
    c = A.conformal(name)  # the calibrated range and its rolling check replace the Phase 3 hold-out counts
    assert v["hits"] is None
    assert v["flag"] is (not 0.7 <= c["coverage"]["0.8"] <= 0.9)
    lb = pd.read_csv(P2 / "leaderboard.csv").query("driver == @name and status == 'ok'").set_index("model")["cv_mae"]
    assert v["vs_reference"] == pytest.approx(1 - lb[chosen] / lb["seasonal_naive"])
    unit = C.SERIES[name][2]
    assert f"{LF.amount(v['miss'], unit)} {unit}" == v["tiles"][0][1]
    assert v["tiles"][1][1] == LF.pct(c["coverage"]["0.8"])
    assert v["tiles"][1][2] == C.TILE_INSIDE_CAL.format(pts=c["scored_points"])


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_past_check_chart_draws_the_saved_predictions(name):
    chosen = pd.read_csv(P2 / "chosen_models.csv").set_index("driver").loc[name, "chosen_model"]
    hold = pd.read_csv(P2 / "holdout.csv")
    h = hold[(hold["driver"] == name) & (hold["model"] == chosen)].sort_values("step_ahead")
    v = _view(name)
    fig = charts_forecast.past_check_chart(v["chart"])
    by = {tr.name: tr for tr in fig.data}
    assert np.allclose(np.asarray(by[C.LEGEND_PREDICTED].y, float), h["forecast"])
    assert np.allclose(np.asarray(by[C.LEGEND_REAL].y, float)[-len(h):], h["actual"])
    assert by[C.LEGEND_PREDICTED].line.dash == "dot"
    inside = int(((h["actual"] >= h["lo80"]) & (h["actual"] <= h["hi80"])).sum())
    got_in = len(by[C.LEGEND_INSIDE].x) if C.LEGEND_INSIDE in by else 0
    got_out = len(by[C.LEGEND_OUTSIDE].x) if C.LEGEND_OUTSIDE in by else 0
    assert (got_in, got_out) == (inside, len(h) - inside)
    assert any(C.PREDICTED_HERE in str(a.text) for a in fig.layout.annotations)
    for t in list(by[C.LEGEND_REAL].customdata) + [charts.text_of(fig)]:
        assert not TECH_RE.search(t) and not BANNED_RE.search(t), t


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_page_is_plain_for_every_trend(name):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["trend"] = name
    at.session_state[f"rel_all_{name}"] = True
    at.run()
    at.switch_page("app_pages/reliability.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("plotly_chart")) == 2
    v = _view(name)
    md = " ".join(str(m.value) for m in at.markdown)
    for s in [v["verdict"], *[x for t in v["tiles"] for x in t], *v["notes"]]:
        assert html.escape(s) in md or s in md, s
    text = _page_text(at)
    for regex in (BANNED_RE, TECH_RE):
        hit = regex.search(text)
        assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]


def test_plain_names_for_every_grain_read_naturally():
    assert LF.approach_label("seasonal_naive", "hour") == "Repeat the same hour the day before"
    assert LF.approach_label("seasonal_ma3", "day") == "Average of the same weekday in the last three weeks"
    for g in ("hour", "day", "month", "quarter"):
        for key in C.APPROACH:
            assert not TECH_RE.search(LF.approach_label(key, g)), (key, g)
    for s in (C.RELIABLE_SUB, C.RELIABLE_VERDICT, C.RANK_SUB, C.RANK_CLOSE, C.RANK_NOT_FIRST, C.RANK_SKIPPED,
              C.HOW_TO_READ["reliable"], *C.TILE_MISS, *C.TILE_INSIDE, *C.TILE_VS):
        assert not TECH_RE.search(s) and not BANNED_RE.search(s), s


@needs
def test_bands_draw_no_stray_markers():
    """Plotly adds markers to short traces unless told otherwise; the shaded ranges must be bands only."""
    name = "ppi_hosting_monthly"
    v = _view(name)
    past = charts_forecast.past_check_chart(v["chart"])
    fc = LF.forecast_view(name, 3, D.history(name), D.saved_forecast(name), pd.read_csv(P3 / "interval_check.csv"))
    ahead = charts_forecast.series_chart(fc["chart"])
    for fig in (past, ahead):
        for tr in fig.data:
            if tr.fill == "toself":
                assert tr.mode == "lines", tr.name
    ranks = charts_forecast.ranking_chart(v["ranking"], v["unit"]).data[0].text
    assert ranks[0] == f"{v['ranking']['average_miss'].iloc[0]:.2f}"  # small gaps between approaches stay visible
