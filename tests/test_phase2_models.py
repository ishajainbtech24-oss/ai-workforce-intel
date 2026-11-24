"""Phase 2 models: output shape, accuracy on a known seasonal series, ML leakage and recursion."""
import numpy as np
import pandas as pd
import pytest

from tsaf.metrics import mae
from tsaf.models import ml
from tsaf.models.registry import build_registry, by_name

H = 7


def _series(n: int = 120) -> pd.Series:
    """Sine (period 7) + trend + fixed-seed noise, strictly positive."""
    rng = np.random.default_rng(42)
    t = np.arange(n)
    return pd.Series(100 + 0.5 * t + 20 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 3, n),
                     index=pd.RangeIndex(n, name="day_index"))


def _ctx(y: pd.Series) -> dict:
    extra = pd.Series(np.asarray(y) / 10 + 5, index=y.index)
    return {"name": "burst_tokens_total_daily", "grain": "daily", "season": 7, "extra_seasons": [],
            "d": 0, "D": 0, "decomposition": "multiplicative", "positive": True, "nonneg": True,
            "fast": False, "with_lstm": True, "n_trees": 50, "arima_max_candidates": 3,
            "arima_budget": {"seconds": 60.0, "used": 0.0},
            "extra": {"series": extra, "lag": 14, "col": "requests"}}


def _run(spec, train, h, ctx):
    params = spec.select(train, ctx) if spec.select else {}
    return spec.fit_predict(train, h, {**ctx, "params": params})


def test_every_registered_model_returns_h_finite_values():
    y = _series()
    ctx = _ctx(y)
    train = y.iloc[:-H]
    ran = []
    for spec in build_registry():
        if spec.skip_reason(ctx):
            continue  # e.g. Prophet when it is not installed
        fc = _run(spec, train, H, ctx)
        assert fc.shape == (H,), spec.name
        assert np.all(np.isfinite(fc)), spec.name
        ran.append(spec.name)
    assert {"naive", "seasonal_naive", "ses", "hw_additive", "arima", "sarima", "sarimax", "ridge",
            "random_forest", "ridge_with_requests"} <= set(ran)


@pytest.mark.parametrize("name", ["hw_additive", "sarima"])
def test_seasonal_models_beat_naive_on_seasonal_series(name):
    y = _series()
    train, test = y.iloc[:-14], y.iloc[-14:]
    ctx = _ctx(y)
    specs = by_name(build_registry())
    naive_err = mae(test, _run(specs["naive"], train, 14, ctx))
    assert mae(test, _run(specs[name], train, 14, ctx)) < naive_err


def test_ml_features_use_no_future_information():
    y = _series()
    ctx = _ctx(y)
    spec = ml.feature_spec(ctx, with_extra=True)
    base = ml.build_features(y, spec, extra=ctx["extra"]["series"])
    for j in (30, 60, 100):
        y2, ex2 = y.copy(), ctx["extra"]["series"].copy()
        y2.iloc[j] += 1e6
        ex2.iloc[j] += 1e6
        changed = ml.build_features(y2, spec, extra=ex2)
        pd.testing.assert_frame_equal(base.iloc[: j + 1], changed.iloc[: j + 1])  # rows <= j unchanged
        assert not base.iloc[j + 1:].equals(changed.iloc[j + 1:])  # later rows do see it


class _PlusOne:
    """Stub model: next value = previous value + 1."""

    def predict(self, X):
        return X["lag_1"].to_numpy() + 1.0


def test_recursive_forecast_feeds_predictions_back():
    y = pd.Series(np.arange(50, dtype=float), index=pd.RangeIndex(50))
    spec = ml.FeatureSpec(grain="daily", lags=(1, 2), roll=3, weekend=False)
    fc = ml.recursive_forecast(_PlusOne(), y, 5, spec, "daily")
    np.testing.assert_allclose(fc, [50, 51, 52, 53, 54])  # only possible if step k used prediction k-1
