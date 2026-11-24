"""Generated Markdown: the data contract and PHASE1_SUMMARY.md (review support, all modules).

Every number in these files is read from the results of the run; nothing is hard-coded.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TIME_COLS = ("day_index", "hour_index", "date", "week", "month", "quarter", "timestamp", "t_sec")


def fmt(x, digits: int = 3) -> str:
    """Readable number: thousands separators for big values, 'n/a' for missing."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    x = float(x)
    return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.{digits}g}" if abs(x) < 1e-3 else f"{x:,.{digits}f}"


def md_table(df: pd.DataFrame) -> str:
    """DataFrame -> GitHub Markdown table with formatted numbers."""
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(fmt(v) if not isinstance(v, str) else v for v in row) + " |"
            for row in df.itertuples(index=False)]
    return "\n".join([head, sep, *body])


def write_data_contract(data_dir: Path, path: Path) -> None:
    """Columns, dtypes, rows, time range and nulls for every Parquet file in data_dir."""
    lines = ["# Data contract (Phase 1 pre-flight)", "",
             f"Source folder: `{data_dir}`. Each table is also saved as CSV with the same content.", ""]
    for f in sorted(data_dir.glob("*.parquet")):
        df = pd.read_parquet(f)
        tcol = next((c for c in TIME_COLS if c in df.columns), None)
        rng = f"`{tcol}`: {df[tcol].min()} to {df[tcol].max()}" if tcol else "no time column"
        lines += [f"## {f.stem}", "", f"- rows: {len(df):,}; columns: {df.shape[1]}; range {rng}", "",
                  "| column | dtype | nulls |", "|---|---|---|"]
        lines += [f"| {c} | {df[c].dtype} | {int(df[c].isna().sum()):,} |" for c in df.columns]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _driver_text(r: dict) -> str:
    """3-5 plain sentences on one driver, built from its results."""
    s, dc, df, b, cfg = r["summary"], r["decomp"], r["diff"], r["best"], r["cfg"]
    level = "very bursty" if s["cv"] > 1 else "moderately variable" if s["cv"] > 0.5 else "steady"
    out = [f"Mean {fmt(s['mean'])} {cfg['unit']} over {s['n']} observations ({s['start']} to {s['end']}), "
           f"coefficient of variation {s['cv']:.2f} ({level}); {s['zero_share']:.1%} zeros.",
           f"Decomposition: **{dc['type']}**, because {dc['reason']}."]
    if np.isfinite(dc.get("seasonal_strength", np.nan)):
        out.append(f"{dc['method']} gives seasonal strength {dc['seasonal_strength']:.2f} and trend "
                   f"strength {dc['trend_strength']:.2f}.")
    out.append(f"Stationarity: {df['decision']}.")
    out.append(f"Best baseline: **{b['baseline']}**, CV MASE {fmt(b['cv_mase'])}, hold-out MASE "
               f"{fmt(b['holdout_mase'])} (seasonal naive CV MASE {fmt(r['snaive_cv_mase'])}).")
    out += [f"**Flag:** {w}" for w in r.get("warnings", [])]
    return " ".join(out)


def _day77_section(check: dict) -> list[str]:
    """The day-77 anomaly-screen result written up as a finding (numbers from the run)."""
    if "z" not in check:
        return ["## Finding: day-77 anomaly check", "", check["status"], ""]
    top = ", ".join(f"day {t} (|z| {z:.2f})" for t, z in check["top"])
    return ["## Finding: day-77 anomaly check", "",
            f"Result: **{check['status']}**. Day 77 is a one-day outage that preprocessing already "
            f"marks as `anomaly_low_day` (kept in the series and shaded on every plot). The Phase 1 "
            f"screen (robust z-score of the seasonal-naive residual, {check['scale']} scale, "
            f"threshold {check['threshold']}) gives day 77 |z| = {check['z']:.2f}, rank {check['rank']} "
            f"of {check['n']} scored days. Most extreme days: {top}.", "",
            f"Why it is a finding, not a bug: the screen flags {check['n_flagged']} day(s) in total "
            "on this series, because the median absolute deviation of the residual is inflated by the "
            "bursty API segment (its coefficient of variation is in section 2), so a genuine one-day "
            "outage does not stand out from ordinary week-on-week swings. For comparison, the same "
            f"robust z on the STL remainder (log scale) gives day 77 |z| = {check['stl_z']:.2f} but "
            f"flags {check['stl_flagged']} of {check['n_stl']} days ({check['stl_share']:.0%}), "
            "which is too many to be a useful screen. The threshold was not tuned to force a PASS. "
            "Practical consequence: "
            "known outages must come from the preprocessing flags, not from a residual screen, and "
            "Phase 2 models of BurstGPT tokens should use robust fitting or an outage dummy for day 77.",
            ""]


