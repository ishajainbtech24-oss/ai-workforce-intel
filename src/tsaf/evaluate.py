"""Phase 2 scoring (syllabus Modules 2 and 4): CV metrics, intervals, coverage and model choice.

Prediction intervals are the same for every model: for fold k, the absolute errors of the
OTHER folds at the same step ahead give empirical 80% / 95% quantiles, used as half-widths
around fold k's point forecast (leave-one-fold-out). The model-choice rule ranks by mean CV
MASE; a model wins only if it is below seasonal naive, ties within 1% go to the simpler family.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase2 as P2
from tsaf import backtest

METRICS = ["mae", "rmse", "smape", "mape", "mase"]


def cv_scores(folds: pd.DataFrame, pre: pd.Series, season: int | None) -> tuple[dict, pd.DataFrame]:
    """Mean CV metrics (MAPE undefined if any fold's is) and the per-fold table."""
    per_fold = backtest.score_folds(folds, pre, season)
    means = {f"cv_{m}": float(per_fold[m].mean(skipna=False)) for m in METRICS}
    return means, per_fold


def share_beating(per_fold: pd.DataFrame, snaive_fold: pd.DataFrame) -> float:
    """Share of folds where the model's fold MASE is strictly below seasonal naive's."""
    j = per_fold[["fold", "mase"]].merge(snaive_fold[["fold", "mase"]], on="fold", suffixes=("", "_sn"))
    return float((j["mase"] < j["mase_sn"]).mean()) if len(j) else float("nan")


def lofo_intervals(folds: pd.DataFrame, levels=P2.LEVELS) -> pd.DataFrame:
    """Add lo/hi columns per level: half-width = quantile of |error| over the other folds, same step."""
    out = folds.copy()
    err = (out["actual"] - out["forecast"]).abs()
    for lv in levels:
        hw = np.full(len(out), np.nan)
        for i, (fold, step) in enumerate(zip(out["fold"].to_numpy(), out["step_ahead"].to_numpy())):
            others = err[(out["fold"] != fold) & (out["step_ahead"] == step)]
            if len(others):
                hw[i] = np.quantile(others, lv)
        tag = int(round(lv * 100))
        out[f"lo{tag}"], out[f"hi{tag}"] = out["forecast"] - hw, out["forecast"] + hw
    return out


def coverage(with_iv: pd.DataFrame, levels=P2.LEVELS) -> dict[str, float]:
    """Share of fold forecasts whose actual lies inside each interval."""
    res = {}
    for lv in levels:
        tag = int(round(lv * 100))
        inside = (with_iv["actual"] >= with_iv[f"lo{tag}"]) & (with_iv["actual"] <= with_iv[f"hi{tag}"])
        res[f"coverage_{tag}"] = float(inside.mean())
    return res


def coverage_flags(cov: dict[str, float]) -> list[str]:
    """Warnings when coverage is below the flag thresholds (60% for 80%, 85% for 95%)."""
    flags = []
    for lv, floor in P2.COVERAGE_FLAG.items():
        tag = int(round(lv * 100))
        v = cov.get(f"coverage_{tag}", float("nan"))
        if np.isfinite(v) and v < floor:
            flags.append(f"{tag}% interval coverage {v:.1%} < {floor:.0%}")
    return flags


def holdout_halfwidths(folds: pd.DataFrame, H: int, levels=P2.LEVELS) -> dict[int, np.ndarray]:
    """Half-widths for an H-step forecast from ALL folds' |errors| at each step ahead.

    Steps beyond the CV horizon reuse the last CV step's quantile (stated on the figure).
    """
    err = (folds["actual"] - folds["forecast"]).abs()
    steps = sorted(folds["step_ahead"].unique())
    out = {}
    for lv in levels:
        q = {s: float(np.quantile(err[folds["step_ahead"] == s], lv)) for s in steps}
        out[int(round(lv * 100))] = np.array([q[min(k, steps[-1])] for k in range(1, H + 1)])
    return out


def choose(board: pd.DataFrame) -> tuple[str, str]:
    """(chosen model, why) from rows with model, family, status, cv_mase."""
    ok = board[(board["status"] == "ok") & np.isfinite(board["cv_mase"].astype(float))]
    sn_row = ok[ok["model"] == "seasonal_naive"]
    if ok.empty:
        return "seasonal_naive", "no model produced a valid CV MASE; seasonal naive by default"
    best = float(ok["cv_mase"].min())
    near = ok[ok["cv_mase"] <= best * (1 + P2.TIE_TOLERANCE)].copy()
    near["rank_family"] = near["family"].map({f: i for i, f in enumerate(P2.FAMILY_ORDER)})
    cand = near.sort_values(["rank_family", "cv_mase"], kind="stable").iloc[0]
    tie = "" if cand["cv_mase"] == best else (
        f" (within {P2.TIE_TOLERANCE:.0%} of the best, {best:.3f}; simpler family preferred)")
    if sn_row.empty:
        return str(cand["model"]), f"lowest mean CV MASE {cand['cv_mase']:.3f}{tie}; seasonal naive unavailable"
    sn = float(sn_row["cv_mase"].iloc[0])
    if cand["model"] == "seasonal_naive":
        return "seasonal_naive", f"seasonal naive is (tied) best, CV MASE {sn:.3f}{tie}"
    if cand["cv_mase"] < sn:
        return str(cand["model"]), (f"lowest mean CV MASE {cand['cv_mase']:.3f}{tie}, below "
                                    f"seasonal naive {sn:.3f}")
    return "seasonal_naive", (f"no model beat seasonal naive (best {cand['model']} {cand['cv_mase']:.3f}"
                              f" vs seasonal naive {sn:.3f}); seasonal naive kept")
