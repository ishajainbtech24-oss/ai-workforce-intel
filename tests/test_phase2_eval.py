"""Phase 2 evaluation: interval coverage, choice rule, failure handling, hand-off schema."""
import numpy as np
import pandas as pd
import pytest

from tsaf import backtest, chosen, evaluate
from tsaf.models.base import Fit
from tsaf.models.registry import ModelSpec, by_name, build_registry
from tsaf.pipeline_phase2 import run_model


def test_lofo_intervals_cover_near_nominal_level():
    rng = np.random.default_rng(42)
    folds = pd.DataFrame([{"fold": f, "step_ahead": s, "actual": rng.normal(0, 1), "forecast": 0.0}
                          for f in range(60) for s in range(1, 6)])
    cov = evaluate.coverage(evaluate.lofo_intervals(folds))
    assert abs(cov["coverage_80"] - 0.80) <= 0.10
    assert abs(cov["coverage_95"] - 0.95) <= 0.10


def _board(rows):
    return pd.DataFrame(rows, columns=["model", "family", "status", "cv_mase"])


def test_choice_rule_keeps_seasonal_naive_when_every_model_is_worse():
    b = _board([("seasonal_naive", "baseline", "ok", 0.80), ("naive", "baseline", "ok", 0.95),
                ("sarima", "arima", "ok", 0.85), ("xgboost", "ml", "ok", 0.90),
                ("broken", "ml", "failed", 0.10)])
    model, why = evaluate.choose(b)
    assert model == "seasonal_naive"


def test_choice_rule_prefers_simpler_family_on_a_one_percent_tie():
    b = _board([("seasonal_naive", "baseline", "ok", 1.00), ("xgboost", "ml", "ok", 0.700),
                ("ses", "smoothing", "ok", 0.705)])
    assert evaluate.choose(b)[0] == "ses"
    b2 = _board([("seasonal_naive", "baseline", "ok", 1.00), ("xgboost", "ml", "ok", 0.70),
                 ("ses", "smoothing", "ok", 0.75)])
    assert evaluate.choose(b2)[0] == "xgboost"


def _boom(train, h, ctx):
    raise RuntimeError("deliberate failure")


def test_failing_model_is_recorded_and_run_continues():
    y = pd.Series(np.arange(80, dtype=float) % 7 + 10)
    cv = {"h": 7, "initial": 42, "step": 7, "max_folds": None, "holdout": 14}
    pre, _ = backtest.holdout_split(y, cv["holdout"])
    origins = backtest.fold_origins(len(pre), 42, 7, 7, None)
    ctx = {"season": 7, "nonneg": True, "grain": "daily"}
    bad = run_model(ModelSpec("boom", "ml", _boom), pre, cv, origins, ctx)
    assert bad.status == "failed" and "deliberate failure" in bad.reason
    good = run_model(by_name(build_registry())["seasonal_naive"], pre, cv, origins, ctx)
    assert good.status == "ok" and len(good.holdout_fc) == 14


def _entry():
    return {"name": "x", "file": "f", "value_col": "v", "grain": "daily", "season": 7,
            "chosen_model": "naive", "family": "baseline", "params": {}, "beats_seasonal_naive": False,
            "cv_mase": 0.9, "holdout_mase": 1.1, "interval_coverage_80": 0.7, "horizon_for_forecast": 14,
            "notes": "test"}


def test_chosen_models_schema_catches_missing_key():
    chosen.validate({"drivers": [_entry()]})
    broken = _entry()
    del broken["horizon_for_forecast"]
    with pytest.raises(ValueError, match="horizon_for_forecast"):
        chosen.validate({"drivers": [broken]})
    wrong = {**_entry(), "cv_mase": "0.9"}
    with pytest.raises(ValueError, match="cv_mase"):
        chosen.validate({"drivers": [wrong]})


def test_fit_type_is_plain_dataclass():
    f = Fit(forecast=np.zeros(3))
    assert f.insample is None and f.info == {}
