"""Exploratory analysis (syllabus Module 1: components of a time series and trend measurement).

Summary statistics, the additive-vs-multiplicative rule, classical / STL / MSTL
decomposition with seasonal and trend strength, the four trend-measurement methods
(semi-averages, centred moving average, least squares linear and quadratic), the
variance-stabilisation check and a robust anomaly screen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import skew
from statsmodels.tsa.seasonal import MSTL, STL, seasonal_decompose

MULT_CORR_THRESHOLD = 0.5
ANOMALY_Z = 3.5


def _label(t) -> str:
    """Index label as text: dates without a midnight time part."""
    return str(t.date()) if isinstance(t, pd.Timestamp) and t == t.normalize() else str(t)


def summary_stats(s: pd.Series) -> dict:
    """n, range, moments, share of zeros, coefficient of variation, skewness and NaN count."""
    mean = float(s.mean())
    return {"n": int(s.size), "start": _label(s.index[0]), "end": _label(s.index[-1]), "mean": mean,
            "std": float(s.std()), "min": float(s.min()), "max": float(s.max()),
            "zero_share": float((s == 0).mean()),
            "cv": float(s.std() / mean) if mean else float("nan"),
            "skewness": float(skew(s.dropna())), "n_nan": int(s.isna().sum())}


def _roll_corr(s: pd.Series, window: int) -> float:
    """Correlation between rolling std and rolling mean (NaN if undefined)."""
    roll = s.rolling(window)
    m, sd = roll.mean(), roll.std()
    ok = m.notna() & sd.notna()
    if ok.sum() < 3 or m[ok].std() == 0 or sd[ok].std() == 0:
        return float("nan")
    return float(np.corrcoef(m[ok], sd[ok])[0, 1])


def choose_decomposition(s: pd.Series, period: int | None) -> dict:
    """Additive vs multiplicative rule, plus the log variance-stabilisation check."""
    window = period if period and period > 1 else 4
    positive = bool((s > 0).all())
    corr = _roll_corr(s, window)
    log_corr = _roll_corr(np.log(s), window) if positive else float("nan")
    mult = positive and np.isfinite(corr) and corr > MULT_CORR_THRESHOLD
    if not positive:
        reason = "series has zero or negative values, so multiplicative is not possible"
    elif mult:
        reason = f"rolling std rises with rolling mean (corr {corr:.2f} > {MULT_CORR_THRESHOLD})"
    else:
        reason = f"rolling std does not track rolling mean (corr {corr:.2f} <= {MULT_CORR_THRESHOLD})"
    log_reduces = bool(positive and np.isfinite(log_corr) and abs(log_corr) < abs(corr))
    return {"type": "multiplicative" if mult else "additive", "roll_corr": corr,
            "reason": reason, "strictly_positive": positive, "log_roll_corr": log_corr,
            "log_reduces_corr": log_reduces, "log_candidate": log_reduces}


def _strength(part: pd.Series, resid: pd.Series) -> float:
    """1 - Var(R)/Var(part + R), floored at 0 (Hyndman's strength measure)."""
    ok = part.notna() & resid.notna()
    denom = np.var(part[ok] + resid[ok])
    return float(max(0.0, 1 - np.var(resid[ok]) / denom)) if denom > 0 else float("nan")


def decompose(s: pd.Series, cfg: dict, dtype: str) -> tuple[dict, dict]:
    """Classical + STL (or MSTL for multiple seasons). Returns (info row, component frames)."""
    period = cfg["season"] or 1
    periods = [period] + list(cfg.get("extra_seasons") or [])
    info: dict = {"period": period, "classical": "skipped", "method": "skipped",
                  "stl_scale": "", "seasonal_strength": np.nan, "trend_strength": np.nan}
    comps: dict[str, pd.DataFrame] = {}
    if period <= 1 or len(s) < 2 * max(periods):
        info["note"] = ("no seasonal period" if period <= 1 else
                        f"fewer than 2 full cycles of {max(periods)}")
        return info, comps
    if len(periods) == 1:
        cd = seasonal_decompose(s, model=dtype, period=period)
        comps["classical"] = pd.DataFrame({"observed": cd.observed, "trend": cd.trend,
                                           "seasonal": cd.seasonal, "remainder": cd.resid})
        info["classical"] = dtype
    use_log = dtype == "multiplicative"
    x = np.log(s) if use_log else s
    if len(periods) > 1:
        res = MSTL(x, periods=periods).fit()
        seas = res.seasonal.sum(axis=1)
        for p, col in zip(periods, res.seasonal.columns):
            info[f"seasonal_strength_{p}"] = _strength(res.seasonal[col], res.resid)
        info["method"] = f"MSTL{tuple(periods)}"
    else:
        res = STL(x, period=period, robust=True).fit()
        seas = res.seasonal
        info["method"] = "STL (robust)"
    comps["stl"] = pd.DataFrame({"observed": x, "trend": res.trend, "seasonal": seas,
                                 "remainder": res.resid})
    info["stl_scale"] = "log" if use_log else "raw"
    info["seasonal_strength"] = _strength(seas, res.resid)
    info["trend_strength"] = _strength(res.trend, res.resid)
    return info, comps


def semi_averages(y: np.ndarray) -> tuple[float, float]:
    """Semi-average trend: (slope, intercept). With odd n the middle point is dropped."""
    y = np.asarray(y, dtype=float)
    t = np.arange(len(y), dtype=float)
    half = len(y) // 2
    t1, y1 = t[:half], y[:half]
    t2, y2 = t[len(y) - half:], y[len(y) - half:]
    slope = (y2.mean() - y1.mean()) / (t2.mean() - t1.mean())
    return float(slope), float(y1.mean() - slope * t1.mean())


def centred_ma(y: pd.Series, period: int) -> pd.Series:
    """Centred moving average; 2xMA for an even period so it stays centred."""
    ma = y.rolling(period, center=True).mean()
    if period % 2 == 0:
        ma = ma.rolling(2).mean().shift(-1)
    return ma


def trend_methods(s: pd.Series, period: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare four trend measures. Returns (slope table, fitted lines per method)."""
    y = s.to_numpy(dtype=float)
    t = np.arange(len(y), dtype=float)
    sa_slope, sa_icpt = semi_averages(y)
    cma = centred_ma(pd.Series(y), period)
    ok = cma.notna().to_numpy()
    cma_slope = float(np.polyfit(t[ok], cma[ok], 1)[0])
    lin = np.polyfit(t, y, 1)
    quad = np.polyfit(t, y, 2)
    t_end = t[-1]
    rows = [
        ("semi_averages", sa_slope, "difference of the two half means / distance between their centres"),
        ("centred_moving_average", cma_slope, f"least squares slope of the {period}-point centred MA"),
        ("least_squares_linear", float(lin[0]), "b in y = a + b t"),
        ("least_squares_quadratic", float(quad[1] + 2 * quad[0] * t_end),
         f"slope b + 2ct at the end of the window (t={t_end:.0f}), c={quad[0]:.4g}; "
         "at the middle it equals the linear slope"),
    ]
    table = pd.DataFrame(rows, columns=["method", "slope_per_step", "how"])
    table["slope_pct_of_mean"] = 100 * table["slope_per_step"] / y.mean()
    lines = pd.DataFrame({"actual": y, "semi_averages": sa_icpt + sa_slope * t,
                          "centred_moving_average": cma.to_numpy(),
                          "least_squares_linear": np.polyval(lin, t),
                          "least_squares_quadratic": np.polyval(quad, t)}, index=s.index)
    return table, lines


def robust_z(s: pd.Series, season: int | None, log_scale: bool = False) -> tuple[pd.Series, pd.Series]:
    """Seasonal-naive residual and its robust z-score 0.6745*(r - median)/MAD.

    For a multiplicative series the residual is taken on the log scale (a ratio to the
    value one season earlier), consistent with the decomposition choice.
    """
    m = season if season and season > 1 else 1
    x = np.log(s) if log_scale else s
    resid = x - x.shift(m)
    med = resid.median()
    mad = (resid - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return resid, pd.Series(np.nan, index=s.index)
    return resid, 0.6745 * (resid - med) / mad


def stl_remainder_z(s: pd.Series, period: int, log_scale: bool) -> pd.Series:
    """Robust z-score of the robust-STL remainder (used only as a comparison screen)."""
    x = np.log(s) if log_scale else s
    r = STL(x, period=period, robust=True).fit().resid
    mad = (r - r.median()).abs().median()
    return 0.6745 * (r - r.median()) / mad if mad > 0 else pd.Series(np.nan, index=s.index)


def anomaly_screen(s: pd.Series, season: int | None, log_scale: bool = False,
                   z: float = ANOMALY_Z) -> pd.DataFrame:
    """Flag |robust z| > z on the seasonal-naive residual; a screen, not a model."""
    resid, rz = robust_z(s, season, log_scale)
    hit = (rz.abs() > z).to_numpy()
    return pd.DataFrame({"time": s.index[hit], "value": s[hit].to_numpy(),
                         "residual": resid[hit].to_numpy(), "robust_z": rz[hit].to_numpy(),
                         "scale": "log" if log_scale else "raw"})