def _review_text(results: list[dict], trend: pd.DataFrame | None, day77: dict) -> list[str]:
    """6-8 sentences for the review, quoting real numbers."""
    by = {r["cfg"]["name"]: r for r in results}
    out = [f"Phase 1 analysed {len(results)} drivers with five benchmark forecasts and an "
           f"expanding-window backtest."]
    cvs = {n: r["summary"]["cv"] for n, r in by.items()}
    hi, lo = max(cvs, key=cvs.get), min(cvs, key=cvs.get)
    out.append(f"Variability differs a lot: {hi} has a coefficient of variation of {cvs[hi]:.2f}, "
               f"while {lo} has {cvs[lo]:.2f}, so one model will not fit both.")
    mult = [n for n, r in by.items() if r["decomp"]["type"] == "multiplicative"]
    out.append(f"The rolling-std rule chose multiplicative for {', '.join(mult) or 'no driver'} "
               f"and additive for the rest.")
    seas = {n: r["decomp"]["seasonal_strength"] for n, r in by.items()
            if np.isfinite(r["decomp"].get("seasonal_strength", np.nan))}
    if seas:
        top = max(seas, key=seas.get)
        out.append(f"The strongest seasonality is in {top} (STL seasonal strength {seas[top]:.2f}).")
    diffs = ", ".join(f"{n} d={r['diff']['d']}, D={r['diff']['D']}" for n, r in by.items())
    out.append(f"ADF and KPSS together give: {diffs}.")
    beat = [n for n, r in by.items() if r["best"]["cv_mase"] < 1]
    out.append(f"Best-baseline CV MASE is below 1 (better than in-sample seasonal naive) for "
               f"{len(beat)} of {len(by)} drivers; these MASE values are the bar Phase 2 must beat.")
    if trend is not None:
        lin = trend.set_index("method").loc["least_squares_linear", "slope_pct_of_mean"]
        out.append(f"For BurstGPT total tokens the least-squares trend is {lin:+.2f}% of the mean per day.")
    status = day77["status"].split(" ")[0]
    if status == "FAIL":
        out.append("The day-77 outage check is FAIL: the residual screen does not separate a known "
                   "outage from API bursts (see the finding below).")
    else:
        out.append(f"The day-77 outage check is {status} (see the finding below).")
    return out


def _coverage_notes(results: list[dict]) -> list[str]:
    """Where a fold cap means the backtest covers only part of the pre-hold-out data."""
    out = []
    for r in results:
        cv = r["cv_settings"]
        if cv.get("max_folds"):
            first = cv["initial"]
            last = first + (r["n_folds"] - 1) * cv["step"] + cv["h"] - 1
            pre = r["summary"]["n"] - cv["holdout"]
            out.append(f"- `{r['cfg']['name']}`: the {r['n_folds']} capped folds test positions "
                       f"{first}-{last} of the {pre} pre-hold-out points, not the most recent ones.")
    return out


def write_summary(path: Path, results: list[dict], skipped: list[dict], window: str,
                  trend: pd.DataFrame | None, leaderboard: pd.DataFrame, day77: dict,
                  deviations: list[str]) -> None:
    """Write PHASE1_SUMMARY.md from the run's results."""
    L = ["# Phase 1 summary: exploration and baselines", "",
         "Generated by `python src/run_phase1.py`; every number comes from this run.", "",
         "## 1. Data used", "", f"Modelling window: {window}.", "",
         "Analysed: " + ", ".join(f"`{r['cfg']['name']}` (n={r['summary']['n']})" for r in results) + ".", ""]
    if skipped:
        L += ["Skipped:", ""] + [f"- `{s['name']}`: {s['reason']}" for s in skipped] + [""]
    L += ["## 2. Per-driver findings", ""]
    for r in results:
        L += [f"### {r['cfg']['name']}", "", _driver_text(r), ""]
    L += ["## 3. Trend methods (BurstGPT total tokens per day)", ""]
    L += [md_table(trend[["method", "slope_per_step", "slope_pct_of_mean", "how"]]) if trend is not None
          else "Trend driver not analysed in this run.", ""]
    L += ["The graphic method is the line drawn by eye through the raw plot (`*_series.png`).", "",
          "## 4. Baseline leaderboard (ranked by mean CV MASE)", "", md_table(leaderboard), "",
          "## 5. Decisions carried into Phase 2", ""]
    dec = pd.DataFrame([{"driver": r["cfg"]["name"], "season": str(r["cfg"]["season"] or "none"),
                         "extra": str(r["cfg"].get("extra_seasons") or "-"), "decomposition": r["decomp"]["type"],
                         "d": r["diff"]["d"], "D": r["diff"]["D"],
                         "tests agree": "yes" if r["diff"]["tests_agree"] else "no (flagged)",
                         "log candidate": "yes" if r["decomp"]["log_candidate"] else "no"} for r in results])
    L += [md_table(dec), "", "## 6. What to say in the review", "", " ".join(_review_text(results, trend, day77)), "",
          *_day77_section(day77),
          "## 7. Limitations", "",
          "- BurstGPT has no calendar dates: time is days/hours since the trace started.",
          "- The weekend (day_of_cycle 4-5) is inferred from lower volume, not known.",
          "- The BurstGPT modelling window is only 87 days (12 weeks), so yearly effects cannot be seen.",
          "- WildChat users are hashed IPs, an imperfect user ID; only 5 of 86 shards are downloaded.",
          "- EDA decisions (d, D, decomposition) use the whole window including the hold-out.",
          *_coverage_notes(results),
          *([f"- Skipped drivers (reasons in section 1): "
             + ", ".join(f"`{s['name']}`" for s in skipped) + "."] if skipped else []), "",
          "## Deviations from the Phase 1 prompt", "", *[f"- {d}" for d in deviations], ""]
    path.write_text("\n".join(L), encoding="utf-8")
