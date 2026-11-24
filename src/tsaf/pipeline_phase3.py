"""Per-driver Phase 3 pipeline: point forecast, bootstrap paths, holdout check, standard table.

`process_driver` never decides anything Phase 2 already decided: the model and its parameters
come from chosen_models.json, the errors from cv_residuals.parquet (ensemble errors rebuilt
from the members' fold forecasts in cv_folds.csv if they are missing).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config
import config_phase3 as P3
from tsaf import export, simulate, tune_intervals
from tsaf.forecast import driver_ctx, ensemble_members, point_forecast
from tsaf.loaders import load_driver

log = logging.getLogger(__name__)


@dataclass
class Phase2Inputs:
    """Everything Phase 3 reads from the Phase 1 and Phase 2 outputs."""
    chosen: list[dict]
    handoff: dict[str, dict]
    residuals: pd.DataFrame
    folds: pd.DataFrame | None = None
    leaderboard: pd.DataFrame | None = None
    holdout: pd.DataFrame | None = None
    notes: list[str] = field(default_factory=list)


def ensemble_residuals(folds: pd.DataFrame, driver: str, members: list[str]) -> pd.DataFrame:
    """Ensemble errors from the two members' stored fold forecasts: mean forecast, actual - mean."""
    keys = ["fold", "step_ahead", "origin_index"]
    parts = [folds[(folds["driver"] == driver) & (folds["model"] == m)][keys + ["actual", "forecast"]]
             for m in members]
    if any(p.empty for p in parts):
        raise ValueError(f"fold forecasts missing for ensemble members {members}")
    j = parts[0].merge(parts[1][keys + ["forecast"]], on=keys, suffixes=("_a", "_b"))
    j["forecast"] = (j["forecast_a"] + j["forecast_b"]) / 2
    j["error"] = j["actual"] - j["forecast"]
    return j.assign(driver=driver, model="ensemble")[["driver", "model", *keys, "actual", "forecast", "error"]]


def residual_rows(inp: Phase2Inputs, chosen: dict, model: str) -> tuple[pd.DataFrame, str]:
    """Backtest error rows for `model` of this driver, and where they came from."""
    r = inp.residuals
    rows = r[(r["driver"] == chosen["name"]) & (r["model"] == model)]
    if len(rows):
        return rows, "cv_residuals.parquet"
    if model == "ensemble" and inp.folds is not None:
        members = [m["model"] for m in ensemble_members(chosen, inp.leaderboard)]
        return ensemble_residuals(inp.folds, chosen["name"], members), "rebuilt from cv_folds.csv members"
    raise ValueError(f"no backtest errors for {model} of {chosen['name']}")


def _as_used(chosen: dict, model_used: str) -> dict:
    """The chosen entry, or a seasonal-naive stand-in when the refit fell back."""
    if model_used == chosen["chosen_model"]:
        return chosen
    return {**chosen, "chosen_model": model_used, "family": "baseline", "params": {}}


def _paths(chosen: dict, train: pd.Series, h: int, rows: pd.DataFrame, entry: dict, data_dir: Path,
           specs: dict, inp: Phase2Inputs, seed: int, cutoff: int | None, options: dict):
    """Point forecast + bootstrap paths for `train` (full window, or pre-holdout with a cut-off)."""
    pr = point_forecast(chosen, train, h, driver_ctx(entry, train, data_dir), specs, inp.leaderboard)
    es = simulate.error_matrix(rows, train, entry["season"], simulate.use_relative(train), cutoff=cutoff)
    cur = simulate.level(train.to_numpy(), len(train), entry["season"])
    es_used, w, notes = simulate.prepare(es, options, cur)
    paths = simulate.simulate(pr.forecast, es_used, cur, P3.N_SAMPLES, seed, config.GROWTH, weights=w)
    return pr, es_used, paths, cur, notes


def _phase2_holdout_coverage(inp: Phase2Inputs, name: str, model: str) -> dict:
    """Phase 2's interval coverage on the same holdout (for the comparison)."""
    ho = inp.holdout
    if ho is None or "lo80" not in ho:
        return {}
    g = ho[(ho["driver"] == name) & (ho["model"] == model)]
    if g.empty or g["lo80"].isna().all():
        return {}
    return {f"phase2_coverage_{lv}": float(((g["actual"] >= g[f"lo{lv}"]) & (g["actual"] <= g[f"hi{lv}"])).mean())
            for lv in (80, 95)}


