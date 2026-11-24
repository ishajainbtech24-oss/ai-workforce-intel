"""Phase 3 sample paths by residual bootstrap (syllabus Modules 2 and 4: forecast uncertainty).

Rules (see PHASE3_SUMMARY.md section 3):
1. Errors are the chosen model's OUT-OF-SAMPLE backtest errors (actual - forecast), as a matrix
   E[fold, step] with one row per fold and one column per step ahead (up to H_cv).
2. A path draws ONE fold at random (with replacement) and uses its whole error vector, so the
   correlation between steps is kept.
3. For a strictly positive series each fold's errors are divided by that fold's level (mean of
   the last `season` values before its origin; 3 without a season) and multiplied by the
   current level (mean of the last `season` values of the window). Otherwise errors are absolute.
4. Beyond H_cv, step h reuses the drawn fold's error at H_cv times sqrt(h / H_cv)
   (config.GROWTH = "sqrt"; "none" = no growth).
5. Path = point forecast + error, clipped at 0. Seed = 42 + driver position (default_rng).

Optional (config.RECENCY_HALF_LIFE, config.LEVEL_MATCH; chosen per driver in tune_intervals.py):
6. Recency: fold sampling weights halve every (share x n_folds) folds of age (newest fold = age 0).
7. Level match (positive series): only folds whose level is within 0.5x-2x of the current level;
   if fewer than 3 qualify, the 3 folds with the closest level (on a log scale).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config_phase3 as P3


@dataclass
class ErrorSet:
    """Backtest error matrix of one driver's chosen model, ready to resample."""
    E: np.ndarray
    relative: bool
    folds: list[int]
    H: int
    skipped: list[str] = field(default_factory=list)
    origins: list[int] = field(default_factory=list)
    levels: np.ndarray | None = None  # level before each fold's origin (same order as E)

    @property
    def n_folds(self) -> int:
        return int(self.E.shape[0])


def use_relative(series) -> bool:
    """Relative errors only for a strictly positive series (volumes, prices, indices)."""
    y = np.asarray(series, dtype=float)
    return bool(len(y) and np.all(y > 0))


def level_window(season: int | None) -> int:
    """Number of observations averaged for a level: the season, or 3 without one."""
    return int(season) if season and season > 1 else 3


def level(values, end: int, season: int | None) -> float:
    """Mean of the last level_window(season) values before position `end`."""
    y = np.asarray(values, dtype=float)
    k = level_window(season)
    return float(np.mean(y[max(0, end - k):end])) if end > 0 else float("nan")


def error_matrix(rows: pd.DataFrame, series: pd.Series, season: int | None, relative: bool,
                 cutoff: int | None = None) -> ErrorSet:
    """E[fold, step] from tidy rows (fold, origin_index, step_ahead, error) of one driver and model.

    `cutoff`: keep only folds whose whole test window ends before this position (holdout check).
    """
    piv = rows.pivot_table(index=["fold", "origin_index"], columns="step_ahead", values="error",
                           aggfunc="first").sort_index()
    H = int(piv.shape[1])
    y = np.asarray(series, dtype=float)
    keep, folds, skipped, origins, levels = [], [], [], [], []
    for (fold, origin), e in piv.iterrows():
        e = e.to_numpy(dtype=float)
        if cutoff is not None and origin + H > cutoff:
            skipped.append(f"fold {fold}: ends after the cut-off")
            continue
        if not np.all(np.isfinite(e)):
            skipped.append(f"fold {fold}: incomplete error vector")
            continue
        lv = level(y, int(origin), season)
        if relative:
            if not lv > 0:
                skipped.append(f"fold {fold}: level {lv} not above 0")
                continue
            e = e / lv
        keep.append(e)
        folds.append(int(fold))
        origins.append(int(origin))
        levels.append(lv)
    E = np.vstack(keep) if keep else np.empty((0, H))
    return ErrorSet(E=E, relative=relative, folds=folds, H=H, skipped=skipped, origins=origins,
                    levels=np.asarray(levels, dtype=float))


def extend_errors(E_rows: np.ndarray, h: int, growth: str) -> np.ndarray:
    """Error vectors of length h: steps beyond H_cv reuse step H_cv (x sqrt(h/H_cv) if growth == 'sqrt')."""
    n, H = E_rows.shape
    out = np.empty((n, h))
    m = min(h, H)
    out[:, :m] = E_rows[:, :m]
    for j in range(H, h):
        factor = np.sqrt((j + 1) / H) if growth == "sqrt" else 1.0
        out[:, j] = E_rows[:, H - 1] * factor
    return out


@dataclass
class Paths:
    """Simulated sample paths of one driver."""
    values: np.ndarray        # (n_samples, h), clipped at 0
    draws: np.ndarray         # fold row drawn for each path
    n_clipped: int
    scale: float              # current level (relative errors) or 1.0


