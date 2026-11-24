"""Choose the interval options per driver with a pseudo-holdout on the backtest folds.

The last ~20% of the backtest folds (at least 2) are held out. For each held-out fold the point
forecast is that fold's stored out-of-sample forecast (the model saw only earlier data), the
errors come only from the EARLIER folds that end before its origin, and the level is the mean of
the season before its origin. Every enabled option combination is scored by coverage_80,
coverage_95 and mean band width relative to the level; the combination with coverage_80 closest
to 0.8 wins (tie: the narrower band). The final Phase 2 holdout is never read: the function only
receives the pre-holdout series and the backtest rows (all inside it), and checks that.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import config
import config_phase3 as P3
from tsaf import simulate


def option_grid() -> list[dict]:
    """Enabled combinations in a fixed order (all off first): recency x level match."""
    rec = [False] if config.RECENCY_HALF_LIFE == "none" else [False, True]
    lm = [False] if config.LEVEL_MATCH == "none" else [False, True]
    return [{"recency": r, "level_match": m,
             "half_life": None if config.RECENCY_HALF_LIFE == "none" else float(config.RECENCY_HALF_LIFE),
             "level_band": None if config.LEVEL_MATCH == "none" else tuple(config.LEVEL_MATCH)}
            for r, m in itertools.product(rec, lm)]


def label(opt: dict) -> str:
    return f"recency={'on' if opt['recency'] else 'off'}, level_match={'on' if opt['level_match'] else 'off'}"


def _fold_vectors(rows: pd.DataFrame, col: str) -> pd.DataFrame:
    return rows.pivot_table(index=["fold", "origin_index"], columns="step_ahead", values=col,
                            aggfunc="first").sort_index()


def _score(opt: dict, es: simulate.ErrorSet, held: list[int], fc: pd.DataFrame, pre: np.ndarray,
           season, seed: int, growth: str) -> dict:
    """Coverage and width of one option combination over the held-out folds."""
    inside80, inside95, widths, n_pts = [], [], [], 0
    first_held = min(es.origins[i] for i in held)
    for i in held:
        o = es.origins[i]
        train_idx = [j for j in range(es.n_folds) if es.origins[j] < first_held and es.origins[j] + es.H <= o]
        if not train_idx:
            continue
        lv = simulate.level(pre, o, season)
        sub, w, _ = simulate.prepare(simulate.subset(es, train_idx), opt, lv)
        point = fc.loc[es.folds[i]].to_numpy(dtype=float)
        actual = point + es.E[i] * (es.levels[i] if es.relative else 1.0)
        paths = simulate.simulate(point, sub, lv, P3.N_SAMPLES, seed + i, growth, weights=w).values
        lo80, hi80 = simulate.band(paths, 0.8)
        lo95, hi95 = simulate.band(paths, 0.95)
        inside80 += list((actual >= lo80) & (actual <= hi80))
        inside95 += list((actual >= lo95) & (actual <= hi95))
        widths.append(np.mean(hi80 - lo80) / lv if lv > 0 else np.nan)
        n_pts += len(actual)
    return {**{k: opt[k] for k in ("recency", "level_match")}, "option": label(opt), "n_heldout_folds": len(held),
            "n_points": n_pts, "coverage_80": float(np.mean(inside80)) if inside80 else np.nan,
            "coverage_95": float(np.mean(inside95)) if inside95 else np.nan,
            "mean_width_80_relative_to_level": float(np.nanmean(widths)) if widths else np.nan}


def pseudo_holdout(rows: pd.DataFrame, pre: pd.Series, season, relative: bool, seed: int,
                   growth: str = config.GROWTH) -> pd.DataFrame:
    """Score every enabled option combination on the last backtest folds (see module docstring)."""
    if len(rows) and int((rows["origin_index"] + rows["step_ahead"]).max()) - 1 > len(pre):
        raise ValueError("a backtest fold reaches past the pre-holdout data")
    es = simulate.error_matrix(rows, pre, season, relative)
    n = es.n_folds
    k = max(P3.PSEUDO_MIN, int(round(P3.PSEUDO_SHARE * n)))
    if n - k < 1:
        return pd.DataFrame()
    order = np.argsort(es.origins, kind="stable")
    held = sorted(int(i) for i in order[-k:])
    fc = _fold_vectors(rows, "forecast").droplevel("origin_index")
    y = np.asarray(pre, dtype=float)
    return pd.DataFrame([_score(opt, es, held, fc, y, season, seed, growth) for opt in option_grid()])


def choose(table: pd.DataFrame) -> tuple[dict, str]:
    """Combination with coverage_80 closest to 0.8 (tie: narrower); all-off if nothing could be scored."""
    grid = option_grid()
    t = table.dropna(subset=["coverage_80"]) if len(table) else table
    if t.empty:
        return grid[0], "pseudo-holdout not possible (too few folds); options off"
    t = t.assign(gap=(t["coverage_80"] - 0.8).abs().round(9),  # equal distances must tie despite float error
                 w=t["mean_width_80_relative_to_level"].fillna(np.inf))
    best = t.sort_values(["gap", "w"], kind="stable").iloc[0]
    opt = next(o for o in grid if o["recency"] == best["recency"] and o["level_match"] == best["level_match"])
    return opt, (f"{label(opt)}: pseudo-holdout coverage_80 {best['coverage_80']:.2f} on "
                 f"{int(best['n_heldout_folds'])} held-out folds ({int(best['n_points'])} points)")
