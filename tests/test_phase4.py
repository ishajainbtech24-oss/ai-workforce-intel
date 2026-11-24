"""Phase 4 engine: line items, break-even, multiplier, extrapolation, cohorts, validation, speed."""
import time

import numpy as np
import pandas as pd
import pytest

from engine import model
from engine.drivers import Driver, DriverPaths, _flat_extend
from engine.inputs import InputError, validate
from engine.simulate import ScenarioSkipped, run_engine, scenario_fraction, summarise, widen

T = 12


def _inputs(**over) -> dict:
    base = {"employees": 100, "adoption_start": 0.1, "adoption_target": 0.5, "ramp_months": 4, "ramp_shape": "linear",
            "tokens_per_active_user_per_month": 2e6, "price_multiplier_vs_frontier": 1.0,
            "fixed_token_price_per_mtok": 5.0, "base_monthly_hosting_cost": 1000.0, "base_hourly_wage_staff": 40.0,
            "base_hourly_wage_engineer": 70.0, "training_hours_per_new_user": 6.0,
            "refresher_hours_per_user_per_year": 4.0, "fixed_enablement_cost_per_month": 500.0,
            "engineering_hours_build": 300.0, "build_months": 3, "maintenance_share_per_month": 0.02,
            "maintenance_during_build": False, "work_hours_per_user_per_month": 160.0, "realisation_rate": 0.5,
            "benefit_lag_months": 2, "ai_assisted_share_of_hours": 0.25, "horizon_months": T}
    return validate({**base, **over})


def _drv(role, covered=T, spread=0.05, seed=0, fallback=False) -> Driver:
    rng = np.random.default_rng(seed)
    vals = np.vstack([np.ones(T), 1 + rng.normal(0, spread, (200, T))])
    return Driver(role, role, np.maximum(vals, 0), covered, T, used_fallback=fallback)


def _drivers(**covered) -> DriverPaths:
    dp = DriverPaths(T=T)
    for i, r in enumerate(("token_demand", "wages", "hosting")):
        dp.drivers[r] = _drv(r, covered.get(r, T), seed=i)
    dp.drivers["token_price"] = _drv("token_price", spread=0.0, fallback=True)
    return dp


SC = pd.DataFrame([{"scenario": "expected", "parameter": "time_saved_share_of_work_hours", "value": 4.0,
                    "unit": "pct_of_work_hours", "status": "measured"},
                   {"scenario": "downside", "parameter": "task_time_change_with_ai", "value": 20.0,
                    "unit": "pct_change_in_task_time", "status": "from_quality_log"},
                   {"scenario": "optimistic", "parameter": "time_saved_share_of_work_hours", "value": 5.0,
                    "unit": "pct_of_work_hours", "status": "needs_review"}])


def _run(inp=None, dp=None, **kw):
    return run_engine(inp or _inputs(), kw.pop("scenario", "expected"), kw.pop("k", 1.0), kw.pop("n", 500),
                      kw.pop("seed", 42), dp or _drivers(), SC, **kw)


def test_zero_adoption_gives_zero_token_cost_and_value():
    r = _run(_inputs(adoption_start=0.0, adoption_target=0.0))
    assert np.all(r.lines["token_expenditure"] == 0) and np.all(r.value == 0)


def test_doubling_employees_doubles_token_cost_and_value():
    a, b = _run(_inputs()), _run(_inputs(employees=200))
    np.testing.assert_allclose(b.lines["token_expenditure"], 2 * a.lines["token_expenditure"])
    np.testing.assert_allclose(b.value, 2 * a.value)


def test_doubling_price_doubles_only_token_expenditure():
    a, b = _run(_inputs()), _run(_inputs(fixed_token_price_per_mtok=10.0))
    np.testing.assert_allclose(b.lines["token_expenditure"], 2 * a.lines["token_expenditure"])
    for ln in ("hosting", "enablement", "integration"):
        np.testing.assert_array_equal(a.lines[ln], b.lines[ln])


