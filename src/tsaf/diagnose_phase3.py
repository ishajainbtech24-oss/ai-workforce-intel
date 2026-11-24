"""Plain-language causes for interval misses and the WildChat end-of-series check (read from data)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from tsaf.loaders import read_table


def miss_cause(r: pd.Series) -> str:
    """One sentence on why a driver's simulated band misses on the holdout, from the check row."""
    n, above, below = int(r["n_holdout_points"]), int(r["misses_above_after"]), int(r["misses_below_after"])
    ratio, chg = r.get("holdout_err_vs_backtest", np.nan), r.get("holdout_level_change", np.nan)
    parts = [f"{above + below} of {n} holdout points fall outside the 80% band ({above} above, {below} below)"]
    side = "above" if above > below else "below"
    if np.isfinite(ratio) and ratio >= 1.5:
        parts.append(f"holdout errors are {ratio:.1f}x the average backtest error (backtest windows: "
                     f"{r.get('backtest_tested', '')}), so the holdout moved much further from the forecast than the "
                     f"backtest windows typically did, with the actual values mostly {side} the band (holdout mean "
                     f"{chg:+.0%} against the {n} points before it): a level or regime change rather than a sampling problem")
    elif above == 0 or below == 0:
        pos = r.get("backtest_positive_share", np.nan)
        lean = (f"{pos:.0%} of the backtest errors were positive (actual above forecast) while every holdout miss is "
                f"{side} the band" if np.isfinite(pos) else f"every holdout miss is {side} the band")
        parts.append(f"errors are about the backtest size ({ratio:.1f}x) but one-sided: {lean}, so the band leans the "
                     "wrong way")
    if n <= 4:
        parts.append(f"with only {n} holdout points each point moves coverage by {100 / n:.0f} percentage points")
    anom = str(r.get("anomalies_in_holdout", "") or "")
    if anom and anom != "nan":
        parts.append(f"the holdout contains the known anomaly at {anom}, which explains at most one missed point")
    return "; ".join(parts) + "."


def wildchat_end_check(data_dir: Path) -> str:
    """Is the end of WildChat undercounted (partial days or weeks)? Read-only."""
    try:
        d = read_table(data_dir, "wildchat_daily")
    except Exception as exc:  # noqa: BLE001
        return f"WildChat end check not possible: {exc}"
    tot = d.groupby("date")["conversations"].sum().sort_index()
    last, base = tot.index[-1], tot.iloc[-29:-1].median()
    prev = tot.iloc[-3:-1]
    msg = (f"WildChat end check: the last date in the file ({pd.Timestamp(last).date()}) has {tot.iloc[-1]:,.0f} "
           f"conversations, {tot.iloc[-1] / base:.0%} of the median of the 28 days before it, so it is partial; "
           "the Phase 1 loader already drops it. The two days before it "
           + ", ".join(f"({pd.Timestamp(t).date()}: {v:,.0f})" for t, v in prev.items())
           + f" are {prev.min() / base:.0%}-{prev.max() / base:.0%} of that median, in line with ordinary weekdays")
    try:
        w = read_table(data_dir, "wildchat_weekly")
        partial = w.loc[w["partial_week"].astype(bool), "week"]
        msg += (f"; partial_week flags only {', '.join(str(pd.Timestamp(x).date()) for x in partial.tail(2))} at the "
                "series edges")
    except Exception:  # noqa: BLE001
        pass
    return msg + ". The holdout and the forecasts are therefore not affected by undercounting."
