"""Phase 3: bootstrap rules, growth, clipping, fallback guard, ensemble, validators, coverage."""
import numpy as np
import pandas as pd
import pytest

import config_phase3 as P3
from tsaf import export, simulate, validate
from tsaf.forecast import model_forecast, point_forecast
from tsaf.models.base import Fit
from tsaf.models.registry import ModelSpec


def _rows(E: np.ndarray, origins) -> pd.DataFrame:
    return pd.DataFrame([{"fold": f, "origin_index": o, "step_ahead": s + 1, "error": E[f, s]}
                         for f, o in enumerate(origins) for s in range(E.shape[1])])


def _es(n_folds=5, H=7, seed=0, relative=False) -> simulate.ErrorSet:
    E = np.random.default_rng(seed).normal(0, 1, (n_folds, H))
    return simulate.ErrorSet(E=E, relative=relative, folds=list(range(n_folds)), H=H)


def test_bootstrap_shape_and_seed():
    es, point = _es(), np.full(10, 100.0)
    a = simulate.simulate(point, es, 1.0, P3.N_SAMPLES, 42, "sqrt").values
    b = simulate.simulate(point, es, 1.0, P3.N_SAMPLES, 42, "sqrt").values
    c = simulate.simulate(point, es, 1.0, P3.N_SAMPLES, 43, "sqrt").values
    assert a.shape == (200, 10)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)


def test_whole_vector_resampling():
    es, point = _es(), np.full(7, 1000.0)
    p = simulate.simulate(point, es, 1.0, 200, 7, "sqrt")
    errs = p.values - point
    for k in range(200):
        assert any(np.allclose(errs[k], row) for row in es.E)
        np.testing.assert_allclose(errs[k], es.E[p.draws[k]])


def test_relative_errors_scale_with_level_and_zeros_use_absolute():
    y = pd.Series(np.linspace(10, 100, 80) * (1 + 0.1 * np.sin(np.arange(80))))
    E = np.random.default_rng(1).normal(0, 5, (4, 7))
    es = simulate.error_matrix(_rows(E, [40, 47, 54, 61]), y, 7, relative=simulate.use_relative(y))
    assert es.relative
    np.testing.assert_allclose(es.E[0], E[0] / simulate.level(y, 40, 7))
    point = np.full(7, 1e4)
    s1 = simulate.simulate(point, es, 100.0, 200, 3, "none").values.std(axis=0)
    s2 = simulate.simulate(point, es, 200.0, 200, 3, "none").values.std(axis=0)
    np.testing.assert_allclose(s2, 2 * s1)
    assert not simulate.use_relative(pd.Series([3.0, 0.0, 5.0]))


def test_sqrt_growth_beyond_backtest_horizon():
    E = np.arange(1, 8, dtype=float)[None, :]  # H_cv = 7
    ext = simulate.extend_errors(E, 14, "sqrt")
    np.testing.assert_allclose(ext[0, :7], E[0])
    np.testing.assert_allclose(ext[0, 13], 7 * np.sqrt(14 / 7))
    np.testing.assert_allclose(simulate.extend_errors(E, 14, "none")[0, 7:], 7.0)


def test_paths_clipped_at_zero_and_counted():
    es = simulate.ErrorSet(E=np.array([[-50.0, 5.0], [10.0, -20.0]]), relative=False, folds=[0, 1], H=2)
    p = simulate.simulate(np.array([10.0, 10.0]), es, 1.0, 100, 0, "none")
    assert p.values.min() == 0.0
    assert p.n_clipped == int((np.array([[-40, 15], [20, -10]])[p.draws] < 0).sum())


def _spec(name, value):
    return ModelSpec(name, "ml", lambda train, h, ctx: Fit(forecast=np.full(h, value)))


def _series():
    return pd.Series(100 + 10 * np.sin(np.arange(60) * 2 * np.pi / 7), index=pd.RangeIndex(60))


def test_sanity_guard_falls_back_to_seasonal_naive():
    chosen = {"name": "x", "chosen_model": "boom", "family": "ml", "params": {}, "grain": "daily"}
    res = point_forecast(chosen, _series(), 7, {"season": 7, "nonneg": True}, {"boom": _spec("boom", 1e9)})
    assert res.fallback and res.model_used == "seasonal_naive"
    np.testing.assert_allclose(res.forecast, _series().iloc[-7:].to_numpy())


def test_ensemble_is_mean_of_members():
    chosen = {"name": "x", "chosen_model": "ensemble", "grain": "daily",
              "params": {"components": [{"model": "a", "params": {}}, {"model": "b", "params": {}}]}}
    fc = model_forecast(chosen, _series(), 5, {"season": 7, "nonneg": True}, {"a": _spec("a", 2.0), "b": _spec("b", 4.0)})
    np.testing.assert_allclose(fc, 3.0)


def _table(n=200, h=3):
    paths = np.full((n, h), 5.0)
    return export.build_table("d", np.ones(h), paths, [""] * h, "tokens", "m", "burstgpt", "daily")


def test_validator_passes_good_table_and_catches_errors():
    good = _table()
    assert validate.check_forecast_table(good, 3) == []
    assert validate.check_forecast_table(good.drop(columns="unit"), 3)
    assert validate.check_forecast_table(good[list(reversed(P3.COLUMNS))], 3)
    neg = good.copy()
    neg.loc[5, "value"] = -1.0
    assert validate.check_forecast_table(neg, 3)
    assert validate.check_forecast_table(_table(n=199), 3)
    assert validate.check_forecast_table(pd.concat([good, good.iloc[[0]]], ignore_index=True), 3)


