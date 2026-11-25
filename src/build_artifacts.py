"""Precompute everything the dashboard's Analyst mode and calibrated intervals need, into artifacts/.

Run once after the phases (about a minute):  python src/build_artifacts.py

Reads only saved files: data/processed (the series), outputs/phase1-3 (anomalies, Phase 2 rolling-origin folds,
parameters, leaderboard, Phase 3 forecasts). Adds the Theta method by refitting it at the same fold origins.
Writes (all small, read by the app at start, nothing computed on a page load):
  artifacts/diagnostics.json        STL strengths, ADF/KPSS + verdict, differencing, ACF/PACF, break test, outliers
  artifacts/stl/<series>.csv        STL trend / seasonal / remainder
  artifacts/cv_metrics.csv          MAE, RMSE, MASE, bias, interval coverage per series and approach
  artifacts/cv_horizon.csv          error by forecast step per series and approach
  artifacts/cv_folds_extra.csv      Theta fold forecasts (same layout as Phase 2 cv_folds.csv)
  artifacts/dm_tests.csv            Diebold-Mariano test of each approach against seasonal naive
  artifacts/residuals.json          one-step errors of the chosen approach: values, ACF, Ljung-Box, QQ points
  artifacts/model_cards.csv         approach, family, settings, AICc (where fitted), fit time, status / why not run
  artifacts/conformal.json          calibrated (conformal) interval scales, nominal-vs-empirical coverage, interval scores
  artifacts/fan/<series>.csv        forecast centre line with conformal 50% and 80% bands
"""
from __future__ import annotations

import json
import logging
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from tsaf.loaders import load_driver  # noqa: E402

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

ROOT = config.ROOT
OUT = ROOT / "artifacts"
P1, P2, P3 = (ROOT / "outputs" / f"phase{i}" / "tables" for i in (1, 2, 3))
FC = ROOT / "outputs" / "phase3" / "forecasts"
SEVEN = ["eci_wages_quarterly", "ppi_hosting_monthly", "burst_tokens_total_daily", "burst_tokens_api_daily",
         "burst_tokens_chat_daily", "burst_requests_hourly", "wildchat_conversations_daily"]
LEVELS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)   # nominal levels for the coverage plot
MIN_CAL = 3                                # calibration folds needed before a fold is scored (conformal)
CARD_MODELS = {"naive": "Naive", "seasonal_naive": "Seasonal naive", "drift": "Drift", "ets": "ETS (exponential smoothing)",
               "arima": "ARIMA", "theta": "Theta", "chosen": "Current approach (chosen)"}
ETS_FAMILY = ("ses", "holt", "damped_holt", "hw_additive", "hw_multiplicative")
ARIMA_FAMILY = ("arima", "sarima", "sarimax")


def series(name: str) -> pd.Series:
    return load_driver(config.driver_by_name(name), config.DATA_DIR).series.astype(float)


def season(name: str) -> int:
    return int(config.driver_by_name(name)["season"] or 1)


def label(ix) -> str:
    return ix.strftime("%Y-%m-%d") if hasattr(ix, "strftime") else str(int(ix))


# ------------------------------------------------------------------ diagnostics (data page)
def strength(var_r: float, var_x: float) -> float:
    return float(max(0.0, 1.0 - var_r / var_x)) if var_x > 0 else 0.0


def stationarity(y: np.ndarray) -> dict:
    from statsmodels.tsa.stattools import adfuller, kpss
    out = {}
    for d in (0, 1, 2):
        z = np.diff(y, n=d) if d else y
        adf_p = float(adfuller(z, autolag="AIC")[1])
        kpss_p = float(kpss(z, regression="c", nlags="auto")[1])
        out[d] = {"adf_p": adf_p, "kpss_p": kpss_p}
        if adf_p < 0.05 and kpss_p > 0.05:
            return {"levels": out, "suggested_differencing": d}
    return {"levels": out, "suggested_differencing": 2}


def verdict(st: dict) -> str:
    lv = st["levels"][0]
    if lv["adf_p"] < 0.05 and lv["kpss_p"] > 0.05:
        return "stable: both tests agree the level does not wander"
    if lv["adf_p"] >= 0.05 and lv["kpss_p"] <= 0.05:
        return f"wandering: both tests agree; difference {st['suggested_differencing']} time(s)"
    return f"mixed: the two tests disagree; differencing {st['suggested_differencing']} time(s) settles it"


