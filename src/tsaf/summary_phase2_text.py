"""Sections 9-11 of PHASE2_SUMMARY.md: review talking points, limitations, deviations."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase2 as P2
from optional import has_xgboost
from tsaf.report import fmt


def _row(chosen_rows, name):
    return next((r for r in chosen_rows if r["driver"] == name), None)


def review(results, diags, chosen_rows, lb) -> list[str]:
    ok = lb[lb["status"] == "ok"]
    n_models = ok["model"].nunique()
    k = len(chosen_rows)
    wins = [r for r in chosen_rows if r["beats_seasonal_naive"]]
    kept = [r["driver"] for r in chosen_rows if not r["beats_seasonal_naive"]]
    s = [f"Phase 2 scored {n_models} different models on {k} drivers, every model on the same "
         f"expanding-window folds and hold-out as the Phase 1 baselines."]
    s.append(f"A model beat seasonal naive on mean CV MASE for {len(wins)} of {k} drivers"
             + (f"; seasonal naive is kept for {', '.join(kept)}." if kept else "."))
    if wins:
        gain = max(wins, key=lambda r: 1 - r["cv_mase"] / r["seasonal_naive_cv_mase"])
        s.append(f"The largest gain is on {gain['driver']}: {gain['chosen_model']} reaches CV MASE "
                 f"{fmt(gain['cv_mase'])} against {fmt(gain['seasonal_naive_cv_mase'])} for seasonal naive "
                 f"({1 - gain['cv_mase'] / gain['seasonal_naive_cv_mase']:.0%} lower).")
    for name in ("burst_tokens_total_daily", "burst_requests_hourly"):
        r = _row(chosen_rows, name)
        if r:
            s.append(f"For {name} the chosen model is {r['chosen_model']} ({r['family']}), CV MASE "
                     f"{fmt(r['cv_mase'])} and hold-out MASE {fmt(r['holdout_mase'])}.")
    worse = [r for r in chosen_rows if r["holdout_mase"] > r["cv_mase"]]
    s.append(f"Hold-out MASE is higher than CV MASE for {len(worse)} of {k} chosen models, so the final "
             f"two weeks (or last periods) are harder than the backtest windows; the hold-out was never "
             f"used for choosing.")
    fams = sorted({r["family"] for r in chosen_rows})
    s.append(f"The chosen models come from these families: {', '.join(fams)}; no single family wins everywhere.")
    flagged = ok["flags"].str.contains("coverage", na=False).sum()
    nmin = min(dr["n_folds"] for dr in results)
    s.append(f"Empirical leave-one-fold-out intervals are too narrow for {flagged} of {len(ok)} model-driver "
             f"pairs; with as few as {nmin} folds each interval rests on {nmin - 1} errors per step.")
    d77 = next((d["day77"] for d in diags if d.get("day77")), None)
    if d77:
        s.append(f"The day-77 outage check is {d77['status']} (|robust z| {fmt(d77['z'])} against "
                 f"{P2.ANOMALY_Z}).")
    s.append("Hyper-parameters were chosen on the first training window only and kept fixed, so no fold "
             "ever saw its own test data.")
    return ["## 9. What to say in the review", "", " ".join(s[:10]), ""]


def _hourly_note(results) -> list[str]:
    """Which positions the (capped) hourly folds test, read from the run's CV settings."""
    out = []
    for dr in results:
        if dr["entry"]["grain"] == "hourly":
            cv, n = dr["cv"], dr["n_folds"]
            last = cv["initial"] + (n - 1) * cv["step"] + cv["h"] - 1
            out.append(f"- {dr['entry']['name']}: the {n} capped folds (Phase 1 settings) test positions "
                       f"{cv['initial']}-{last} of the {len(dr['pre'])} pre-hold-out hours, not the most recent weeks.")
    return out