def test_coverage_near_nominal_on_normal_errors():
    rng = np.random.default_rng(42)
    paths, actual = rng.normal(size=(200, 400)), rng.normal(size=400)
    assert abs(simulate.coverage(paths, actual, 0.8) - 0.80) <= 0.12
    assert abs(simulate.coverage(paths, actual, 0.95) - 0.95) <= 0.12


def test_scenario_validator_rejects_missing_source_or_derivation():
    ok = pd.DataFrame([{"scenario": "expected", "parameter": "p", "value": 1.0, "unit": "pct", "source": "s",
                        "derivation": "d", "status": "measured", "kind": "assumption"}])
    assert validate.check_scenarios(ok) == []
    assert validate.check_scenarios(ok.assign(source=""))
    assert validate.check_scenarios(ok.assign(derivation=np.nan))


def test_ensemble_residuals_rebuilt_from_member_folds():
    from tsaf.pipeline_phase3 import ensemble_residuals
    base = {"driver": "d", "fold": 0, "origin_index": 10, "actual": 10.0}
    folds = pd.DataFrame([{**base, "model": "a", "step_ahead": 1, "forecast": 6.0},
                          {**base, "model": "b", "step_ahead": 1, "forecast": 8.0}])
    r = ensemble_residuals(folds, "d", ["a", "b"])
    assert r["model"].iloc[0] == "ensemble" and r["forecast"].iloc[0] == 7.0 and r["error"].iloc[0] == 3.0


def test_recency_weights_halve_with_age_and_sum_to_one():
    w = simulate.recency_weights([40, 10, 30, 20], 0.25)  # n = 4 -> half-life 1 fold
    assert abs(w.sum() - 1) < 1e-12
    order = np.argsort([40, 10, 30, 20])                # oldest .. newest
    np.testing.assert_allclose(w[order][1:] / w[order][:-1], 2.0)
    es = simulate.ErrorSet(E=np.eye(4), relative=False, folds=[0, 1, 2, 3], H=4, origins=[40, 10, 30, 20])
    a = simulate.simulate(np.full(4, 10.0), es, 1.0, 400, 5, "none", weights=w)
    b = simulate.simulate(np.full(4, 10.0), es, 1.0, 400, 5, "none", weights=w)
    np.testing.assert_array_equal(a.values, b.values)
    counts = np.bincount(a.draws, minlength=4)
    assert counts[0] > counts[2] > counts[3] > counts[1]  # newest (origin 40) drawn most


def _lvl_es(levels):
    n = len(levels)
    return simulate.ErrorSet(E=np.ones((n, 3)), relative=True, folds=list(range(n)), H=3,
                             origins=list(range(0, 10 * n, 10)), levels=np.asarray(levels, dtype=float))


def test_level_match_band_and_closest_fallback():
    es, note = simulate.level_match(_lvl_es([1, 10, 20, 40]), 20.0, (0.5, 2.0))
    assert es.levels.tolist() == [10, 20, 40] and "3 of 4" in note
    es2, note2 = simulate.level_match(_lvl_es([1, 10, 20, 40]), 100.0, (0.5, 2.0))
    assert sorted(es2.levels.tolist()) == [10, 20, 40] and "closest" in note2
    absolute = simulate.ErrorSet(E=np.ones((2, 3)), relative=False, folds=[0, 1], H=3)
    assert simulate.level_match(absolute, 5.0, (0.5, 2.0))[0] is absolute


def test_pseudo_holdout_never_reads_the_final_holdout():
    from tsaf.pipeline_phase3 import tune
    rng = np.random.default_rng(3)
    n, hold, H = 120, 14, 7
    s = pd.Series(50 + 10 * np.sin(np.arange(n) * 2 * np.pi / 7) + rng.normal(0, 2, n))
    origins = list(range(42, n - hold - H + 1, 7))
    rows = pd.DataFrame([{"fold": f, "origin_index": o, "step_ahead": k + 1, "error": rng.normal(0, 3),
                          "forecast": 50.0} for f, o in enumerate(origins) for k in range(H)])
    entry = {"season": 7, "cv_settings": {"holdout": hold}}
    _, why1, t1 = tune(rows, s, entry, "d", 42)
    s2 = s.copy()
    s2.iloc[-hold:] = 1e12  # garbage in the final holdout must change nothing
    _, why2, t2 = tune(rows, s2, entry, "d", 42)
    pd.testing.assert_frame_equal(t1, t2)
    assert why1 == why2 and len(t1) == 4
    late = rows.assign(origin_index=rows["origin_index"] + 20)  # a fold reaching into the holdout is refused
    with pytest.raises(ValueError):
        tune(late, s, entry, "d", 42)


def test_choice_rule_closest_to_80_then_narrower():
    from tsaf import tune_intervals
    grid = tune_intervals.option_grid()
    rows = [{"recency": o["recency"], "level_match": o["level_match"], "option": tune_intervals.label(o),
             "n_heldout_folds": 2, "n_points": 10, "coverage_80": c, "coverage_95": 0.9,
             "mean_width_80_relative_to_level": w} for o, c, w in zip(grid, [0.5, 0.75, 0.85, 0.75], [1.0, 2.0, 1.0, 1.5])]
    opt, _ = tune_intervals.choose(pd.DataFrame(rows))
    assert tune_intervals.label(opt) == tune_intervals.label(grid[2])  # 0.75 and 0.85 tie at 0.05; width 1.0 is narrowest
    off, why = tune_intervals.choose(pd.DataFrame())
    assert off == grid[0] and "not possible" in why
