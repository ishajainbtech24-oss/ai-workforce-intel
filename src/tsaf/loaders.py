"""Load one driver as a clean, regularly spaced series (syllabus Module 1: the time series object).

`load_driver` returns the modelling series (BurstGPT restricted to the clean window), the
full series for context plots, and boolean flag columns (copied, low-activity, anomaly).
Nothing is interpolated or filled: NaN at the ends is dropped and reported, NaN in the
middle stops the driver with a `SkipDriver` error that the runner logs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
FLAG_COLS = ("copied_day", "low_activity", "anomaly_low_day", "partial_day", "missing_day")


class SkipDriver(Exception):
    """Raised when a driver cannot be analysed; the message is the logged reason."""


@dataclass
class LoadedDriver:
    """A loaded driver: modelling series, full-length context series, flags and notes."""
    series: pd.Series
    full: pd.Series
    flags: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def read_table(data_dir: Path, file: str) -> pd.DataFrame:
    """Read `<file>.parquet` (or `.csv`) from `data_dir`; SkipDriver if neither exists."""
    pq, csv = data_dir / f"{file}.parquet", data_dir / f"{file}.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    if csv.exists():
        return pd.read_csv(csv)
    raise SkipDriver(f"file '{file}' not found in {data_dir.parent.name}/{data_dir.name}")


def _value(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Return the value column, summing '+'-joined columns; SkipDriver if any is missing."""
    cols = value_col.split("+")
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SkipDriver(f"column(s) {missing} missing; available: {list(df.columns)}")
    vals = df[cols].apply(pd.to_numeric, errors="coerce")
    return vals.sum(axis=1, min_count=len(cols))


def _apply_window(df: pd.DataFrame, cfg: dict, notes: list[str]) -> pd.Series:
    """Boolean mask of rows inside the modelling window (all rows for non-BurstGPT)."""
    wcol = cfg.get("window_col")
    if not wcol:
        return pd.Series(True, index=df.index)
    if wcol in df.columns:
        return df[wcol].astype(bool)
    from config import BURST_WINDOW_DAYS  # local import keeps the module testable alone
    lo, hi = BURST_WINDOW_DAYS
    day = df["day_index"] if "day_index" in df.columns else df[cfg["index_col"]] // (
        24 if cfg["grain"] == "hourly" else 1)
    msg = f"'{wcol}' column missing: window rebuilt as days {lo}-{hi}"
    log.warning("%s: %s", cfg["name"], msg)
    notes.append(msg)
    return day.between(lo, hi)


def _flags(df: pd.DataFrame, cfg: dict, data_dir: Path) -> pd.DataFrame:
    """Flag columns present in the table; hourly BurstGPT borrows anomaly days from daily."""
    flags = pd.DataFrame({c: df[c].astype(bool) for c in FLAG_COLS if c in df.columns})
    if cfg.get("source") == "burstgpt" and "anomaly_low_day" not in flags and "day_index" in df:
        try:
            daily = read_table(data_dir, "burstgpt_daily_wide")
            if "anomaly_low_day" in daily.columns:
                days = daily.loc[daily["anomaly_low_day"].astype(bool), "day_index"]
                flags["anomaly_low_day"] = df["day_index"].isin(set(days)).to_numpy()
        except SkipDriver:
            pass
    return flags