def break_test(y: np.ndarray) -> dict:
    """CUSUM test on the residuals of a straight-line fit, plus the most likely single shift in the mean change."""
    from statsmodels.regression.linear_model import OLS
    from statsmodels.stats.diagnostic import breaks_cusumolsresid
    t = np.arange(len(y), dtype=float)
    X = np.column_stack([np.ones_like(t), t])
    res = OLS(y, X).fit()
    stat, p, _ = breaks_cusumolsresid(res.resid, ddof=2)
    d = np.diff(y)
    best, at = np.inf, None
    for k in range(max(3, len(d) // 10), len(d) - max(3, len(d) // 10)):
        sse = ((d[:k] - d[:k].mean()) ** 2).sum() + ((d[k:] - d[k:].mean()) ** 2).sum()
        if sse < best:
            best, at = sse, k + 1
    return {"cusum_stat": float(stat), "cusum_p": float(p), "likely_shift_at": int(at) if at else None}


def diagnostics(name: str) -> dict:
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.stattools import acf, pacf
    s = series(name)
    y, m = s.to_numpy(), season(name)
    out = {"n": int(len(y)), "period": m, "first": label(s.index[0]), "last": label(s.index[-1])}
    if m > 1 and len(y) >= 2 * m + 1:
        stl = STL(y, period=m, robust=True).fit()
        out["trend_strength"] = strength(np.var(stl.resid), np.var(stl.trend + stl.resid))
        out["seasonal_strength"] = strength(np.var(stl.resid), np.var(stl.seasonal + stl.resid))
        (OUT / "stl").mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"x": [label(i) for i in s.index], "value": y, "trend": stl.trend, "seasonal": stl.seasonal,
                      "remainder": stl.resid}).to_csv(OUT / "stl" / f"{name}.csv", index=False)
    st = stationarity(y)
    out["stationarity"] = {"adf_p": st["levels"][0]["adf_p"], "kpss_p": st["levels"][0]["kpss_p"],
                           "suggested_differencing": st["suggested_differencing"], "verdict": verdict(st)}
    nlags = int(min(max(3 * m, 12), len(y) // 2 - 1, 72))
    out["acf"] = [float(v) for v in acf(y, nlags=nlags, fft=True)]
    out["pacf"] = [float(v) for v in pacf(y, nlags=min(nlags, len(y) // 2 - 1), method="ywm")]
    out["band"] = float(1.96 / math.sqrt(len(y)))
    out["break"] = break_test(y)
    if out["break"]["likely_shift_at"] is not None:
        out["break"]["likely_shift_label"] = label(s.index[out["break"]["likely_shift_at"]])
    an = pd.read_csv(P1 / "anomalies.csv")
    an = an[(an["driver"] == name) & an["value"].notna()]
    out["outliers"] = {"count": int(len(an)), "treatment": "kept in the data and flagged; models were fitted on the real values"}
    return out


# ------------------------------------------------------------------ cross-validation (reliability page)
def theta_folds(name: str, folds: pd.DataFrame) -> pd.DataFrame:
    from statsmodels.tsa.forecasting.theta import ThetaModel
    s = series(name)
    y, m = s.to_numpy(), season(name)
    rows = []
    for (fold, origin), g in folds[folds["model"] == "naive"].groupby(["fold", "origin_index"]):
        train = y[: int(origin)]
        h = int(g["step_ahead"].max())
        t0 = time.time()
        try:
            seasonal = m > 1 and len(train) >= 2 * m and np.all(train > 0)
            res = ThetaModel(train, period=m if seasonal else 1, deseasonalize=seasonal).fit()
            fc = np.asarray(res.forecast(h), float)
            pi = res.prediction_intervals(h, alpha=0.2)
            lo, hi = np.asarray(pi.iloc[:, 0], float), np.asarray(pi.iloc[:, 1], float)
        except Exception:  # noqa: BLE001 - recorded as not run
            continue
        for r in g.itertuples():
            k = int(r.step_ahead) - 1
            rows.append({"driver": name, "model": "theta", "fold": fold, "step_ahead": r.step_ahead, "origin_index": origin,
                         "time": r.time, "actual": r.actual, "forecast": fc[k], "error": r.actual - fc[k],
                         "lo80": lo[k], "hi80": hi[k], "lo95": np.nan, "hi95": np.nan, "fit_seconds": time.time() - t0})
    return pd.DataFrame(rows)


def mase_scale(name: str) -> float:
    y, m = series(name).to_numpy(), season(name)
    m = m if len(y) > 2 * m else 1
    return float(np.mean(np.abs(y[m:] - y[:-m])))


def dm_test(e1: np.ndarray, e2: np.ndarray, h: int) -> tuple[float, float]:
    """Diebold-Mariano on squared errors (e1 = approach, e2 = seasonal naive), Harvey small-sample correction."""
    from scipy import stats
    d = e1 ** 2 - e2 ** 2
    n = len(d)
    if n < 5 or np.allclose(d, 0):
        return float("nan"), float("nan")
    dbar = d.mean()
    gamma = [np.mean((d[k:] - dbar) * (d[: n - k] - dbar)) for k in range(h)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        return float("nan"), float("nan")
    stat = dbar / math.sqrt(var) * math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(stat), float(2 * stats.t.sf(abs(stat), df=n - 1))


def winkler(y, lo, hi, alpha: float) -> float:
    y, lo, hi = map(np.asarray, (y, lo, hi))
    width = hi - lo
    pen = (2 / alpha) * ((lo - y) * (y < lo) + (y - hi) * (y > hi))
    return float(np.mean(width + pen))


def conformal(name: str, f: pd.DataFrame) -> dict:
    """Split-conformal bands from rolling-origin folds, scored out of sample: fold k is covered by a band whose scale
    comes only from folds before k. Nonconformity = |error| / (|forecast| * sqrt(step)) (relative, growing with the
    square root of the step, as the Phase 3 simulation does)."""
    f = f.sort_values(["fold", "step_ahead"]).copy()
    f["score"] = (f["actual"] - f["forecast"]).abs() / (f["forecast"].abs().clip(lower=1e-9) * np.sqrt(f["step_ahead"]))
    folds = sorted(f["fold"].unique())
    cover = {lv: [] for lv in LEVELS}
    boot80, wk80, wk80_boot = [], [], []
    for i, k in enumerate(folds):
        if i < MIN_CAL:
            continue
        cal = f[f["fold"].isin(folds[:i])]["score"].to_numpy()
        test = f[f["fold"] == k]
        n = len(cal)
        for lv in LEVELS:
            q = np.quantile(cal, min(1.0, math.ceil((n + 1) * lv) / n), method="higher")
            half = q * test["forecast"].abs() * np.sqrt(test["step_ahead"])
            inside = (test["actual"] >= test["forecast"] - half) & (test["actual"] <= test["forecast"] + half)
            cover[lv] += inside.tolist()
            if lv == 0.8:
                wk80.append(winkler(test["actual"], test["forecast"] - half, test["forecast"] + half, 0.2))
        if test["lo80"].notna().all():
            boot80 += ((test["actual"] >= test["lo80"]) & (test["actual"] <= test["hi80"])).tolist()
            wk80_boot.append(winkler(test["actual"], test["lo80"], test["hi80"], 0.2))
    all_scores = f["score"].to_numpy()
    n = len(all_scores)
    q_final = {str(lv): float(np.quantile(all_scores, min(1.0, math.ceil((n + 1) * lv) / n), method="higher")) for lv in LEVELS}
    scored = len(cover[0.8])
    return {"q": q_final, "folds": len(folds), "scored_points": scored, "scored_folds": max(0, len(folds) - MIN_CAL),
            "coverage": {str(lv): (float(np.mean(v)) if v else None) for lv, v in cover.items()},
            "coverage_bootstrap_80": float(np.mean(boot80)) if boot80 else None,
            "interval_score_80": float(np.mean(wk80)) if wk80 else None,
            "interval_score_80_bootstrap": float(np.mean(wk80_boot)) if wk80_boot else None}


def cards(name: str, lb: pd.DataFrame, params: pd.DataFrame, arima: pd.DataFrame, chosen: str, theta_ok: bool,
          theta_secs: float) -> list[dict]:
    rows = []
    ldr = lb[lb["driver"] == name].set_index("model")

    def best(family):
        ok = [m for m in family if m in ldr.index and ldr.loc[m, "status"] == "ok"]
        return min(ok, key=lambda m: ldr.loc[m, "cv_mase"]) if ok else (family[0] if family[0] in ldr.index else None)

    picks = {"naive": "naive", "seasonal_naive": "seasonal_naive", "drift": "drift", "ets": best(ETS_FAMILY),
             "arima": best(ARIMA_FAMILY), "chosen": chosen}
    for key, model in picks.items():
        if model is None or model not in ldr.index:
            continue
        r = ldr.loc[model]
        p = params[(params["driver"] == name) & (params["model"] == model)]
        p = p[~p["param"].isin(["validation_mae", "validation_rows", "n_train_rows", "candidates"])]
        settings = "; ".join(f"{a}={str(b)[:24]}" for a, b in zip(p["param"], p["value"]))[:220]
        aicc = p[p["param"].str.lower() == "aicc"]["value"]
        rows.append({"series": name, "card": key, "title": CARD_MODELS[key], "model": model, "status": r["status"],
                     "why_not_run": "" if r["status"] == "ok" else str(r.get("reason", "")),
                     "settings": settings or "none (rule-based)", "aicc": float(aicc.iloc[0]) if len(aicc) else None,
                     "fit_seconds": float(r.get("fit_seconds", np.nan)), "cv_mase": float(r["cv_mase"]) if r["status"] == "ok" else None})
    rows.insert(5, {"series": name, "card": "theta", "title": CARD_MODELS["theta"], "model": "theta",
                    "status": "ok" if theta_ok else "skipped", "why_not_run": "" if theta_ok else "the Theta fit failed at every fold origin",
                    "settings": "theta=2, multiplicative deseasonalising when the period allows", "aicc": None,
                    "fit_seconds": theta_secs, "cv_mase": None})
    return rows


def residuals(name: str, f: pd.DataFrame) -> dict:
    from scipy import stats
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.stattools import acf
    e = f[f["step_ahead"] == 1].sort_values("origin_index")["error"].to_numpy(float)
    out = {"n": int(len(e)), "values": e.tolist()}
    if len(e) >= 8:
        lags = int(min(10, len(e) // 2))
        out["acf"] = [float(v) for v in acf(e, nlags=lags, fft=True)]
        out["band"] = float(1.96 / math.sqrt(len(e)))
        out["ljung_box_p"] = float(acorr_ljungbox(e, lags=[lags], return_df=True)["lb_pvalue"].iloc[0])
        osm, osr = stats.probplot(e, dist="norm", fit=False)
        out["qq"] = {"theoretical": [float(v) for v in osm], "sample": [float(v) for v in osr]}
    return out


def fan(name: str, conf: dict, max_step: int, floor: float | None) -> pd.DataFrame:
    """Conformal 50% and 80% bands around the saved forecast. Width grows with sqrt(step) up to the furthest step the
    cross-validation scored (`max_step`) and stays there beyond it (no unchecked extrapolation); series that cannot go
    below zero are floored at `floor`."""
    fc = pd.read_csv(FC / f"{name}.csv")
    pt = fc[fc["sample_id"] == -1].sort_values("period_index")
    h = pt["period_index"].to_numpy(float)
    c = pt["value"].to_numpy(float)
    out = {"period_index": pt["period_index"].astype(int), "x": pt["calendar_month"] if "calendar_month" in pt else h,
           "centre": c}
    for lv in ("0.5", "0.8"):
        half = conf["q"][lv] * np.abs(c) * np.sqrt(np.minimum(h, max_step))
        lo = c - half if floor is None else np.maximum(c - half, floor)
        out[f"lo{int(float(lv) * 100)}"], out[f"hi{int(float(lv) * 100)}"] = lo, c + half
    paths = fc[fc["sample_id"] >= 0].pivot_table(index="period_index", columns="sample_id", values="value")
    out["boot_lo80"] = paths.quantile(0.1, axis=1).reindex(pt["period_index"]).to_numpy()
    out["boot_hi80"] = paths.quantile(0.9, axis=1).reindex(pt["period_index"]).to_numpy()
    return pd.DataFrame(out)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    (OUT / "fan").mkdir(exist_ok=True)
    folds = pd.read_csv(P2 / "cv_folds.csv")
    lb = pd.read_csv(P2 / "leaderboard.csv")
    params = pd.read_csv(P2 / "params.csv")
    arima = pd.read_csv(P2 / "arima_params.csv")
    chosen = pd.read_csv(P2 / "chosen_models.csv").set_index("driver")["chosen_model"]
    diag, conf, resid, metrics, horizon, dms, card_rows, extra = {}, {}, {}, [], [], [], [], []
    for name in SEVEN:
        t0 = time.time()
        diag[name] = diagnostics(name)
        f = folds[folds["driver"] == name]
        th = theta_folds(name, f)
        extra.append(th)
        f = pd.concat([f, th.drop(columns="fit_seconds")], ignore_index=True) if len(th) else f
        scale = mase_scale(name)
        sn = f[f["model"] == "seasonal_naive"].set_index(["fold", "step_ahead"])["error"]
        h = int(f["step_ahead"].max())
        for model, g in f.groupby("model"):
            e = g["error"].to_numpy(float)
            inside = ((g["actual"] >= g["lo80"]) & (g["actual"] <= g["hi80"])) if g["lo80"].notna().all() else None
            metrics.append({"series": name, "model": model, "n": len(e), "mae": float(np.mean(np.abs(e))),
                            "rmse": float(np.sqrt(np.mean(e ** 2))), "mase": float(np.mean(np.abs(e)) / scale),
                            "bias": float(np.mean(e)), "coverage80": float(inside.mean()) if inside is not None else None})
            for step, gs in g.groupby("step_ahead"):
                es = gs["error"].to_numpy(float)
                horizon.append({"series": name, "model": model, "step": int(step), "mae": float(np.mean(np.abs(es))),
                                "mase": float(np.mean(np.abs(es)) / scale)})
            if model != "seasonal_naive":
                both = g.set_index(["fold", "step_ahead"])["error"].to_frame("e1").join(sn.rename("e2"), how="inner")
                stat, p = dm_test(both["e1"].to_numpy(float), both["e2"].to_numpy(float), h)
                dms.append({"series": name, "model": model, "dm_stat": stat, "p_value": p, "n": len(both)})
        ch = chosen.get(name)
        fc_chosen = f[f["model"] == ch]
        conf[name] = conformal(name, fc_chosen)
        conf[name]["model"] = ch
        resid[name] = residuals(name, fc_chosen)
        y = series(name)
        conf[name]["max_step"] = int(folds.loc[folds["driver"] == name, "step_ahead"].max())
        fan(name, conf[name], conf[name]["max_step"], 0.0 if float(y.min()) >= 0 else None).to_csv(OUT / "fan" / f"{name}.csv", index=False)
        card_rows += cards(name, lb, params, arima, ch, len(th) > 0,
                           float(th["fit_seconds"].mean()) if len(th) else float("nan"))
        print(f"{name:30s} folds={conf[name]['folds']:3d} cover80={conf[name]['coverage']['0.8']}"
              f" (bootstrap {conf[name]['coverage_bootstrap_80']})  {time.time() - t0:.1f}s", flush=True)
    (OUT / "diagnostics.json").write_text(json.dumps(diag, indent=1), encoding="utf-8")
    (OUT / "conformal.json").write_text(json.dumps(conf, indent=1), encoding="utf-8")
    (OUT / "residuals.json").write_text(json.dumps(resid), encoding="utf-8")
    pd.DataFrame(metrics).to_csv(OUT / "cv_metrics.csv", index=False)
    pd.DataFrame(horizon).to_csv(OUT / "cv_horizon.csv", index=False)
    pd.DataFrame(dms).to_csv(OUT / "dm_tests.csv", index=False)
    pd.DataFrame(card_rows).to_csv(OUT / "model_cards.csv", index=False)
    pd.concat(extra, ignore_index=True).to_csv(OUT / "cv_folds_extra.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
