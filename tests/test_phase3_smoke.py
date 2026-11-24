"""Smoke test: run_phase3.py --fast on a small synthetic project (data, Phase 1 and Phase 2 outputs)."""
import json
import re

import numpy as np
import pandas as pd

import run_phase3
from test_phase2_smoke import _handoff
from test_smoke import _burst_daily, _burst_hourly


def _residuals(rng) -> pd.DataFrame:
    rows = [{"driver": "burst_tokens_total_daily", "model": "ensemble", "fold": f, "step_ahead": s,
             "origin_index": o, "error": rng.normal(0, 3e5)} for f, o in enumerate([42, 49, 56, 63]) for s in range(1, 8)]
    rows += [{"driver": "burst_requests_hourly", "model": "seasonal_naive", "fold": f, "step_ahead": s,
              "origin_index": o, "error": rng.normal(0, 10)} for f, o in enumerate([336, 408]) for s in range(1, 25)]
    df = pd.DataFrame(rows)
    df["time"], df["actual"], df["forecast"] = "", 0.0, 0.0
    return df


def _chosen() -> dict:
    daily = {"name": "burst_tokens_total_daily", "file": "burstgpt_daily_wide", "value_col": "total_tokens",
             "grain": "daily", "season": 7, "chosen_model": "ensemble", "family": "ensemble",
             "params": {"components": [{"model": "naive", "params": {}}, {"model": "seasonal_naive", "params": {}}]},
             "beats_seasonal_naive": True, "cv_mase": 0.5, "holdout_mase": 0.9, "interval_coverage_80": 0.7,
             "horizon_for_forecast": 14, "notes": "synthetic"}
    hourly = {**daily, "name": "burst_requests_hourly", "file": "burstgpt_hourly_total", "value_col": "requests",
              "grain": "hourly", "season": 24, "chosen_model": "seasonal_naive", "family": "baseline", "params": {},
              "horizon_for_forecast": 168}
    return {"phase": 2, "drivers": [daily, hourly], "skipped": []}


def _data(folder) -> None:
    d = _burst_daily()
    d.to_parquet(folder / "burstgpt_daily_wide.parquet", index=False)
    _burst_hourly().to_parquet(folder / "burstgpt_hourly_total.parquet", index=False)
    pd.DataFrame({"day_index": d["day_index"], "request_tokens": d["total_tokens"] * 0.7,
                  "response_tokens": d["total_tokens"] * 0.3, "total_tokens": d["total_tokens"]}).to_parquet(
        folder / "burstgpt_daily.parquet", index=False)
    pd.DataFrame({"date": pd.date_range("2025-01-01", periods=4, freq="QS"), "hours_assisted_pct": [4.0, 4.5, 5, 5.5],
                  "time_saved_pct_hours": [1.5, 1.6, 1.8, 2.0]}).to_parquet(folder / "genai_tracker.parquet", index=False)
    pd.DataFrame({"date": pd.Timestamp("2025-01-01"), "series_id": ["A", "B"], "description": ["occ a", "ind b"],
                  "time_saved_pct_hours": [2.5, 3.1], "group_type": ["occupation", "industry"]}).to_parquet(
        folder / "genai_timesaved_panel.parquet", index=False)
    pd.DataFrame({"ai_treatment": [0, 1], "tasks": [10, 12], "mean_minutes": [90.0, 110.0], "median_minutes": [60, 70],
                  "arm": ["no", "yes"]}).to_parquet(folder / "metr_effect_summary.parquet", index=False)


def test_phase3_fast_on_synthetic_project(tmp_path):
    data, p1, p2, out = tmp_path / "data", tmp_path / "p1", tmp_path / "p2", tmp_path / "p3"
    for f in (data, p1, p2 / "tables"):
        f.mkdir(parents=True)
    _data(data)
    (p1 / "handoff.json").write_text(json.dumps(_handoff()), encoding="utf-8")
    (p2 / "chosen_models.json").write_text(json.dumps(_chosen()), encoding="utf-8")
    _residuals(np.random.default_rng(0)).to_parquet(p2 / "tables" / "cv_residuals.parquet", index=False)
    log = tmp_path / "quality.md"
    log.write_text("- **paper_estimate:** +18.8% time with AI (95% CI ~+1% to +39%), per repo README\n", encoding="utf-8")
    assert run_phase3.main(["--fast", "--data-dir", str(data), "--phase1-dir", str(p1), "--phase2-dir", str(p2),
                            "--out-dir", str(out), "--quality-log", str(log)]) == 0
    expected = ["manifest.json", "inputs_for_phase4.json", "PHASE3_SUMMARY.md", "run.log",
                "tables/interval_check.csv", "tables/validation.csv", "forecasts/scenario_tables.csv",
                "forecasts/burstgpt_monthly_run_rate.csv", "forecasts/burstgpt_monthly_run_rate_summary.csv",
                "figures/interval_check.png", "figures/run_rate_burstgpt.png", "figures/scenarios.png"]
    for d in ("burst_tokens_total_daily", "burst_requests_hourly"):
        expected += [f"forecasts/{d}.parquet", f"forecasts/{d}.csv", f"figures/fan_{d}.png"]
    for name in expected:
        assert (out / name).exists(), name
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert {m["driver"] for m in man["drivers"]} == {"burst_tokens_total_daily", "burst_requests_hourly"}
    assert next(m for m in man["drivers"] if m["driver"] == "burst_requests_hourly")["few_folds"] is True
    assert (pd.read_csv(out / "tables" / "validation.csv")["status"] == "PASS").all()
    assert not re.search(r"\b(nan|None|NaN)\b", (out / "PHASE3_SUMMARY.md").read_text(encoding="utf-8"))
