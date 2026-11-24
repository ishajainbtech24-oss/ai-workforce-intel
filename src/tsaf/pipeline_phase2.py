"""Per-driver Phase 2 pipeline: run every registered model through the same backtest.

For one driver: load the series with the Phase 1 loader, split off the hold-out, pick
hyper-parameters on the first training window, run Phase 1's `rolling_origin` for every
model, forecast the hold-out once, add the two-model ensemble, then score everything the
same way (CV metrics, share of folds beating seasonal naive, leave-one-fold-out intervals and
their coverage, hold-out metrics) and apply the model-choice rule. A failing model is
recorded as `failed` with its reason and never stops the driver.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config
import config_phase2 as P2
from tsaf import backtest, evaluate
from tsaf.loaders import SkipDriver, load_driver, read_table
from tsaf.metrics import score_all
from tsaf.models.base import check_forecast
from tsaf.models.registry import ModelSpec

log = logging.getLogger(__name__)


class BudgetExceeded(RuntimeError):
    """A model used up its wall-clock budget for this driver."""


@dataclass
class ModelResult:
    """Everything one model produced for one driver."""
    name: str
    family: str
    status: str = "ok"
    reason: str = ""
    params: dict = field(default_factory=dict)
    folds: pd.DataFrame | None = None
    holdout_fc: np.ndarray | None = None
    holdout_info: dict = field(default_factory=dict)
    holdout_table: pd.DataFrame | None = None
    fallbacks: list = field(default_factory=list)
    seconds: float = 0.0


def _extra_series(name: str, s: pd.Series, data_dir: Path) -> dict | None:
    """The configured extra (multivariate) series aligned to the driver's index, or None."""
    ex = P2.EXTRA_SERIES.get(name)
    if not ex:
        return None
    df = read_table(data_dir, ex["file"]).set_index(ex["index_col"]).sort_index()
    ser = df[ex["col"]].astype(float).reindex(s.index)
    if ser.isna().any():
        raise SkipDriver(f"extra series {ex['col']} has gaps inside the window")
    return {"series": ser, "lag": ex["lag"], "col": ex["col"]}


def make_ctx(entry: dict, s: pd.Series, pre: pd.Series, args, data_dir: Path) -> dict:
    """The model context: handoff decisions plus run settings (one dict per driver)."""
    return {"name": entry["name"], "grain": entry["grain"], "season": entry["season"],
            "extra_seasons": entry.get("extra_seasons", []), "d": entry["d"], "D": entry["D"],
            "decomposition": entry["decomposition"], "positive": bool((pre > 0).all()),
            "nonneg": bool((s >= 0).all()), "fast": bool(args.fast),
            "with_lstm": bool(getattr(args, "with_lstm", False)),
            "n_trees": P2.N_TREES_FAST if args.fast else P2.N_TREES,
            "arima_max_candidates": P2.ARIMA_MAX_CANDIDATES_FAST if args.fast else P2.ARIMA_MAX_CANDIDATES,
            "arima_budget": {"seconds": P2.ARIMA_BUDGET_S, "used": 0.0},
            "extra": _extra_series(entry["name"], s, data_dir)}


def _forecaster(spec: ModelSpec, mctx: dict, res: ModelResult, t0: float, budget: float):
    """Wrap a model as Phase 1's forecaster(train, h, season); checks the budget between fits."""

    def f(train: pd.Series, h: int, season) -> np.ndarray:
        if time.time() - t0 > budget:
            raise BudgetExceeded(f"time budget of {budget:.0f}s used up")
        fit = spec.fit(train, h, mctx)
        if fit.info.get("fallback"):
            res.fallbacks.append(str(fit.info["fallback"]))
        fc = check_forecast(fit.forecast, h)
        return np.maximum(fc, 0.0) if mctx["nonneg"] else fc

    return f


def run_model(spec: ModelSpec, pre: pd.Series, cv: dict, origins: list[int], ctx: dict,
              budget: float = P2.MODEL_BUDGET_S) -> ModelResult:
    """Select (first window), backtest and hold-out forecast one model; never raises."""
    res, t0 = ModelResult(spec.name, spec.family), time.time()
    reason = spec.skip_reason(ctx)
    if reason:
        res.status, res.reason = "skipped", reason
        return res
    try:
        res.params = spec.select(pre.iloc[: origins[0]], ctx) if spec.select else {}
        mctx = {**ctx, "params": res.params}
        f = _forecaster(spec, mctx, res, t0, budget)
        res.folds = backtest.rolling_origin(pre, f, cv["h"], cv["initial"], cv["step"],
                                            cv["max_folds"], ctx["season"])
        # Hold-out: fit on everything before it, forecast it in one go (Phase 1 protocol).
        ho = spec.fit(pre, cv["holdout"], mctx)
        fc = check_forecast(ho.forecast, cv["holdout"])
        res.holdout_fc = np.maximum(fc, 0.0) if ctx["nonneg"] else fc
        res.holdout_info, res.holdout_table = ho.info, ho.table
        if ho.info.get("fallback"):
            res.fallbacks.append(f"hold-out fit: {ho.info['fallback']}")
    except Exception as exc:  # noqa: BLE001 - a failing model must never stop the run
        res.status, res.reason = "failed", f"{type(exc).__name__}: {exc}"[:300]
        res.folds, res.holdout_fc = None, None
    res.seconds = time.time() - t0
    return res


