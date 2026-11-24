"""Per-driver Phase 1 pipeline (syllabus Modules 1-4 tied together).

`analyse_driver` loads one driver and runs: summary statistics, decomposition choice and
decomposition, stationarity tests and the differencing decision, ACF/PACF, the anomaly
screen, the five baselines through the rolling-origin backtest and the hold-out, and its
figures. It returns a plain dict; the runner collects these into tables.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from tsaf import backtest, baselines, dependence, eda, plots, stationarity
from tsaf.loaders import SkipDriver, load_driver

log = logging.getLogger(__name__)
WEAK_SEASON = 0.1  # STL seasonal strength below this counts as "no real seasonality"


def _run_baselines(s: pd.Series, cfg: dict, cv: dict) -> dict:
    """Backtest + hold-out for every baseline. Returns folds, CV means and hold-out rows."""
    season = cfg["season"]
    pre, _ = backtest.holdout_split(s, cv["holdout"])
    n_folds = len(backtest.fold_origins(len(pre), cv["initial"], cv["h"], cv["step"], cv["max_folds"]))
    if n_folds < 2:
        raise SkipDriver(f"only {n_folds} backtest fold(s) fit before the hold-out (need 2)")
    if n_folds < 3:
        log.warning("%s: only %d folds fit (3 preferred)", cfg["name"], n_folds)
    folds, cv_rows, ho_rows = [], [], []
    for name, f in baselines.BASELINES.items():
        fd = backtest.rolling_origin(pre, f, cv["h"], cv["initial"], cv["step"], cv["max_folds"], season)
        fd.insert(0, "baseline", name)
        fd["error"] = fd["actual"] - fd["forecast"]
        folds.append(fd)
        sc = backtest.score_folds(fd, pre, season)
        cv_rows.append({"baseline": name, "n_folds": len(sc),
                        # skipna=False: a fold with an undefined MAPE (zero actual) makes the
                        # mean undefined too, instead of silently averaging the other folds.
                        **{m: sc[m].mean(skipna=False) for m in ["mae", "rmse", "smape", "mape", "mase"]}})
        ho, _, _ = backtest.score_holdout(s, f, cv["holdout"], season)
        ho_rows.append({"baseline": name, "h": cv["holdout"], **ho})
    return {"folds": pd.concat(folds, ignore_index=True), "cv": pd.DataFrame(cv_rows),
            "holdout": pd.DataFrame(ho_rows), "n_folds": n_folds}


def _best(cv: pd.DataFrame, ho: pd.DataFrame) -> dict:
    """Best baseline by mean CV MASE (ties: by the order of BASELINES)."""
    ranked = cv.dropna(subset=["mase"]).sort_values("mase", kind="stable")
    if ranked.empty:
        raise SkipDriver("MASE undefined for every baseline (zero seasonal-naive scale)")
    b = ranked.iloc[0]
    return {"baseline": b["baseline"], "cv_mase": float(b["mase"]),
            "holdout_mase": float(ho.set_index("baseline").loc[b["baseline"], "mase"])}


def _dependence(s: pd.Series, cfg: dict, diff: dict) -> tuple[dict, dict, str]:
    """ACF/PACF of the original and the chosen differenced series (first difference if d=D=0)."""
    d, D = diff["d"], diff["D"]
    if d == 0 and D == 0:
        d, label = 1, "first difference (d=0 chosen; shown for reference)"
    else:
        label = f"differenced d={d}, D={D}"
    x = stationarity.difference(s, d, D, cfg["season"])
    return dependence.acf_pacf(s), dependence.acf_pacf(x), label


def analyse_driver(cfg: dict, base_cv: dict, data_dir: Path, fig_dir: Path, fast: bool,
                   max_folds: int | None) -> dict:
    """Run all Phase 1 steps for one driver (raises SkipDriver with a reason)."""
    ld = load_driver(cfg, data_dir)
    s, name = ld.series, cfg["name"]
    cv = backtest.resolve_settings(base_cv, len(s), cfg.get("cv_override"), max_folds)
    summary = eda.summary_stats(s)
    choice = eda.choose_decomposition(s, cfg["season"])
    dinfo, comps = eda.decompose(s, cfg, choice["type"])
    st_table = stationarity.stationarity_table(s, name, cfg["season"])
    diff = stationarity.choose_differencing(st_table)
    orig_acf, diff_acf, diff_label = _dependence(s, cfg, diff)
    log_scale = choice["type"] == "multiplicative"
    anomalies = eda.anomaly_screen(s, cfg["season"], log_scale)
    _, rz = eda.robust_z(s, cfg["season"], log_scale)
    bl = _run_baselines(s, cfg, cv)
    best = _best(bl["cv"], bl["holdout"])
    snaive = float(bl["cv"].set_index("baseline").loc["seasonal_naive", "mase"])
    last = bl["folds"][bl["folds"]["fold"] == bl["folds"]["fold"].max()]
    plots.plot_series(ld.full, s, ld.flags, cfg, cv["holdout"], fig_dir / f"{name}_series.png", fast)
    plots.plot_decomposition(comps, cfg, dinfo, fig_dir / f"{name}_decomposition.png", fast)
    plots.plot_acf_pacf(orig_acf, diff_acf, diff_label, cfg, fig_dir / f"{name}_acf_pacf.png", fast)
    plots.plot_baselines(s, last, cfg, fig_dir / f"baselines_{name}.png", fast)
    warns: list[str] = []
    if not diff["tests_agree"]:
        warns.append("ADF/KPSS disagree at every level; d=1 used to be safe.")
    s_str = dinfo.get("seasonal_strength", float("nan"))
    if diff["D"] >= 1 and s_str == s_str and s_str < WEAK_SEASON:
        warns.append(f"D=1 comes from the decision order (seasonal differencing is tried before "
                     f"d=2), but STL seasonal strength is only {s_str:.2f}: risk of over-differencing; "
                     f"Phase 2 should also compare d={diff['d'] + 1}, D=0 by AICc and residual checks.")
    return {"cfg": cfg, "series": s, "summary": summary, "decomp": {**choice, **dinfo},
            "stationarity": st_table, "diff": diff, "anomalies": anomalies, "robust_z": rz,
            "cv_settings": cv,
            "n_folds": bl["n_folds"], "folds": bl["folds"], "cv": bl["cv"], "holdout": bl["holdout"],
            "best": best, "snaive_cv_mase": snaive, "warnings": warns,
            "notes": [n for n in [cfg.get("notes", ""), *ld.notes, *warns] if n]}
