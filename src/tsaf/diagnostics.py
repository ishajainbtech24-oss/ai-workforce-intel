"""Residual diagnostics and anomaly detection for each driver's chosen model (Modules 3 and 4).

The chosen model is refit on the data before the hold-out; its in-sample one-step residuals
(for ML: predictions from actual lags) are checked with Ljung-Box (lags 10 and 2 x season),
mean / std / skewness and Shapiro-Wilk. Anomalies use a robust z-score (median, MAD) of the
residuals of the chosen model refit on the FULL modelling window, because BurstGPT day 77
lies inside the hold-out (days 73-86) and so is not part of the pre-hold-out fit.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

import config_phase2 as P2
from tsaf.models.registry import ModelSpec

SHAPIRO_MAX_N = 5000


def insample(name: str, specs: dict[str, ModelSpec], results: dict, train: pd.Series,
             ctx: dict) -> tuple[pd.Series, pd.DataFrame | None]:
    """One-step in-sample fitted values of model `name` on `train` (ensemble = mean of parts)."""
    if name == "ensemble":
        parts = [insample(p, specs, results, train, ctx)[0] for p in results["ensemble"].params["components"]]
        return (parts[0] + parts[1]) / 2, None
    mctx = {**ctx, "params": results[name].params}
    fit = specs[name].fit(train, 1, mctx)
    return pd.Series(np.asarray(fit.insample, dtype=float), index=train.index), fit.table


def residual_stats(resid: pd.Series, season: int | None) -> dict:
    """Ljung-Box at 10 and 2 x season (10 and 20 without a season), moments, Shapiro-Wilk."""
    r = resid.dropna()
    lags = [10, 2 * season] if season and season > 1 else [10, 20]
    lags = sorted({lag for lag in lags if lag < len(r)})
    out = {"n_resid": int(len(r)), "resid_mean": float(r.mean()), "resid_std": float(r.std()),
           "resid_skew": float(stats.skew(r)) if len(r) > 2 else np.nan}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lb = acorr_ljungbox(r, lags=lags, return_df=True) if lags else pd.DataFrame()
        sh = stats.shapiro(r).pvalue if 3 <= len(r) < SHAPIRO_MAX_N else np.nan
    for lag in lags:
        out[f"ljung_box_p_lag{lag}"] = float(lb.loc[lag, "lb_pvalue"])
    out["ljung_box_lags"] = ",".join(map(str, lags))
    white = bool(len(lags)) and all(out[f"ljung_box_p_lag{lag}"] > 0.05 for lag in lags)
    out["white_noise"] = "yes" if white else "no"
    out["shapiro_p"] = float(sh) if np.isfinite(sh) else np.nan
    out["normal_residuals"] = ("yes" if sh > 0.05 else "no") if np.isfinite(sh) else "not tested (n >= 5000)"
    return out


def robust_z(resid: pd.Series) -> pd.Series:
    """0.6745 * (r - median) / MAD (NaN when the MAD is 0)."""
    r = resid.dropna()
    med = r.median()
    mad = (r - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(np.nan, index=r.index)
    return 0.6745 * (r - med) / mad


def anomalies(resid: pd.Series, series: pd.Series, driver: str, model: str) -> pd.DataFrame:
    """Points with |robust z| above ANOMALY_Z."""
    z = robust_z(resid)
    hit = z[z.abs() > P2.ANOMALY_Z]
    return pd.DataFrame({"driver": driver, "model": model, "time": hit.index.astype(str),
                         "value": series.reindex(hit.index).to_numpy(),
                         "residual": resid.reindex(hit.index).to_numpy(), "robust_z": hit.to_numpy(),
                         "note": ""})


def day77_check(resid: pd.Series, model: str) -> dict:
    """PASS if day 77 of BurstGPT total tokens is flagged by the robust z screen, else FAIL."""
    z = robust_z(resid).abs()
    t = P2.DAY77["time"]
    if t not in z.index or not np.isfinite(z.loc[t]):
        return {"status": "FAIL", "detail": f"day {t} has no residual for {model}", "z": np.nan}
    rank = int((z > z.loc[t]).sum()) + 1
    ok = bool(z.loc[t] > P2.ANOMALY_Z)
    detail = (f"chosen model {model}: |robust z| of day {t} = {z.loc[t]:.2f} (threshold {P2.ANOMALY_Z}), "
              f"rank {rank} of {int(z.notna().sum())} days; {int((z > P2.ANOMALY_Z).sum())} day(s) flagged")
    return {"status": "PASS" if ok else "FAIL", "detail": detail, "z": float(z.loc[t]), "rank": rank}