def make_ensemble(results: list[ModelResult], cv_mase: dict[str, float]) -> ModelResult:
    """Average of the two models with the best mean CV MASE (stored forecasts, no refit)."""
    res = ModelResult("ensemble", "ensemble")
    ranked = sorted((m for m in cv_mase if np.isfinite(cv_mase[m])), key=lambda m: cv_mase[m])
    if len(ranked) < 2:
        res.status, res.reason = "failed", "fewer than two successful models to average"
        return res
    a, b = (next(r for r in results if r.name == n) for n in ranked[:2])
    keys = ["fold", "step_ahead", "origin_index", "time", "actual"]
    j = a.folds.merge(b.folds[keys + ["forecast"]], on=keys, suffixes=("_a", "_b"))
    j["forecast"] = (j["forecast_a"] + j["forecast_b"]) / 2
    res.folds = j[keys[:4] + ["actual", "forecast"]]
    res.holdout_fc = (a.holdout_fc + b.holdout_fc) / 2
    res.params = {"components": [a.name, b.name], "weights": [0.5, 0.5]}
    return res


def score_result(r: ModelResult, pre: pd.Series, test: pd.Series, season, sn_fold: pd.DataFrame | None,
                 n_folds: int) -> tuple[dict, pd.DataFrame | None]:
    """Leaderboard row (CV, share beating seasonal naive, coverage, hold-out) and folds with intervals."""
    row = {"model": r.name, "family": r.family, "status": r.status, "reason": r.reason,
           "n_folds": n_folds if r.status == "ok" else 0, "fit_seconds": round(r.seconds, 2)}
    if r.status != "ok":
        return row, None
    means, per_fold = evaluate.cv_scores(r.folds, pre, season)
    row.update(means)
    row["share_beats_snaive"] = evaluate.share_beating(per_fold, sn_fold) if sn_fold is not None else np.nan
    flags, folds = [], r.folds.copy()
    if n_folds >= P2.MIN_FOLDS_FOR_INTERVALS:
        folds = evaluate.lofo_intervals(folds)
        cov = evaluate.coverage(folds)
        row.update(cov)
        flags += evaluate.coverage_flags(cov)
    else:
        flags.append(f"intervals skipped: only {n_folds} folds (need {P2.MIN_FOLDS_FOR_INTERVALS})")
    if r.fallbacks:
        flags.append(f"fallback used in {len(r.fallbacks)} fit(s): {sorted(set(r.fallbacks))}")
    ho = score_all(test, r.holdout_fc, pre, season)
    row.update({f"holdout_{k}": v for k, v in ho.items()})
    row["flags"] = "; ".join(flags)
    return row, folds


def _log_model(name: str, r: ModelResult, row: dict | None = None) -> None:
    if r.status == "ok":
        log.info("  %-28s ok      CV MASE %.3f  [%.1fs]", r.name, row["cv_mase"] if row else np.nan, r.seconds)
    else:
        (log.info if r.status == "skipped" else log.warning)("  %-28s %-7s %s [%.1fs]", r.name,
                                                             r.status, r.reason, r.seconds)


def load_for_phase2(entry: dict, args, data_dir: Path) -> tuple[pd.Series, dict, list[int]]:
    """Load with the Phase 1 loader; CV settings = Phase 1 config + handoff values."""
    cfg = config.driver_by_name(entry["name"])
    s = load_driver(cfg, data_dir).series
    cv = backtest.resolve_settings(config.CV_SETTINGS[entry["grain"]], len(s), entry["cv_settings"],
                                   config.FAST_MAX_FOLDS if args.fast else None)
    pre, _ = backtest.holdout_split(s, cv["holdout"])
    origins = backtest.fold_origins(len(pre), cv["initial"], cv["h"], cv["step"], cv["max_folds"])
    if len(origins) < 2:
        raise SkipDriver(f"only {len(origins)} backtest fold(s) fit before the hold-out (need 2)")
    return s, cv, origins


def model_driver(entry: dict, specs: list[ModelSpec], args, data_dir: Path) -> dict:
    """All models for one driver: results, leaderboard rows, folds with intervals, choice."""
    s, cv, origins = load_for_phase2(entry, args, data_dir)
    pre, test = backtest.holdout_split(s, cv["holdout"])
    ctx = make_ctx(entry, s, pre, args, data_dir)
    season = entry["season"]
    results, rows, folds_iv, sn_fold = [], [], {}, None
    for spec in specs:
        r = run_model(spec, pre, cv, origins, ctx)
        results.append(r)
        if r.name == "seasonal_naive" and r.status == "ok":
            sn_fold = evaluate.cv_scores(r.folds, pre, season)[1]
        row, fiv = score_result(r, pre, test, season, sn_fold, len(origins))
        rows.append(row)
        if fiv is not None:
            folds_iv[r.name] = fiv
        _log_model(entry["name"], r, row)
    ok_mase = {row["model"]: row["cv_mase"] for row in rows if row["status"] == "ok"}
    ens = make_ensemble(results, ok_mase)
    results.append(ens)
    row, fiv = score_result(ens, pre, test, season, sn_fold, len(origins))
    if ens.status == "ok":
        row["reason"] = "average of " + " and ".join(ens.params["components"])
        folds_iv["ensemble"] = fiv
    rows.append(row)
    _log_model(entry["name"], ens, row)
    board = pd.DataFrame(rows)
    chosen, why = evaluate.choose(board)
    return {"entry": entry, "series": s, "pre": pre, "test": test, "cv": cv, "n_folds": len(origins),
            "ctx": ctx, "results": {r.name: r for r in results}, "board": board,
            "folds": folds_iv, "chosen": chosen, "why": why}
