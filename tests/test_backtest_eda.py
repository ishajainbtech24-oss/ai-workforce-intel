"""Backtest leakage checks, stationarity decisions and the semi-averages slope."""
import numpy as np
import pandas as pd

from tsaf import backtest, baselines, eda, stationarity


def test_folds_never_train_on_test_and_expand():
    s = pd.Series(np.arange(100, dtype=float))
    seen = {}

    def spy(train, h, season):
        seen[len(seen)] = (train.index.max(), len(train))
        return baselines.naive(train, h)

    df = backtest.rolling_origin(s, spy, h=7, initial=42, step=7, max_folds=None, season=7)
    for fold, g in df.groupby("fold"):
        last_train, n_train = seen[fold]
        assert last_train < g["time"].min()
        assert n_train == g["origin_index"].iloc[0]
    sizes = [seen[k][1] for k in sorted(seen)]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    assert df.groupby("fold")["time"].max().max() <= 99


def test_holdout_split_has_no_overlap():
    s = pd.Series(np.arange(30, dtype=float))
    train, test = backtest.holdout_split(s, 8)
    assert len(test) == 8 and len(train) == 22
    assert train.index.max() < test.index.min()
    assert set(train.index).isdisjoint(test.index)


def test_resolve_settings_share_and_fast_cap():
    cv = backtest.resolve_settings({"initial": 0.6, "h": 4, "step": 4, "holdout": 8, "max_folds": None},
                                   n=50, max_folds=3)
    assert cv["initial"] == 30 and cv["max_folds"] == 3


def test_white_noise_is_stationary_at_d0():
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(size=400))
    choice = stationarity.choose_differencing(stationarity.stationarity_table(s, "wn", None))
    assert (choice["d"], choice["D"], choice["tests_agree"]) == (0, 0, True)


def test_random_walk_needs_one_difference():
    rng = np.random.default_rng(42)
    s = pd.Series(np.cumsum(rng.normal(size=400)))
    table = stationarity.stationarity_table(s, "rw", None)
    assert table.loc[table["d"] == 0, "verdict"].iloc[0].split(" [")[0] != "stationary"
    choice = stationarity.choose_differencing(table)
    assert (choice["d"], choice["D"]) == (1, 0)


def test_semi_averages_slope_on_straight_line():
    for n in (20, 21):
        slope, icpt = eda.semi_averages(4.0 + 2.5 * np.arange(n))
        assert np.isclose(slope, 2.5) and np.isclose(icpt, 4.0)


def test_decomposition_rule():
    t = np.arange(140)
    level = 100 + 5 * t
    mult = pd.Series(level * (1 + 0.3 * np.sin(2 * np.pi * t / 7)))
    add = pd.Series(level + 30 * np.sin(2 * np.pi * t / 7))
    assert eda.choose_decomposition(mult, 7)["type"] == "multiplicative"
    assert eda.choose_decomposition(add, 7)["type"] == "additive"
    assert eda.choose_decomposition(add - 10_000, 7)["type"] == "additive"  # negatives
