"""Metrics against hand-computed values, and the five baselines on known series."""
import math

import numpy as np
import pandas as pd
import pytest

from tsaf import baselines, metrics


def test_metrics_hand_computed():
    y, f = [2.0, 4.0, 6.0], [3.0, 3.0, 9.0]          # errors -1, 1, -3
    assert metrics.mae(y, f) == pytest.approx(5 / 3)
    assert metrics.rmse(y, f) == pytest.approx(math.sqrt(11 / 3))
    # MAPE: (1/2 + 1/4 + 3/6) / 3 * 100
    assert metrics.mape(y, f) == pytest.approx(125 / 3)
    # sMAPE: 200 * (1/5 + 1/7 + 3/15) / 3
    assert metrics.smape(y, f) == pytest.approx(200 * (1 / 5 + 1 / 7 + 3 / 15) / 3)
    # MASE, naive scale of train [1, 3, 6] = mean(|2|, |3|) = 2.5
    assert metrics.mase(y, f, [1.0, 3.0, 6.0], None) == pytest.approx((5 / 3) / 2.5)


def test_mape_nan_with_zero_actual_and_smape_zero_terms():
    assert math.isnan(metrics.mape([0.0, 1.0], [1.0, 1.0]))
    assert metrics.smape([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_mase_seasonal_naive_on_periodic_series_is_zero():
    # Periodic from the second cycle on. The first cycle differs so the in-sample
    # seasonal-naive scale is > 0 (an exactly periodic train has scale 0 -> MASE NaN).
    pattern = np.array([1.0, 5.0, 3.0, 8.0])
    values = np.tile(pattern, 10)
    values[:4] += [2.0, -1.0, 0.5, 1.0]
    series = pd.Series(values)
    train, test = series.iloc[:32], series.iloc[32:]
    fc = baselines.seasonal_naive(train, len(test), 4)
    assert metrics.mase(test, fc, train, 4) == 0.0


def test_mase_nan_when_scale_is_zero():
    assert math.isnan(metrics.mase([1.0], [2.0], [5.0, 5.0, 5.0], None))


def test_naive_repeats_last_value():
    assert np.array_equal(baselines.naive(pd.Series([1.0, 2.0, 7.0]), 3), [7.0, 7.0, 7.0])


def test_seasonal_naive_reproduces_periodic_series():
    pattern = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0])
    s = pd.Series(np.tile(pattern, 5))
    assert np.array_equal(baselines.seasonal_naive(s, 10, 7), np.tile(pattern, 2)[:10])


def test_seasonal_naive_falls_back_to_naive():
    assert np.array_equal(baselines.seasonal_naive(pd.Series([1.0, 4.0]), 2, None), [4.0, 4.0])


def test_drift_continues_straight_line():
    s = pd.Series(3.0 + 2.0 * np.arange(10))
    assert np.allclose(baselines.drift(s, 4), 3.0 + 2.0 * np.arange(10, 14))


def test_mean_and_seasonal_ma():
    s = pd.Series(np.tile([1.0, 2.0, 3.0], 4))
    assert np.allclose(baselines.mean_forecast(s, 2), [2.0, 2.0])
    assert np.allclose(baselines.seasonal_ma(s, 3, 3), [1.0, 2.0, 3.0])
    assert np.allclose(baselines.seasonal_ma(pd.Series([1.0, 2.0, 3.0, 9.0]), 2, None), [14 / 3, 14 / 3])
