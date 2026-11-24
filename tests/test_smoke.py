"""End-to-end smoke test: the whole runner in --fast mode on a synthetic data folder."""
import json

import numpy as np
import pandas as pd

import run_phase1
from tsaf.handoff import validate


def _burst_daily(n_days: int = 121) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    d = np.arange(n_days)
    week = 1 + 0.4 * np.sin(2 * np.pi * d / 7)
    api = 1e6 * week * rng.lognormal(0, 0.3, n_days)
    df = pd.DataFrame({"day_index": d, "ChatGPT_api_total_tokens": api * 0.9,
                       "GPT-4_api_total_tokens": api * 0.1,
                       "ChatGPT_conversation_total_tokens": 2e5 * week + 1e3 * d,
                       "GPT-4_conversation_total_tokens": 1e5 * week, "requests": api / 300})
    df["total_tokens"] = df.filter(like="_total_tokens").sum(axis=1)
    df.loc[77, ["total_tokens", "ChatGPT_api_total_tokens"]] = [1e4, 5e3]
    df["day_of_cycle"] = d % 7
    df["copied_day"] = d.__ge__(87) & d.__le__(91)
    df["low_activity"] = d >= 93
    df["anomaly_low_day"] = d == 77
    df["in_model_window"] = d <= 86
    return df


def _burst_hourly(n_hours: int = 624) -> pd.DataFrame:
    """26 days: enough for 2 hourly folds (initial 336, step 72, h 24) before a 168-hour hold-out."""
    h = np.arange(n_hours)
    req = 100 + 50 * np.sin(2 * np.pi * h / 24) + 20 * np.sin(2 * np.pi * h / 168) + h % 5
    return pd.DataFrame({"hour_index": h, "requests": req, "day_index": h // 24,
                         "copied_day": False, "low_activity": False, "in_model_window": True})


def _wildchat_daily(n_days: int = 90) -> pd.DataFrame:
    dates = pd.date_range("2023-04-09", periods=n_days, freq="D")
    rows = [{"date": dt, "model_family": fam, "conversations": int(1000 + 10 * i + 200 * (i % 7 == 0)),
             "missing_day": False}
            for i, dt in enumerate(dates) for fam in ("gpt35_family", "gpt4_family")]
    df = pd.DataFrame(rows)
    df.loc[df["date"] == dates[-1], ["conversations", "missing_day"]] = [0, True]  # gap at the end
    return df


def test_fast_pipeline_on_synthetic_data(tmp_path):
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir()
    _burst_daily().to_parquet(data / "burstgpt_daily_wide.parquet", index=False)
    _burst_hourly().to_parquet(data / "burstgpt_hourly_total.parquet", index=False)
    _wildchat_daily().to_parquet(data / "wildchat_daily.parquet", index=False)
    assert run_phase1.main(["--fast", "--data-dir", str(data), "--out-dir", str(out)]) == 0
    for name in ["data_contract.md", "run.log", "handoff.json", "PHASE1_SUMMARY.md",
                 "tables/summary_stats.csv", "tables/stationarity.csv", "tables/baseline_cv.csv",
                 "tables/leaderboard_baselines.csv", "tables/trend_methods.csv",
                 "figures/trend_methods_burstgpt.png", "figures/burst_tokens_total_daily_series.png"]:
        assert (out / name).exists(), name
    doc = json.loads((out / "handoff.json").read_text(encoding="utf-8"))
    validate(doc)
    names = {d["name"] for d in doc["drivers"]}
    assert {"burst_tokens_total_daily", "burst_requests_hourly", "wildchat_conversations_daily"} <= names
    assert any(s["name"] == "eci_wages_quarterly" for s in doc["skipped"])