def _segments(entry: dict, hold: int) -> list[tuple[str, int, int]]:
    segs = [("all", 0, hold)]
    if entry["grain"] == "hourly" and hold > P3.HOURLY_SPLIT:
        segs += [(f"steps 1-{P3.HOURLY_SPLIT}", 0, P3.HOURLY_SPLIT),
                 (f"steps {P3.HOURLY_SPLIT + 1}-{hold}", P3.HOURLY_SPLIT, hold)]
    return segs


def _cover(paths: np.ndarray, y: np.ndarray, cur: float) -> dict:
    lo, hi = simulate.band(paths, 0.8)
    return {"coverage_80": simulate.coverage(paths, y, 0.8), "coverage_95": simulate.coverage(paths, y, 0.95),
            "width": float(np.mean(hi - lo) / cur) if cur > 0 else np.nan,
            "above": int((y > hi).sum()), "below": int((y < lo).sum())}


def _label(index: pd.Index, i: int) -> str:
    return str(index[i])[:10] if isinstance(index, pd.DatetimeIndex) else str(index[i])


def _causes(s: pd.Series, flags: pd.DataFrame, hold: int, point: np.ndarray, es: simulate.ErrorSet,
            cur: float) -> dict:
    """Data facts used to explain a miss: error size vs backtest, level change, anomalies, fold dates."""
    pre, test = s.iloc[:-hold], s.iloc[-hold:]
    err = test.to_numpy() - point
    back = np.mean(np.abs(es.E)) * (cur if es.relative else 1.0) if es.n_folds else np.nan
    prev = pre.iloc[-hold:].mean()
    anom = []
    if "anomaly_low_day" in flags:
        f = flags["anomaly_low_day"].reindex(test.index).fillna(False).astype(bool)
        anom = [_label(test.index, i) for i in np.flatnonzero(f.to_numpy())]
    tested = ""
    if es.origins:
        tested = f"{_label(pre.index, min(es.origins))} to {_label(pre.index, min(max(es.origins) + es.H, len(pre)) - 1)}"
    return {"holdout_err_vs_backtest": float(np.mean(np.abs(err)) / back) if back and back > 0 else np.nan,
            "holdout_level_change": float(test.mean() / prev - 1) if prev > 0 else np.nan,
            "anomalies_in_holdout": ",".join(anom), "backtest_tested": tested,
            "backtest_positive_share": float(np.mean(es.E > 0)) if es.n_folds else np.nan}


def holdout_check(chosen: dict, s: pd.Series, flags: pd.DataFrame, rows: pd.DataFrame, entry: dict,
                  data_dir: Path, specs: dict, inp: Phase2Inputs, seed: int, options: dict) -> list[dict]:
    """Whole procedure as of the Phase 2 holdout, BEFORE (no options) and AFTER (chosen options)."""
    hold = int(entry["cv_settings"]["holdout"])
    pre, test = s.iloc[:-hold], s.iloc[-hold:]
    off = tune_intervals.option_grid()[0]
    pr, es_b, pb, cur, _ = _paths(chosen, pre, hold, rows, entry, data_dir, specs, inp, seed, len(pre), off)
    _, es_a, pa, _, _ = _paths(chosen, pre, hold, rows, entry, data_dir, specs, inp, seed, len(pre), options)
    out = []
    for seg, a, b in _segments(entry, hold):
        y = test.to_numpy()[a:b]
        bf, af = _cover(pb.values[:, a:b], y, cur), _cover(pa.values[:, a:b], y, cur)
        row = {"driver": chosen["name"], "segment": seg, "n_holdout_points": b - a,
               "coverage_80": af["coverage_80"], "coverage_95": af["coverage_95"],
               "mean_width_80_relative_to_level": af["width"],
               "coverage_80_before": bf["coverage_80"], "coverage_80_after": af["coverage_80"],
               "coverage_95_before": bf["coverage_95"], "coverage_95_after": af["coverage_95"],
               "mean_width_80_before": bf["width"], "mean_width_80_after": af["width"],
               "misses_above_after": af["above"], "misses_below_after": af["below"],
               "options": tune_intervals.label(options), "model": pr.model_used,
               "n_folds_before": es_b.n_folds, "n_folds_after": es_a.n_folds}
        row["flag"] = bool(row["coverage_80"] < P3.COVERAGE_FLAG[0.80] or row["coverage_95"] < P3.COVERAGE_FLAG[0.95])
        if seg == "all":
            row.update(_phase2_holdout_coverage(inp, chosen["name"], pr.model_used))
            row.update(_causes(s, flags, hold, pr.forecast, es_a, cur))
        out.append(row)
    return out


