"""Loader rules: longest clean run, partial periods treated as missing, no filling."""
import numpy as np
import pandas as pd
import pytest

from tsaf.loaders import SkipDriver, load_driver, longest_run


def test_longest_run():
    assert longest_run(np.array([1, 1, 0, 1, 1, 1, 0, 1], dtype=bool)) == (3, 5)
    assert longest_run(np.array([0, 0], dtype=bool)) == (0, -1)
    assert longest_run(np.array([1, 1, 1], dtype=bool)) == (0, 2)


def _weekly_cfg() -> dict:
    return {"name": "w", "file": "weekly", "value_col": "conversations", "filter": None,
            "grain": "weekly", "season": None, "min_obs": 5, "index_col": "week",
            "source": "wildchat", "invalid_col": "partial_week"}


def test_partial_week_inside_series_skips_driver(tmp_path):
    weeks = pd.date_range("2024-01-01", periods=12, freq="W-MON")
    partial = np.zeros(12, dtype=bool)
    partial[[0, 6, 11]] = True
    pd.DataFrame({"week": weeks, "conversations": np.arange(12.0) + 100,
                  "partial_week": partial}).to_parquet(tmp_path / "weekly.parquet")
    with pytest.raises(SkipDriver, match="longest complete run is 5"):
        load_driver(_weekly_cfg(), tmp_path)


def test_partial_weeks_at_ends_are_trimmed(tmp_path):
    weeks = pd.date_range("2024-01-01", periods=12, freq="W-MON")
    partial = np.zeros(12, dtype=bool)
    partial[[0, 11]] = True
    pd.DataFrame({"week": weeks, "conversations": np.arange(12.0) + 100,
                  "partial_week": partial}).to_parquet(tmp_path / "weekly.parquet")
    ld = load_driver(_weekly_cfg(), tmp_path)
    assert len(ld.series) == 10 and ld.series.index[0] == weeks[1]
    assert ld.series.index.freqstr == "W-MON"
