"""Builds PHASE2_SUMMARY.md from the run's results (no hard-coded numbers, no placeholders)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config_phase2 as P2
from optional import has_xgboost
from tsaf.report import fmt, md_table
from tsaf.report_phase2 import leaderboard

SEG = ("burst_tokens_api_daily", "burst_tokens_chat_daily")


def _pct(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.0%}"


def _ok(lb: pd.DataFrame) -> pd.DataFrame:
    return lb[(lb["status"] == "ok") & np.isfinite(lb["cv_mase"])]


def s1_drivers(results, skipped, lb) -> list[str]:
    out = ["## 1. Drivers modelled and skipped", ""]
    for dr in results:
        e = dr["entry"]
        n_ok = int(((lb["driver"] == e["name"]) & (lb["status"] == "ok")).sum())
        out.append(f"- `{e['name']}`: {e['grain']}, n = {len(dr['series'])}, season {e['season']}, "
                   f"d = {e['d']}, D = {e['D']}, {e['decomposition']}; {dr['n_folds']} CV folds of "
                   f"{dr['cv']['h']} steps, hold-out {dr['cv']['holdout']}; {n_ok} models scored.")
    out += ["", "Skipped drivers:" if skipped else "No driver was skipped.", ""]
    out += [f"- `{s['name']}`: {s['reason']}" for s in skipped]
    sk = lb[lb["status"] == "skipped"].groupby(["model", "reason"])["driver"].apply(
        lambda d: ", ".join(d)).reset_index()
    out += ["", "Models not run for some drivers (by rule):", ""]
    out += [f"- `{r.model}` for {r.driver}: {r.reason}" for r in sk.itertuples()]
    failed = lb[lb["status"] == "failed"]
    out += ["", "Failed models: " + ("no model failed." if failed.empty else "")]
    out += [f"- `{r.model}` for `{r.driver}`: {r.reason}" for r in failed.itertuples()]
    return out + [""]


def s2_leaderboards(lb) -> list[str]:
    out = ["## 2. Leaderboard per driver (top 5 by mean CV MASE)", ""]
    for d, g in _ok(lb).groupby("driver", sort=False):
        top = g.sort_values("cv_mase", kind="stable").head(5)
        t = top[["model", "family", "cv_mase", "cv_smape", "share_beats_snaive", "coverage_80", "holdout_mase"]]
        sn = g.loc[g["model"] == "seasonal_naive", "cv_mase"]
        out += [f"### {d}", "", md_table(t.fillna(np.nan)), "",
                f"Seasonal naive CV MASE: {fmt(float(sn.iloc[0])) if len(sn) else 'n/a'}.", ""]
    return out


def s3_chosen(chosen_rows) -> list[str]:
    df = pd.DataFrame(chosen_rows)[["driver", "chosen_model", "family", "cv_mase", "holdout_mase",
                                    "seasonal_naive_cv_mase", "beats_seasonal_naive"]].copy()
    df["beats_seasonal_naive"] = df["beats_seasonal_naive"].map({True: "yes", False: "no"})
    out = ["## 3. Chosen model per driver", "", md_table(df), "", "Rule applied per driver:", ""]
    out += [f"- `{r['driver']}`: {r['why']}." for r in chosen_rows]
    n_sn = sum(r["chosen_model"] == "seasonal_naive" for r in chosen_rows)
    if n_sn:
        out += ["", f"Seasonal naive is kept for {n_sn} driver(s): no model beat it in the backtest. "
                    "A baseline winning is a valid, honest result."]
    return out + [""]


def _best_non_baseline(lb, d) -> pd.Series | None:
    g = _ok(lb)
    g = g[(g["driver"] == d) & (g["family"] != "baseline") & (g["family"] != "ensemble")]
    return None if g.empty else g.sort_values("cv_mase", kind="stable").iloc[0]


def s4_api_chat(lb, chosen_rows) -> list[str]:
    out = ["## 4. API versus chat", ""]
    ch = {r["driver"]: r for r in chosen_rows}
    if not all(s in ch for s in SEG):
        return out + ["Not available: one of the two segment drivers was not modelled.", ""]
    for s in SEG:
        b = _best_non_baseline(lb, s)
        best = f"best single non-baseline model `{b['model']}` ({b['family']}, CV MASE {fmt(b['cv_mase'])})" if b is not None else "no non-baseline model"
        out.append(f"- `{s}`: chosen `{ch[s]['chosen_model']}` ({ch[s]['family']}), CV MASE "
                   f"{fmt(ch[s]['cv_mase'])}; {best}.")
    a, c = (ch[s] for s in SEG)
    ba, bc = (_best_non_baseline(lb, s) for s in SEG)
    same = a["family"] == c["family"]
    out += ["", f"Chosen model families {'are the same' if same else 'differ'} "
                f"({a['family']} for API, {c['family']} for chat)."]
    if ba is not None and bc is not None:
        out.append(f"Best non-baseline model types {'match' if ba['family'] == bc['family'] else 'differ'}: "
                   f"{ba['family']} for API, {bc['family']} for chat.")
    return out + [""]


def s5_requests(lb) -> list[str]:
    out = ["## 5. Does `requests` help as an extra feature? (BurstGPT total tokens)", ""]
    g = lb[lb["driver"] == "burst_tokens_total_daily"].set_index("model")
    pairs = [(m, f"{m}_with_requests") for m in ("ridge", "random_forest",
                                                  "xgboost" if has_xgboost() else "hist_gradient_boosting")]
    lines, helped = [], 0
    for a, b in pairs:
        if a in g.index and b in g.index and g.loc[a, "status"] == "ok" and g.loc[b, "status"] == "ok":
            d = g.loc[b, "cv_mase"] - g.loc[a, "cv_mase"]
            helped += d < 0
            lines.append(f"- `{a}`: CV MASE {fmt(g.loc[a, 'cv_mase'])} without, {fmt(g.loc[b, 'cv_mase'])} "
                         f"with requests ({'better' if d < 0 else 'worse'} by {fmt(abs(d))}).")
    if not lines:
        return out + ["Not run (driver or ML models not available in this run).", ""]
    lag = P2.EXTRA_SERIES["burst_tokens_total_daily"]["lag"]
    return out + lines + ["", f"Requests (lagged {lag} days) helped {helped} of {len(lines)} ML models."]  + [""]


def s6_optional(lb) -> list[str]:
    out = ["## 6. Prophet and LSTM", ""]
    for m in ("prophet", "lstm"):
        g = lb[lb["model"] == m]
        for r in g.itertuples():
            if r.status == "ok":
                sn = lb[(lb["driver"] == r.driver) & (lb["model"] == "seasonal_naive")]["cv_mase"]
                out.append(f"- `{m}` on `{r.driver}`: ran, CV MASE {fmt(r.cv_mase)} (seasonal naive "
                           f"{fmt(float(sn.iloc[0]))}), hold-out MASE {fmt(r.holdout_mase)}.")
            elif not str(r.reason).startswith(("Prophet runs only", "LSTM runs only")):
                out.append(f"- `{m}` on `{r.driver}`: {r.status}: {r.reason}.")
    if any(lb["model"].eq("prophet") & lb["status"].eq("ok")):
        out.append(f"- Prophet uses the arbitrary start date {P2.PROPHET_START} purely as an index; "
                   "BurstGPT has no calendar dates.")
    return out + [""]


def s7_diagnostics(diags, lb) -> list[str]:
    out = ["## 7. Residual diagnostics and interval coverage", "",
           "Chosen model refit on the data before the hold-out; Ljung-Box at lags 10 and 2 x season (5% level).", ""]
    for d in diags:
        st = d["stats"]
        if "white_noise" not in st:
            out.append(f"- `{d['driver']}` ({d['model']}): diagnostics failed: {st.get('error', 'unknown error')}.")
            continue
        lbp = ", ".join(f"lag {lag}: p = {fmt(st[f'ljung_box_p_lag{lag}'])}" for lag in st["ljung_box_lags"].split(","))
        out.append(f"- `{d['driver']}` ({d['model']}): residuals look like white noise: **{st['white_noise']}** "
                   f"({lbp}); mean {fmt(st['resid_mean'])}, std {fmt(st['resid_std'])}, skewness "
                   f"{fmt(st['resid_skew'])}; Shapiro-Wilk p = {fmt(st['shapiro_p'])} (normal: {st['normal_residuals']}).")
    ok = lb[lb["status"] == "ok"]
    flagged = ok[ok["flags"].str.contains("coverage", na=False)]
    out += ["", f"Coverage warnings: {len(flagged)} of {len(ok)} scored model-driver pairs have 80% coverage "
                f"below {P2.COVERAGE_FLAG[0.80]:.0%} or 95% coverage below {P2.COVERAGE_FLAG[0.95]:.0%}.", ""]
    for d, g in ok.groupby("driver", sort=False):
        if g["coverage_80"].notna().any():
            out.append(f"- `{d}`: 80% coverage from {_pct(g['coverage_80'].min())} to {_pct(g['coverage_80'].max())}, "
                       f"95% from {_pct(g['coverage_95'].min())} to {_pct(g['coverage_95'].max())}; "
                       f"{int(g['flags'].str.contains('coverage').sum())} model(s) flagged.")
        else:
            out.append(f"- `{d}`: intervals skipped (fewer than {P2.MIN_FOLDS_FOR_INTERVALS} folds).")
    return out + [""]


def s8_day77(diags) -> list[str]:
    d77 = next((d["day77"] for d in diags if d.get("day77")), None)
    out = ["## 8. Day-77 anomaly check", ""]
    if not d77:
        return out + ["Not run: BurstGPT total tokens was not modelled in this run.", ""]
    return out + [f"Result: **{d77['status']}**. {d77['detail']}.", "",
                  "Day 77 lies inside the hold-out (days 73-86), so the screen uses the residuals of the "
                  "chosen model refit on the full modelling window (days 0-86); robust z = "
                  f"0.6745 (r - median) / MAD, threshold {P2.ANOMALY_Z}, not tuned.", ""]


def build_summary(results, diags, chosen_rows, skipped, args) -> str:
    from tsaf.summary_phase2_text import deviations, limitations, review
    lb = leaderboard(results)
    head = ["# Phase 2 summary: forecasting models and rolling backtests", "",
            f"Generated by `python src/run_phase2.py{' --fast' if args.fast else ''}"
            f"{' --with-lstm' if args.with_lstm else ''}`; every number comes from this run.", ""]
    parts = (head + s1_drivers(results, skipped, lb) + s2_leaderboards(lb) + s3_chosen(chosen_rows)
             + s4_api_chat(lb, chosen_rows) + s5_requests(lb) + s6_optional(lb) + s7_diagnostics(diags, lb)
             + s8_day77(diags) + review(results, diags, chosen_rows, lb) + limitations(results, lb)
             + deviations(results, args))
    return "\n".join(parts) + "\n"
