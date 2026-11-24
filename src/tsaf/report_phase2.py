"""Phase 2 tables and the generated PHASE2_SUMMARY.md (every number read from this run)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config_phase2 as P2
from tsaf import evaluate
from tsaf.report import fmt, md_table

LB_COLS = ["driver", "model", "family", "status", "reason", "n_folds", "cv_mae", "cv_rmse", "cv_smape",
           "cv_mape", "cv_mase", "share_beats_snaive", "coverage_80", "coverage_95", "flags",
           "holdout_mae", "holdout_rmse", "holdout_smape", "holdout_mape", "holdout_mase", "fit_seconds"]


def _s(v) -> str:
    """Parameter value as text for params.csv."""
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, default=str)
    return str(v)


def leaderboard(results: list[dict]) -> pd.DataFrame:
    lb = pd.concat([dr["board"].assign(driver=dr["entry"]["name"]) for dr in results], ignore_index=True)
    for c in LB_COLS:
        if c not in lb:
            lb[c] = np.nan
    lb["flags"] = lb["flags"].fillna("")
    lb["reason"] = lb["reason"].fillna("")
    return lb[LB_COLS]


def params_table(results: list[dict]) -> pd.DataFrame:
    rows = []
    for dr in results:
        for r in dr["results"].values():
            if r.status != "ok":
                continue
            for stage, d in (("selected on first training window", r.params),
                             ("fitted on data before the hold-out", r.holdout_info)):
                rows += [{"driver": dr["entry"]["name"], "model": r.name, "family": r.family, "stage": stage,
                          "param": k, "value": _s(v)} for k, v in d.items() if k != "features"]
            if r.fallbacks:
                rows.append({"driver": dr["entry"]["name"], "model": r.name, "family": r.family,
                             "stage": "backtest folds", "param": "fallbacks", "value": _s(sorted(set(r.fallbacks)))})
    return pd.DataFrame(rows, columns=["driver", "model", "family", "stage", "param", "value"])


def folds_table(results: list[dict]) -> pd.DataFrame:
    frames = [f.assign(driver=dr["entry"]["name"], model=m) for dr in results for m, f in dr["folds"].items()]
    df = pd.concat(frames, ignore_index=True)
    df["error"] = df["actual"] - df["forecast"]
    first = ["driver", "model", "fold", "step_ahead", "origin_index", "time", "actual", "forecast", "error"]
    return df[first + [c for c in df.columns if c not in first]]


def holdout_table(results: list[dict]) -> pd.DataFrame:
    rows = []
    for dr in results:
        b = dr["board"].set_index("model")
        for m, r in dr["results"].items():
            if r.status != "ok":
                continue
            f = dr["folds"][m]
            hw = (evaluate.holdout_halfwidths(f, len(dr["test"]))
                  if dr["n_folds"] >= P2.MIN_FOLDS_FOR_INTERVALS else None)
            df = pd.DataFrame({"driver": dr["entry"]["name"], "model": m,
                               "step_ahead": np.arange(1, len(dr["test"]) + 1),
                               "time": dr["test"].index.astype(str), "actual": dr["test"].to_numpy(),
                               "forecast": r.holdout_fc})
            for lv in (80, 95):
                df[f"lo{lv}"] = df["forecast"] - hw[lv] if hw else np.nan
                df[f"hi{lv}"] = df["forecast"] + hw[lv] if hw else np.nan
            for k in ("mae", "rmse", "smape", "mape", "mase"):
                df[f"holdout_{k}"] = b.loc[m, f"holdout_{k}"]
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def write_tables(results: list[dict], diags: list[dict], chosen_rows: list[dict], tables: Path) -> None:
    """Every CSV / Parquet table listed in the README."""
    lb = leaderboard(results)
    lb.to_csv(tables / "leaderboard.csv", index=False)
    pd.DataFrame(chosen_rows).to_csv(tables / "chosen_models.csv", index=False)
    params_table(results).to_csv(tables / "params.csv", index=False)
    folds = folds_table(results)
    folds.to_csv(tables / "cv_folds.csv", index=False)
    res = folds[["driver", "model", "fold", "step_ahead", "origin_index", "time", "actual", "forecast", "error"]].copy()
    res["time"] = res["time"].astype(str)
    res.to_parquet(tables / "cv_residuals.parquet", index=False)
    holdout_table(results).to_csv(tables / "holdout.csv", index=False)
    pd.DataFrame([d["stats"] for d in diags]).to_csv(tables / "residual_diagnostics.csv", index=False)
    cov = lb[lb["status"] == "ok"][["driver", "model", "family", "n_folds", "coverage_80", "coverage_95", "flags"]]
    cov.to_csv(tables / "interval_coverage.csv", index=False)
    feature_importance(results).to_csv(tables / "feature_importance.csv", index=False)
    arima_tables(results, diags).to_csv(tables / "arima_params.csv", index=False)
    anomalies_table(diags).to_csv(tables / "anomalies.csv", index=False)


def feature_importance(results: list[dict]) -> pd.DataFrame:
    rows = [r.holdout_table.assign(driver=dr["entry"]["name"], model=r.name)
            for dr in results for r in dr["results"].values()
            if r.status == "ok" and r.family == "ml" and r.holdout_table is not None]
    cols = ["driver", "model", "feature", "importance"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.concat(rows, ignore_index=True)[cols].sort_values(["driver", "model", "importance"],
                                                                ascending=[True, True, False])


def arima_tables(results: list[dict], diags: list[dict]) -> pd.DataFrame:
    """Parameter tables (estimate, std err, p-value) of every ARIMA-family fit before the hold-out."""
    chosen = {d["driver"]: d["model"] for d in diags}
    rows = [r.holdout_table.assign(driver=dr["entry"]["name"], model=r.name,
                                   is_chosen=chosen.get(dr["entry"]["name"]) == r.name)
            for dr in results for r in dr["results"].values()
            if r.status == "ok" and r.family == "arima" and r.holdout_table is not None]
    cols = ["driver", "model", "is_chosen", "param", "estimate", "std_err", "p_value"]
    return pd.concat(rows, ignore_index=True)[cols] if rows else pd.DataFrame(columns=cols)


def anomalies_table(diags: list[dict]) -> pd.DataFrame:
    frames = [d["anomalies"] for d in diags if len(d["anomalies"])]
    d77 = next((d["day77"] for d in diags if d.get("day77")), None)
    if d77:
        frames.append(pd.DataFrame([{"driver": P2.DAY77["driver"], "model": "", "time": str(P2.DAY77["time"]),
                                     "value": np.nan, "residual": np.nan, "robust_z": d77.get("z", np.nan),
                                     "note": f"day-77 check: {d77['status']} ({d77['detail']})"}]))
    cols = ["driver", "model", "time", "value", "residual", "robust_z", "note"]
    return pd.concat(frames, ignore_index=True)[cols] if frames else pd.DataFrame(columns=cols)


def write_summary(path: Path, results, diags, chosen_rows, skipped, args) -> None:
    from tsaf.summary_phase2 import build_summary
    path.write_text(build_summary(results, diags, chosen_rows, skipped, args), encoding="utf-8")


__all__ = ["write_tables", "write_summary", "leaderboard", "fmt", "md_table"]