def _to_index(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Sort and index the table by its time column; aggregate duplicates if configured."""
    icol = cfg["index_col"]
    if icol not in df.columns:
        raise SkipDriver(f"index column '{icol}' missing; available: {list(df.columns)}")
    if cfg.get("filter"):
        f = cfg["filter"]
        df = df[df[f["col"]] == f["value"]]
    if cfg.get("aggregate") == "sum":
        num = df.select_dtypes(include=[np.number, bool]).columns.drop(icol, errors="ignore")
        df = df.groupby(icol, as_index=False)[list(num)].sum(min_count=1)
    if df[icol].duplicated().any():
        raise SkipDriver(f"duplicate '{icol}' values; set a filter or aggregate in config")
    df = df.sort_values(icol).reset_index(drop=True)
    if cfg["grain"] in ("daily", "hourly") and cfg.get("source") == "burstgpt":
        return df.set_index(icol)
    from config import FREQ
    df[icol] = pd.to_datetime(df[icol])
    df = df.set_index(icol)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq=FREQ[cfg["grain"]])
    if len(full_idx) != len(df) or not full_idx.equals(df.index):
        df = df.reindex(full_idx)  # gaps become NaN and are judged by _check_nan
    df.index.freq = FREQ[cfg["grain"]]
    return df


def longest_run(mask: np.ndarray) -> tuple[int, int]:
    """(start, end) positions, inclusive, of the longest run of True; (0, -1) if none."""
    best, start, cur = (0, -1), None, 0
    for i, ok in enumerate(np.append(np.asarray(mask, dtype=bool), False)):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            if i - start > best[1] - best[0] + 1:
                best = (start, i - 1)
            start = None
    return best


def _clean_run_window(df: pd.DataFrame, cfg: dict, notes: list[str]) -> np.ndarray:
    """Window = longest run of rows with no missing data (config `missing_col` == 0)."""
    col = cfg["missing_col"]
    if col not in df.columns:
        raise SkipDriver(f"window rule needs column '{col}'; available: {list(df.columns)}")
    ok = (df[col].fillna(1) == 0).to_numpy()
    lo, hi = longest_run(ok)
    win = np.zeros(len(df), dtype=bool)
    win[lo:hi + 1] = True
    notes.append(f"modelling window = longest run without missing data: {df.index[lo]} to "
                 f"{df.index[hi]} ({hi - lo + 1} points; {int((~ok).sum())} flagged point(s) in the file)")
    return win


def _check_nan(s: pd.Series, name: str, notes: list[str]) -> pd.Series:
    """Drop NaN only at the ends; SkipDriver if NaN remains inside the series."""
    n0 = len(s)
    valid = s.notna().to_numpy()
    if not valid.any():
        raise SkipDriver("series is entirely NaN")
    first, last = int(np.argmax(valid)), int(len(valid) - 1 - np.argmax(valid[::-1]))
    s = s.iloc[first:last + 1]
    if n0 - len(s):
        notes.append(f"dropped {n0 - len(s)} NaN value(s) at the series ends")
    inner = int(s.isna().sum())
    if inner:
        lo, hi = longest_run(s.notna().to_numpy())
        where = ", ".join(str(t.date()) if isinstance(t, pd.Timestamp) else str(t)
                          for t in s.index[s.isna().to_numpy()][:4])
        raise SkipDriver(f"{inner} missing or partial value(s) inside the series ({where}); no filling "
                         f"allowed, and the longest complete run is {hi - lo + 1} points")
    return s


def load_driver(cfg: dict, data_dir: Path) -> LoadedDriver:
    """Load the driver described by `cfg` from `data_dir` (see module docstring)."""
    notes: list[str] = []
    raw = read_table(data_dir, cfg["file"])
    df = _to_index(raw, cfg)
    full = _value(df, cfg["value_col"]).rename(cfg["name"])
    bad = cfg.get("invalid_col")
    if bad and bad in df.columns:  # e.g. partial weeks: incomplete totals count as missing
        full = full.mask(df[bad].fillna(True).astype(bool))
    if cfg.get("last_is_partial"):  # download cut-off: the final period is incomplete
        full = full.copy()
        full.iloc[-1] = np.nan
        notes.append(f"last date in the file ({full.index[-1]}) is partial (download cut-off): dropped")
    if cfg.get("window_rule") == "longest_clean_run":
        in_window = _clean_run_window(df, cfg, notes)
    else:
        in_window = _apply_window(df.reset_index(), cfg, notes).to_numpy()
    flags = _flags(df.reset_index(), cfg, data_dir).set_axis(df.index)
    s = _check_nan(full[in_window], cfg["name"], notes)
    if isinstance(s.index, pd.DatetimeIndex):
        s.index.freq = df.index.freq
    else:
        if not np.array_equal(s.index.to_numpy(), np.arange(s.index[0], s.index[0] + len(s))):
            raise SkipDriver("integer index is not consecutive inside the window")
        s.index = pd.RangeIndex(int(s.index[0]), int(s.index[0]) + len(s), name=df.index.name)
    zero_share = float((s == 0).mean())
    if zero_share > cfg.get("max_zero_share", 1.0):
        raise SkipDriver(f"{zero_share:.0%} zero values in the window (limit "
                         f"{cfg['max_zero_share']:.0%})")
    if len(s) < cfg["min_obs"]:
        raise SkipDriver(f"only {len(s)} observations; needs at least {cfg['min_obs']}")
    return LoadedDriver(series=s.astype(float), full=full.astype(float), flags=flags, notes=notes)
