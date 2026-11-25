"""Phase 5D, step B: read-only loaders and forecast helpers. Every value is checked against the saved files,
recomputed here independently; the 'show the next' choices never go past the saved forecast length; missing files
raise Missing; plain names never contain engine names or banned words."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")

from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import BANNED_RE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FC_DIR = ROOT / "outputs" / "phase3" / "forecasts"
P1, P2, P3 = (ROOT / "outputs" / f"phase{i}" / "tables" for i in (1, 2, 3))
SEVEN = ["eci_wages_quarterly", "ppi_hosting_monthly", "burst_tokens_total_daily", "burst_tokens_api_daily",
         "burst_tokens_chat_daily", "burst_requests_hourly", "wildchat_conversations_daily"]
needs = pytest.mark.skipif(not all((FC_DIR / f"{s}.csv").exists() for s in SEVEN)
                           or not (P2 / "leaderboard.csv").exists() or not (P3 / "interval_check.csv").exists(),
                           reason="Phase 1 to 3 outputs missing")
ENGINE_NAMES = ["arima", "sarima", "holt", "ensemble", "naive", "prophet", "lstm", "xgboost", "ridge", "ses",
                "drift", "random_forest", "seasonal", "hw_", "_ma3", "MAE", "RMSE", "MAPE", "MASE"]


@needs
def test_every_saved_series_is_listed_once_in_page_order():
    assert D.forecast_series() == SEVEN
    assert list(LF.SERIES) == SEVEN and set(C.SERIES) == set(SEVEN)


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_likely_range_is_the_10th_to_90th_percentile(name):
    fc = pd.read_csv(FC_DIR / f"{name}.csv")
    rng = LF.expected_and_range(fc)
    sims = fc[fc["sample_id"] >= 0]
    for step in (1, len(rng) // 2, len(rng)):
        v = sims.loc[sims["period_index"] == step, "value"].to_numpy()
        row = rng[rng["period_index"] == step].iloc[0]
        assert row["low"] == pytest.approx(np.quantile(v, 0.10))
        assert row["high"] == pytest.approx(np.quantile(v, 0.90))
        assert row["expected"] == pytest.approx(fc[(fc["sample_id"] == -1) & (fc["period_index"] == step)]["value"].iloc[0])
    assert len(rng) == LF.saved_horizon(fc) == fc["period_index"].max()


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_show_the_next_never_goes_past_the_saved_length(name):
    fc = pd.read_csv(FC_DIR / f"{name}.csv")
    saved, g = LF.saved_horizon(fc), LF.grain(fc)
    opts = LF.horizon_options(g, saved)
    assert opts[-1] == saved and all(1 <= n <= saved for n in opts) and opts == sorted(set(opts))
    rng = LF.expected_and_range(fc)
    for n in opts:
        assert len(LF.cut(rng, n)) == n
    with pytest.raises(ValueError):
        LF.cut(rng, saved + 1)
    with pytest.raises(ValueError):
        LF.cut(rng, 0)


def test_saved_lengths_give_these_choices():
    assert LF.horizon_options("month", 12) == [3, 6, 12]
    assert LF.horizon_options("quarter", 8) == [4, 8]
    assert LF.horizon_options("day", 14) == [7, 14]
    assert LF.horizon_options("hour", 168) == [24, 72, 168]
    assert LF.horizon_options("month", 6) == [3, 6]  # a shorter saved forecast only gets shorter cuts


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_history_is_the_series_the_forecast_was_built_on(name):
    h = D.history(name)
    stats = pd.read_csv(ROOT / "outputs" / "phase1" / "tables" / "summary_stats.csv").set_index("driver").loc[name]
    assert len(h) == int(stats["n"])
    assert h["value"].mean() == pytest.approx(float(stats["mean"]), rel=1e-9)
    assert h["value"].min() == pytest.approx(float(stats["min"])) and h["value"].max() == pytest.approx(float(stats["max"]))
    assert str(h["x"].iloc[0])[:10] == str(stats["start"])[:10] and str(h["x"].iloc[-1])[:10] == str(stats["end"])[:10]
    assert not h["value"].isna().any()


@needs
def test_future_positions_follow_the_last_real_point():
    expect = {"eci_wages_quarterly": ("Q4 2026", "Q3 2028"), "ppi_hosting_monthly": ("Nov 2026", "Oct 2027"),
              "burst_tokens_total_daily": ("Day 88", "Day 101"), "burst_requests_hourly": ("Hour 2,089", "Hour 2,256"),
              "wildchat_conversations_daily": ("3 Jul 2024", "16 Jul 2024")}
    for name, (first, last) in expect.items():
        fc = pd.read_csv(FC_DIR / f"{name}.csv")
        g, h = LF.grain(fc), D.history(name)
        fx = LF.future_x(h["x"].iloc[-1], LF.expected_and_range(fc), g)
        assert (LF.step_label(fx[0], g), LF.step_label(fx[-1], g)) == (first, last), name


@needs
def test_series_facts_match_phase1():
    an = pd.read_csv(P1 / "anomalies.csv")
    f = LF.series_facts(D.history("ppi_hosting_monthly"), "ppi_hosting_monthly", "month", an)
    assert f == {"start": "Dec 2000", "end": "Oct 2026", "count": 311, "unusual": 12, "dated": True, "gaps": 0}
    f = LF.series_facts(D.history("burst_tokens_total_daily"), "burst_tokens_total_daily", "day", an)
    assert (f["start"], f["end"], f["dated"]) == ("Day 1", "Day 87", False)


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_past_checks_and_ranking_match_phase2_and_phase3(name):
    chosen = pd.read_csv(P2 / "chosen_models.csv")
    hold, lb = pd.read_csv(P2 / "holdout.csv"), pd.read_csv(P2 / "leaderboard.csv")
    ic = pd.read_csv(P3 / "interval_check.csv")
    ap = LF.chosen_approach(chosen, name)
    assert ap == chosen.set_index("driver").loc[name, "chosen_model"]
    pc = LF.past_check(hold, name, ap)
    raw = hold[(hold["driver"] == name) & (hold["model"] == ap)]
    assert len(pc) == len(raw)
    assert LF.average_miss(pc) == pytest.approx(float(raw["holdout_mae"].iloc[0]), rel=1e-6)
    assert int(pc["inside"].sum()) == int(((raw["actual"] >= raw["lo80"]) & (raw["actual"] <= raw["hi80"])).sum())
    inside, n = LF.range_hits(ic, name)
    row = ic[(ic["driver"] == name) & (ic["segment"] == "all")].iloc[0]
    assert n == int(row["n_holdout_points"]) and inside / n == pytest.approx(row["coverage_80_after"], abs=0.5 / n)
    g = LF.grain(pd.read_csv(FC_DIR / f"{name}.csv"))
    rk = LF.ranking(lb, name, ap, g)
    ok = lb[(lb["driver"] == name) & (lb["status"] == "ok")]
    assert len(rk) == len(ok) and list(rk["average_miss"]) == sorted(rk["average_miss"])
    assert rk["chosen"].sum() == 1 and rk["reference"].sum() == 1
    ref = float(ok.loc[ok["model"] == "seasonal_naive", "cv_mae"].iloc[0])
    mine = float(ok.loc[ok["model"] == ap, "cv_mae"].iloc[0])
    assert rk.loc[rk["chosen"], "smaller_than_reference"].iloc[0] == pytest.approx(1 - mine / ref)
    assert mine < ref  # Phase 2: every chosen approach beat the simple reference


def test_plain_names_hide_engine_names():
    for g in ("hour", "day", "month", "quarter"):
        for key in C.APPROACH:
            label = LF.approach_label(key, g)
            assert "{" not in label and not BANNED_RE.search(label), label
            low = label.lower()
            assert not any(e.lower() in low for e in ENGINE_NAMES), label
    for name, desc, unit, axis in C.SERIES.values():
        for s in (name, desc, unit, axis):
            assert not BANNED_RE.search(s), s
    assert LF.approach_label("seasonal_naive", "day") == "Repeat the same weekday last week"
    assert LF.approach_label("seasonal_naive", "month") == "Repeat the same month last year"


def test_amounts_use_the_indian_style():
    assert LF.amount(950) == "950" and LF.amount(12345) == "12,345"
    assert LF.amount(2_310_000) == "23.1 lakh" and LF.amount(34_461_774) == "3.45 crore"
    assert LF.amount(120_000_000) == "12 crore" and LF.amount(128.78, "points") == "128.8"
    assert LF.amount(float("nan")) == "Not available"


def test_missing_files_raise_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TSAF_DASH_ROOT", str(tmp_path))
    for call in (lambda: D.phase_table(2, "leaderboard"), lambda: D.history("ppi_hosting_monthly"),
                 lambda: D.saved_forecast("eci_wages_quarterly")):
        with pytest.raises(D.Missing):
            call()
    assert D.forecast_series() == []
    (tmp_path / "data" / "processed").mkdir(parents=True)  # folder there, file not: still Missing, not a crash
    with pytest.raises(D.Missing):
        D.history("ppi_hosting_monthly")