def limitations(results, lb) -> list[str]:
    folds = {dr["entry"]["name"]: dr["n_folds"] for dr in results}
    few = [d for d, n in folds.items() if n < 5]
    out = ["## 10. Limitations", "",
           "- Short window: BurstGPT has 87 clean days (12 weeks)"
           + (f"; {', '.join(few)} have fewer than 5 folds, so mean CV MASE rests on few windows." if few else "."),
           "- Hyper-parameters (ARIMA orders, moving-average window, Ridge alpha) are tuned on the first "
           "training window only; smoothing parameters are re-estimated in every fold.",
           "- Intervals are empirical (leave-one-fold-out quantiles of absolute errors); with few folds the "
           "95% quantile is close to the largest of a handful of errors and under-covers.",
           "- The ensemble's two components are picked by the same CV MASE it is then scored on, so its CV "
           "score is optimistic; its hold-out score is the fair check.",
           "- BurstGPT weekend (day_of_cycle 4 and 5) is inferred from lower volume, not known.",
           f"- Prophet would use an arbitrary start date ({P2.PROPHET_START}) as an index only.",
           *_hourly_note(results),
           "- All models forecast the raw scale (no log transform), and forecasts are clipped at 0."]
    return out + [""]


def _sarimax_d_changes(results) -> list[str]:
    out = []
    for dr in results:
        r = dr["results"].get("sarimax")
        if r is not None and r.status == "ok" and r.params.get("D_used") != dr["entry"]["D"]:
            out.append(dr["entry"]["name"])
    return out


def deviations(results, args) -> list[str]:
    lag = P2.EXTRA_SERIES["burst_tokens_total_daily"]["lag"]
    dchg = _sarimax_d_changes(results)
    items = [
        "Day-77 check: day 77 lies inside the BurstGPT hold-out (days 73-86), so the anomaly screen uses the "
        "chosen model refit on the full window (days 0-86); the other residual diagnostics use the "
        "pre-hold-out fit as specified.",
        f"The requests feature is lagged {lag} days, not 7: the hold-out (and Phase 3) horizon is 14 days, "
        "and a 7-day lag would need future requests there.",
        "Machine-learning models also run for wildchat_conversations_daily (a daily series with more "
        "observations than BurstGPT); its is_weekend is the real calendar Saturday/Sunday.",
        "SARIMAX for daily series uses is_weekend (also for WildChat daily); for quarterly and monthly "
        "series no exogenous variable is defined, so SARIMAX is skipped there.",
        "Hourly SARIMAX uses Fourier terms (K=3 for 24 and 168) with D=0: the deterministic terms replace "
        "the seasonal difference D=1 from the handoff.",
        "ARIMA-family forecasts that are non-finite or move more than 5x the training range (an explosive "
        "unconstrained AR part) are treated as failed fits and that fold falls back to ARIMA(1, d, 0); "
        "the fallbacks are listed in params.csv and in the leaderboard flags.",
        "Trend term in the ARIMA family: constant when d + D = 0, drift when only d = 1, no trend term otherwise.",
        "Every forecast is clipped at 0 because all modelled series are non-negative.",
        "The moving-average window is chosen by the MAE of a flat forecast on the last 20% of the first "
        "training window; Ridge alpha by one-step MAE on the same share.",
        "Over-differencing flag from Phase 1 (ECI, PPI): d=2 is not refit; the comparison of D=0 versus "
        "D=1 is made by CV MASE of ARIMA (D=0) against SARIMA (D=1), because AICc is not comparable "
        "across differencing orders.",
        "Prophet is filed under the family 'deep' (the optional-challenger family) since the prompt gives it no family.",
        f"Each model has a wall-clock budget of {P2.MODEL_BUDGET_S:.0f} s per driver, checked between fits.",
        "Hold-out intervals for steps beyond the CV horizon reuse the quantile of the last CV step.",
        "ARIMA parameter tables for every ARIMA-family fit are written to an extra table, arima_params.csv.",
    ]
    if dchg:
        items.insert(4, "SARIMAX uses D=0 instead of the handoff D=1 for " + ", ".join(dchg) + ": is_weekend "
                     "is a period-7 dummy, so seasonal differencing at 7 would wipe it out.")
    if not has_xgboost():
        items.append("xgboost is not installed: HistGradientBoostingRegressor is used instead.")
    if not getattr(args, "with_lstm", False):
        items.append("The LSTM is off by default and did not run (use --with-lstm).")
    return ["## 11. Deviations from the Phase 2 prompt", ""] + [f"- {i}" for i in items] + [""]
