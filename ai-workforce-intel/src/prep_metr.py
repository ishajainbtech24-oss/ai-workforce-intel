"""METR developer RCT -> clean task table + effect summary for the downside scenario.

Not a time series: it supplies the evidence that AI can slow some workers down.
The headline estimate here is a simple ratio of means; the paper's regression
(repo: regression.py) is the citable figure.

Outputs (data/processed/):
  metr_tasks            one row per task, with log times
  metr_effect_summary   mean times by arm and the naive slowdown ratio
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, save, log_quality  # noqa: E402


def run():
    print("METR RCT")
    f = RAW / "metr" / "data_complete.csv"
    if not f.exists():
        raise FileNotFoundError("data/raw/metr/data_complete.csv missing - run download.py --only metr")
    d = pd.read_csv(f)
    n0 = len(d)
    d = d.dropna(subset=["ai_treatment", "initial_implementation_time"])
    d = d[d["initial_implementation_time"] > 0]
    d["ai_treatment"] = d["ai_treatment"].astype(int)
    d["log_time"] = np.log(d["initial_implementation_time"])
    d["log_pred_no_ai"] = np.log(d["predicted_time_no_ai"])
    d["forecast_speedup_expected"] = d["predicted_time_no_ai"] / d["predicted_time_ai_allowed"] - 1
    save(d, "metr_tasks")

    s = d.groupby("ai_treatment").agg(tasks=("issue_id", "size"),
                                      mean_minutes=("initial_implementation_time", "mean"),
                                      median_minutes=("initial_implementation_time", "median")).reset_index()
    s["arm"] = s["ai_treatment"].map({0: "AI not allowed", 1: "AI allowed"})
    save(s, "metr_effect_summary")
    ratio = s.loc[s.ai_treatment == 1, "mean_minutes"].item() / s.loc[s.ai_treatment == 0, "mean_minutes"].item() - 1
    log_quality("METR RCT", rows_raw=n0, rows_clean=len(d), developers=int(d.dev_id.nunique()),
                naive_time_change_with_ai=f"{ratio:+.1%} (ratio of mean times; not the paper's regression)",
                paper_estimate="+18.8% time with AI (95% CI ~+1% to +39%), per repo README",
                use="downside bound for hours-saved scenario")


if __name__ == "__main__":
    run()
