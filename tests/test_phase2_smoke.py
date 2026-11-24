"""End-to-end smoke test: Phase 2 (--fast) on a small synthetic data folder and handoff."""
import json
import re

import run_phase2
from test_smoke import _burst_daily, _burst_hourly
from tsaf import chosen

TABLES = ["leaderboard.csv", "chosen_models.csv", "params.csv", "cv_folds.csv", "cv_residuals.parquet",
          "holdout.csv", "residual_diagnostics.csv", "interval_coverage.csv", "feature_importance.csv",
          "anomalies.csv"]
DRIVERS = ["burst_tokens_total_daily", "burst_requests_hourly"]


def _handoff() -> dict:
    """A minimal Phase 1 handoff for the two synthetic drivers (same keys Phase 1 writes)."""
    daily = {"name": "burst_tokens_total_daily", "file": "burstgpt_daily_wide", "value_col": "total_tokens",
             "grain": "daily", "season": 7, "extra_seasons": [], "decomposition": "multiplicative",
             "d": 0, "D": 0, "cv_settings": {"initial": 42, "h": 7, "step": 7, "holdout": 14}}
    hourly = {"name": "burst_requests_hourly", "file": "burstgpt_hourly_total", "value_col": "requests",
              "grain": "hourly", "season": 24, "extra_seasons": [168], "decomposition": "additive",
              "d": 0, "D": 1, "cv_settings": {"initial": 336, "h": 24, "step": 72, "holdout": 168}}
    return {"phase": 1, "drivers": [daily, hourly],
            "skipped": [{"name": "eci_wages_quarterly", "reason": "file not found"}]}


def test_phase2_fast_pipeline_on_synthetic_data(tmp_path):
    data, out1, out2 = tmp_path / "data", tmp_path / "p1", tmp_path / "p2"
    data.mkdir()
    _burst_daily().to_parquet(data / "burstgpt_daily_wide.parquet", index=False)
    _burst_hourly().to_parquet(data / "burstgpt_hourly_total.parquet", index=False)
    out1.mkdir()
    (out1 / "handoff.json").write_text(json.dumps(_handoff()), encoding="utf-8")
    assert run_phase2.main(["--fast", "--data-dir", str(data), "--out-dir", str(out2),
                            "--handoff", str(out1 / "handoff.json"), "--drivers", *DRIVERS]) == 0
    for name in ["run.log", "chosen_models.json", "PHASE2_SUMMARY.md"] + [f"tables/{t}" for t in TABLES]:
        assert (out2 / name).exists(), name
    for d in DRIVERS:
        for kind in ("leaderboard", "forecast", "residuals", "cv_folds"):
            assert (out2 / "figures" / f"{kind}_{d}.png").exists(), (kind, d)
    doc = json.loads((out2 / "chosen_models.json").read_text(encoding="utf-8"))
    chosen.validate(doc)
    assert {e["name"] for e in doc["drivers"]} == set(DRIVERS)
    text = (out2 / "PHASE2_SUMMARY.md").read_text(encoding="utf-8")
    assert not re.search(r"\b(nan|None|NaN)\b", text)