def test_zero_and_negative_time_saved():
    z = _run(time_saved_fraction=0.0)
    assert np.all(z.value == 0) and np.all(np.isnan(z.break_even))
    d = _run(scenario="downside")
    assert d.meta["time_saved_fraction"] < 0 and np.all(d.value.sum(axis=1) < 0)


def test_components_add_up():
    r = _run()
    np.testing.assert_allclose(r.total_cost, sum(r.lines.values()))
    np.testing.assert_allclose(r.cum_net, np.cumsum(r.value - r.total_cost, axis=1))


def test_break_even_by_hand_and_never():
    cum = np.cumsum(np.array([[-5.0, 3.0, 4.0, 1.0], [-5.0, -1.0, -1.0, -1.0]]), axis=1)  # [-5,-2,2,3] / never
    be = model.break_even(cum)
    assert be[0] == 3 and np.isnan(be[1])
    s = summarise(_run(time_saved_fraction=0.0))
    assert s["break_even"]["share_none"] == 1.0 and s["break_even"]["prob_within_T"] == 0.0


def test_uncertainty_multiplier():
    vals = np.array([[10.0, 10.0], [12.0, 9.0], [8.0, 11.0]])
    np.testing.assert_allclose(widen(vals, 0.0), [[10, 10], [10, 10]])
    np.testing.assert_allclose(widen(vals, 2.0) - 10.0, 2 * (vals[1:] - 10.0))
    r0 = _run(k=0.0)
    assert np.ptp(r0.lines["hosting"], axis=0).max() == 0


def test_flat_extrapolation_and_counting():
    arr = np.arange(1, 7, dtype=float)[None, :]
    np.testing.assert_array_equal(_flat_extend(arr, 9)[0], [1, 2, 3, 4, 5, 6, 6, 6, 6])
    r = _run(dp=_drivers(hosting=6))
    ex = r.meta["extrapolation"]["per_driver"]["hosting"]
    assert ex["extrapolated"] == 6 and ex["covered"] == 6
    expected_share = r.lines["hosting"][:, 6:].sum() / r.total_cost.sum()
    assert abs(ex["share_of_total_cost"] - expected_share) < 1e-12


def test_cohort_ramp_matches_slow_loop():
    E = model.effective_users(10.0, np.array([5.0, 0, 0]), lag=1)
    np.testing.assert_allclose(E, [10.0, 15.0, 15.0])  # month-1 cohort counts from month 2
    rng = np.random.default_rng(1)
    for lag in (0, 1, 3, 5):
        N = rng.uniform(0, 20, 10)
        np.testing.assert_allclose(model.effective_users(7.0, N, lag), model.effective_users_loop(7.0, N, lag))


def test_reproducible_with_seed():
    a, b, c = _run(seed=7), _run(seed=7), _run(seed=8)
    np.testing.assert_array_equal(a.cum_net, b.cum_net)
    assert not np.array_equal(a.cum_net, c.cum_net)


@pytest.mark.parametrize("bad,msg", [({"employees": -1}, "employees"), ({"adoption_target": 1.5}, "between 0 and 1"),
                                     ({"build_months": 0}, "build_months"), ({"realisation_rate": -0.1}, "realisation")])
def test_input_validation(bad, msg):
    with pytest.raises(InputError, match=msg):
        _inputs(**bad)
    raw = dict(_inputs())
    del raw["work_hours_per_user_per_month"]
    with pytest.raises(InputError, match="missing required field 'work_hours_per_user_per_month'"):
        validate(raw)


def test_scenario_conversion_and_needs_review():
    inp = _inputs()
    assert scenario_fraction(SC, "expected", inp)[0] == pytest.approx(0.04)
    assert scenario_fraction(SC, "downside", inp)[0] == pytest.approx(-0.20 * 0.25)
    with pytest.raises(ScenarioSkipped, match="needs_review"):
        scenario_fraction(SC, "optimistic", inp)


def test_speed_2000_draws():
    dp, inp = _drivers(), _inputs()
    t0 = time.time()
    run_engine(inp, "expected", 1.0, 2000, 42, dp, SC)
    assert time.time() - t0 < 2.0
