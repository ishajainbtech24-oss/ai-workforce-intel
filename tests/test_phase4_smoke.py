"""Smoke test: run_phase4.py --fast on a small synthetic project (data + Phase 3 outputs)."""
import json
import re

import numpy as np
import pandas as pd

import config_phase4 as P4
import run_phase4
from tsaf import export


def _phase3(p3, rng):
    fc = p3 / "forecasts"
    fc.mkdir(parents=True)
    for name, h, grain, start in (("eci_wages_quarterly", 8, "quarterly", 100.0), ("ppi_hosting_monthly", 12, "monthly", 120.0)):
        point = start * (1 + 0.005 * np.arange(1, h + 1))
        paths = point * (1 + rng.normal(0, 0.01, (200, h)))
        t = export.build_table(name, point, paths, [""] * h, "index_points", "m", "fred", grain)
        t.to_parquet(fc / f"{name}.parquet", index=False)
    rr = np.r_[1e8, 1e8 * rng.lognormal(0, 0.3, 200)]
    pd.DataFrame({"driver": "burst_tokens_total_daily", "sample_id": np.arange(-1, 200), "run_rate_30d": rr,
                  "extrapolated": True}).to_csv(fc / "burstgpt_monthly_run_rate.csv", index=False)
    pd.DataFrame([{"scenario": s, "parameter": p, "value": v, "unit": u, "source": "x", "derivation": "y",
                   "status": "measured", "kind": "assumption"} for s, p, v, u in
                  (("downside", "task_time_change_with_ai", 18.8, "pct_change_in_task_time"),
                   ("expected", "time_saved_share_of_work_hours", 2.0, "pct_of_work_hours"),
                   ("optimistic", "time_saved_share_of_work_hours", 4.0, "pct_of_work_hours"))]).to_csv(
        fc / "scenario_tables.csv", index=False)
    man = {"drivers": [{"driver": d, "file": f"forecasts/{d}.parquet", "unit": "index_points", "grain": g, "horizon": h,
                        "n_samples": 200, "model_used": "m"} for d, g, h in
                       (("eci_wages_quarterly", "quarterly", 8), ("ppi_hosting_monthly", "monthly", 12),
                        ("burst_tokens_total_daily", "daily", 14))]}
    (p3 / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    (p3 / "inputs_for_phase4.json").write_text(json.dumps({"input_token_share": 0.86, "uncertainty_sensitivity":
                                                           {"multipliers": [1.0, 2.0]}}), encoding="utf-8")


def _data(data):
    data.mkdir()
    pd.DataFrame({"date": pd.date_range("2016-01-01", periods=40, freq="QS"),
                  "eci_wages_sa": np.linspace(80, 100, 40)}).to_parquet(data / "eci_quarterly.parquet", index=False)
    pd.DataFrame({"date": pd.date_range("2018-01-01", periods=60, freq="MS"),
                  "ppi_hosting": np.linspace(110, 120, 60)}).to_parquet(data / "ppi_hosting_monthly.parquet", index=False)


def test_phase4_fast_on_synthetic_project(tmp_path):
    p3, data, out = tmp_path / "p3", tmp_path / "data", tmp_path / "p4"
    _phase3(p3, np.random.default_rng(0))
    _data(data)
    assert run_phase4.main(["--fast", "--phase3-dir", str(p3), "--data-dir", str(data), "--out-dir", str(out),
                            "--inputs", str(P4.EXAMPLE_INPUTS)]) == 0
    files = ["data_contract.md", "run.log", "assumptions.json", "PHASE4_SUMMARY.md"]
    files += [f"tables/{t}" for t in ("monthly_summary.csv", "totals_summary.csv", "break_even_summary.csv",
                                      "cost_breakdown.csv", "extrapolation.csv", "sensitivity.csv", "draws_sample.parquet")]
    files += [f"figures/{f}_{s}.png" for f in ("cost_stack", "cumulative_net", "break_even_hist")
              for s in ("downside", "expected", "optimistic")]
    files += ["figures/scenario_compare.png", "figures/multiplier_effect.png", "figures/cost_share_by_type.png"]
    for f in files:
        assert (out / f).exists(), f
    be = pd.read_csv(out / "tables" / "break_even_summary.csv")
    assert len(be) == 6  # 3 scenarios x 2 multipliers
    assert not re.search(r"\b(nan|None|NaN)\b", (out / "PHASE4_SUMMARY.md").read_text(encoding="utf-8"))
