"""Stationarity testing and the differencing decision (syllabus Module 3: ARIMA preparation).

ADF (null: unit root) and KPSS (null: stationary) are run on the series after d ordinary
and D seasonal differences. Stationary means ADF p < 0.05 AND KPSS p > 0.05. The chosen
(d, D) is the first candidate, in order of smallest d then smallest D, where both agree.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

ALPHA = 0.05
COLUMNS = ["driver", "d", "D", "adf_stat", "adf_p", "kpss_stat", "kpss_p", "verdict"]


def difference(s: pd.Series, d: int, D: int, season: int | None) -> pd.Series:
    """Apply D seasonal differences (lag = season) then d ordinary differences."""
    x = s.astype(float)
    for _ in range(D):
        x = x - x.shift(season)
    for _ in range(d):
        x = x.diff()
    return x.dropna()


def run_tests(x: pd.Series) -> dict:
    """ADF (autolag AIC) and KPSS (level, nlags auto) with warnings captured as notes."""
    out = {"adf_stat": np.nan, "adf_p": np.nan, "kpss_stat": np.nan, "kpss_p": np.nan, "note": ""}
    if len(x) < 10 or np.isclose(x.std(), 0):
        out["note"] = "constant or too short: tests skipped"
        return out
    notes = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stat, p, *_ = adfuller(x, autolag="AIC")
        out.update(adf_stat=float(stat), adf_p=float(p))
    except Exception as exc:  # noqa: BLE001 - recorded, never raised
        notes.append(f"ADF failed: {exc}")
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            stat, p, *_ = kpss(x, regression="c", nlags="auto")
        out.update(kpss_stat=float(stat), kpss_p=float(p))
        if any(issubclass(w.category, InterpolationWarning) for w in caught):
            notes.append("KPSS p-value at the table bound")
    except Exception as exc:  # noqa: BLE001
        notes.append(f"KPSS failed: {exc}")
    out["note"] = "; ".join(notes)
    return out


def verdict(adf_p: float, kpss_p: float) -> str:
    """Plain-language result of the joint decision rule."""
    if not (np.isfinite(adf_p) and np.isfinite(kpss_p)):
        return "not tested"
    adf_ok, kpss_ok = adf_p < ALPHA, kpss_p > ALPHA
    if adf_ok and kpss_ok:
        return "stationary"
    if not adf_ok and not kpss_ok:
        return "non-stationary"
    return "tests disagree (ADF says stationary)" if adf_ok else "tests disagree (KPSS says stationary)"


def candidates(season: int | None) -> list[tuple[int, int]]:
    """(d, D) pairs in decision order: smallest d first, then smallest D."""
    seasonal = bool(season and season > 1)
    pairs = [(0, 0), (1, 0), (2, 0)] + ([(0, 1), (1, 1)] if seasonal else [])
    return sorted(pairs)


def stationarity_table(s: pd.Series, name: str, season: int | None) -> pd.DataFrame:
    """One row per (d, D) candidate with both tests and the verdict."""
    rows = []
    for d, D in candidates(season):
        res = run_tests(difference(s, d, D, season))
        v = verdict(res["adf_p"], res["kpss_p"])
        if res["note"]:
            v = f"{v} [{res['note']}]"
        rows.append({"driver": name, "d": d, "D": D, **{k: res[k] for k in COLUMNS[3:7]},
                     "verdict": v})
    return pd.DataFrame(rows, columns=COLUMNS)


def choose_differencing(table: pd.DataFrame) -> dict:
    """First (d, D) where both tests agree on stationarity; else difference once and flag."""
    for _, r in table.iterrows():
        if str(r["verdict"]).startswith("stationary"):
            return {"d": int(r["d"]), "D": int(r["D"]), "tests_agree": True,
                    "decision": f"d={int(r['d'])}, D={int(r['D'])}: ADF and KPSS agree"}
    return {"d": 1, "D": 0, "tests_agree": False,
            "decision": "tests disagree at every level tried, difference once to be safe (flagged)"}