def tune(rows: pd.DataFrame, s: pd.Series, entry: dict, name: str, seed: int) -> tuple[dict, str, pd.DataFrame]:
    """Pseudo-holdout on the backtest folds only: the series passed on stops before the final holdout."""
    pre = s.iloc[:-int(entry["cv_settings"]["holdout"])]
    table = tune_intervals.pseudo_holdout(rows, pre, entry["season"], simulate.use_relative(pre), seed)
    opt, why = tune_intervals.choose(table)
    if len(table):
        table.insert(0, "driver", name)
        table["chosen"] = table["option"] == tune_intervals.label(opt)
    return opt, why, table


def _manifest(name, pq, pr, chosen, h, es, es_all, opt, why, notes, paths, check, warnings, err_src, unit,
              entry, seed, future_note, cur) -> dict:
    allc = check[0]
    return {"driver": name, "file": f"forecasts/{pq.name}", "model_used": pr.model_used,
            "family": chosen["family"] if not pr.fallback else "baseline", "fallback_used": pr.fallback,
            "horizon": h, "n_samples": P3.N_SAMPLES, "relative_errors": es.relative,
            "growth_rule": config.GROWTH, "n_folds_used": es.n_folds, "n_folds_available": es_all.n_folds,
            "few_folds": es.n_folds < P3.MIN_FOLDS, "recency_weights": bool(opt["recency"]),
            "recency_half_life_share": opt["half_life"] if opt["recency"] else None,
            "level_match": bool(opt["level_match"]),
            "level_band": list(opt["level_band"]) if opt["level_match"] else None,
            "option_choice": why, "option_notes": notes, "uncertainty_multiplier": P3.UNCERTAINTY_MULTIPLIER,
            "clipped_share": (paths.n_clipped + pr.n_clipped) / (paths.values.size + len(pr.forecast)),
            "coverage_80_holdout": allc["coverage_80"], "coverage_95_holdout": allc["coverage_95"],
            "coverage_80_holdout_before": allc["coverage_80_before"],
            "coverage_95_holdout_before": allc["coverage_95_before"],
            "warnings": warnings, "errors_from": err_src, "unit": unit, "grain": entry["grain"],
            "seed": seed, "future_inputs": future_note, "level_used": cur}


def process_driver(chosen: dict, inp: Phase2Inputs, all_names: list[str], data_dir: Path,
                   out_dir: Path, specs: dict) -> dict:
    """Everything for one driver; returns the manifest entry, tables and arrays for figures."""
    name = chosen["name"]
    entry = inp.handoff[name]
    cfg = config.driver_by_name(name)
    ld = load_driver(cfg, data_dir)
    s = ld.series
    h, seed = int(chosen["horizon_for_forecast"]), simulate.driver_seed(name, all_names)
    pr = point_forecast(chosen, s, h, driver_ctx(entry, s, data_dir), specs, inp.leaderboard)
    used = _as_used(chosen, pr.model_used)
    rows, err_src = residual_rows(inp, chosen, pr.model_used)
    opt, why, tuning = tune(rows, s, entry, name, seed)
    es_all = simulate.error_matrix(rows, s, entry["season"], simulate.use_relative(s))
    cur = simulate.level(s.to_numpy(), len(s), entry["season"])
    es, w, notes = simulate.prepare(es_all, opt, cur)
    for n in notes:
        log.info("%s: %s", name, n)
    paths = simulate.simulate(pr.forecast, es, cur, P3.N_SAMPLES, seed, config.GROWTH, weights=w)
    warnings = [n for n in pr.notes if not n.startswith("future ")]
    future_note = next((n for n in pr.notes if n.startswith("future ")), "")
    share = simulate.bracket_share(paths.values, pr.forecast)
    if share < P3.BRACKET_SHARE:
        warnings.append(f"P10-P90 brackets the point forecast in only {share:.0%} of steps")
        log.warning("%s: %s", name, warnings[-1])
    unit = export.standard_unit(cfg["unit"])
    table = export.build_table(name, pr.forecast, paths.values, export.calendar_months(s.index, h, entry["grain"]),
                               unit, pr.model_used, cfg.get("source", ""), entry["grain"])
    pq, _ = export.write_table(table, out_dir / "forecasts", name)
    check = holdout_check(used, s, ld.flags, rows, entry, data_dir, specs, inp, seed, opt)
    manifest = _manifest(name, pq, pr, chosen, h, es, es_all, opt, why, notes, paths, check, warnings, err_src,
                         unit, entry, seed, future_note, cur)
    return {"manifest": manifest, "table": table, "check": check, "tuning": tuning, "series": s,
            "point": pr.forecast, "paths": paths.values, "entry": entry, "cfg": cfg, "unit": unit}