def simulate(point: np.ndarray, es: ErrorSet, current_level: float, n: int, seed: int,
             growth: str, weights: np.ndarray | None = None) -> Paths:
    """n bootstrap paths around the point forecast (whole-vector resampling, clipped at 0).

    `weights` (optional) are fold sampling probabilities; None = every fold equally likely.
    """
    if es.n_folds == 0:
        raise ValueError("no usable backtest folds to resample")
    point = np.asarray(point, dtype=float)
    rng = np.random.default_rng(seed)
    if weights is None:
        draws = rng.integers(0, es.n_folds, size=n)
    else:
        draws = rng.choice(es.n_folds, size=n, p=np.asarray(weights, dtype=float))
    errs = extend_errors(es.E[draws], len(point), growth)
    scale = float(current_level) if es.relative else 1.0
    raw = point[None, :] + errs * scale
    return Paths(values=np.maximum(raw, 0.0), draws=draws, n_clipped=int((raw < 0).sum()), scale=scale)


def bracket_share(paths: np.ndarray, point: np.ndarray) -> float:
    """Share of steps where the P10-P90 range of the paths contains the point forecast."""
    p10, p90 = np.percentile(paths, [10, 90], axis=0)
    return float(np.mean((p10 <= point + 1e-9) & (point - 1e-9 <= p90)))


def band(paths: np.ndarray, level_: float) -> tuple[np.ndarray, np.ndarray]:
    """Central `level_` band of the paths at each step (e.g. 0.8 -> P10 and P90)."""
    a = (1 - level_) / 2 * 100
    lo, hi = np.percentile(paths, [a, 100 - a], axis=0)
    return lo, hi


def coverage(paths: np.ndarray, actual, level_: float) -> float:
    """Share of actual values inside the central `level_` band of the paths."""
    lo, hi = band(paths, level_)
    y = np.asarray(actual, dtype=float)
    return float(np.mean((y >= lo) & (y <= hi)))


def driver_seed(name: str, all_names: list[str]) -> int:
    """42 + position of the driver in the sorted driver names."""
    return P3.SEED_BASE + sorted(all_names).index(name)


def subset(es: ErrorSet, idx) -> ErrorSet:
    """The folds at positions `idx` of an ErrorSet (order kept)."""
    idx = np.asarray(idx, dtype=int)
    lv = es.levels[idx] if es.levels is not None and len(es.levels) else None
    return ErrorSet(E=es.E[idx], relative=es.relative, folds=[es.folds[i] for i in idx], H=es.H,
                    skipped=list(es.skipped), origins=[es.origins[i] for i in idx] if es.origins else [],
                    levels=lv)


def recency_weights(origins, share: float) -> np.ndarray:
    """Sampling weights that halve every (share x n_folds) folds of age; the newest fold has age 0."""
    o = np.asarray(origins, dtype=float)
    n = len(o)
    age = (n - 1) - np.argsort(np.argsort(o, kind="stable"), kind="stable")
    half_life = max(share * n, 1e-9)
    w = 0.5 ** (age / half_life)
    return w / w.sum()


def level_match(es: ErrorSet, current_level: float, band_: tuple[float, float],
                min_folds: int = P3.LEVEL_MATCH_MIN_FOLDS) -> tuple[ErrorSet, str]:
    """Folds whose level is within band_ x the current level (else the min_folds closest levels)."""
    if not es.relative or es.levels is None or not current_level > 0:
        return es, "level match not applied (absolute errors)"
    ratio = es.levels / current_level
    ok = np.flatnonzero((ratio >= band_[0]) & (ratio <= band_[1]))
    if len(ok) >= min_folds:
        return subset(es, ok), f"level match: {len(ok)} of {es.n_folds} folds within {band_[0]:g}-{band_[1]:g}x"
    closest = np.argsort(np.abs(np.log(ratio)), kind="stable")[: min(min_folds, es.n_folds)]
    return subset(es, np.sort(closest)), (f"level match: only {len(ok)} of {es.n_folds} folds within "
                                          f"{band_[0]:g}-{band_[1]:g}x; used the {len(closest)} closest levels")


def prepare(es: ErrorSet, options: dict, current_level: float) -> tuple[ErrorSet, np.ndarray | None, list[str]]:
    """Apply the chosen options: level match first, then recency weights on the remaining folds."""
    notes: list[str] = []
    if options.get("level_match"):
        es, note = level_match(es, current_level, options["level_band"])
        notes.append(note)
    w = recency_weights(es.origins, options["half_life"]) if options.get("recency") and es.n_folds > 1 else None
    if w is not None:
        notes.append(f"recency weights: half-life {options['half_life']:g} x {es.n_folds} folds")
    return es, w, notes
