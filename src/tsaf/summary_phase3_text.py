"""Sections 8-10 of PHASE3_SUMMARY.md: review talking points, limitations, deviations."""
from __future__ import annotations

import numpy as np

import config
import config_phase3 as P3
from tsaf.report import fmt


def _pct(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.0%}"


def review(results, extras, inputs) -> list[str]:
    ms = [r["manifest"] for r in results]
    chk = extras["check"]
    allr = chk[chk["segment"] == "all"]
    s = [f"Phase 3 turns the chosen model of each of the {len(ms)} drivers into {P3.N_SAMPLES} simulated future "
         "paths plus a point forecast, all written in one ten-column table format."]
    fb = [m["driver"] for m in ms if m["fallback_used"]]
    s.append("Every chosen model refitted cleanly on the full window." if not fb else
             f"{len(fb)} driver(s) fell back to seasonal naive: {', '.join(fb)}.")
    s.append("Paths are built by resampling whole vectors of out-of-sample backtest errors, scaled to the current "
             f"level for the {sum(m['relative_errors'] for m in ms)} strictly positive series.")
    ok = allr[~allr["flag"]]
    s.append(f"On the Phase 2 holdout the simulated 80% band covered between {_pct(allr['coverage_80'].min())} and "
             f"{_pct(allr['coverage_80'].max())} of the actual values; {len(ok)} of {len(allr)} drivers pass both "
             "coverage thresholds.")
    moved = allr[(allr["coverage_80_after"] != allr["coverage_80_before"]) | (allr["coverage_95_after"] != allr["coverage_95_before"])]
    s.append("Recency weights and level matching were tested on the last backtest folds only; "
             + (", ".join(f"{r.driver} moved from {_pct(r.coverage_80_before)} to {_pct(r.coverage_80_after)} (80%) and "
                          f"{_pct(r.coverage_95_before)} to {_pct(r.coverage_95_after)} (95%)" for r in moved.itertuples())
                if len(moved) else "no driver changed") + ".")
    hr = chk[chk["segment"] != "all"]
    if len(hr) == 2:
        s.append(f"For hourly requests the 80% band covered {_pct(hr['coverage_80'].iloc[0])} of hours 1 to "
                 f"{P3.HOURLY_SPLIT} and {_pct(hr['coverage_80'].iloc[1])} of the later hours.")
    rr = extras.get("run_rate_summary")
    if rr is not None and len(rr):
        t = rr.iloc[0]
        s.append(f"The 30-day run-rate of {t['driver']} has P10 {t['p10'] / 1e6:,.0f}M, P50 {t['p50'] / 1e6:,.0f}M and "
                 f"P90 {t['p90'] / 1e6:,.0f}M tokens, with the last 16 days extrapolated.")
    if inputs.get("input_token_share") is not None:
        s.append(f"Input tokens are {_pct(inputs['input_token_share'])} of all BurstGPT tokens in the window.")
    s.append(f"The scenario table holds {len(extras['scenarios'])} assumption rows taken directly from the METR and "
             "FRED tracker data; they are kept apart from the forecasts.")
    s.append("Reruns give identical files because every driver has a fixed seed.")
    return ["## 8. What to say in the review", "", " ".join(s[:10]), ""]


def limitations(results) -> list[str]:
    few = [r["manifest"]["driver"] for r in results if r["manifest"]["n_folds_used"] < 5]
    return ["## 9. Limitations", "",
            "- Short window: BurstGPT has 87 clean days" + (f"; {', '.join(few)} have fewer than 5 backtest folds "
                                                            "to resample from." if few else "."),
            "- BurstGPT has no calendar dates; periods are days or hours after day 86 and the weekend is inferred.",
            "- For dated sources (WildChat, ECI, PPI) `calendar_month` is the month after the data end, which can "
            "lie in the past relative to today.",
            "- The bootstrap assumes future errors look like past backtest errors; a regime change is not covered.",
            "- Whole-vector resampling can only reuse the folds that exist: with k folds each step has at most k "
            "distinct path values, so the 80% and 95% bands are close to the smallest and largest fold error and "
            "often nearly coincide.",
            f"- The `{config.GROWTH}` growth beyond the backtest horizon is an assumption, not an estimate.",
            "- Series with zeros (hourly requests) use absolute errors from early, quieter folds, so their bands can "
            "be too narrow when volume is higher; the holdout check measures this.", ""]


def deviations(results, extras) -> list[str]:
    items = [
        "interval_check.csv has extra columns: `segment` (the hourly driver has rows for all steps and the two "
        "horizon splits), `model`, `n_folds_used` and Phase 2's coverage on the same holdout for comparison.",
        "The run-rate file also holds the point forecast's run-rate as sample_id -1; the extrapolation note is a "
        "companion file, burstgpt_monthly_run_rate_NOTE.md, so the CSV stays machine-readable.",
        "Units: WildChat conversations use the unit `conversations` (from the driver config), not `users`.",
        "`--fast` does not change any number: it only drops the thin sample paths from the fan charts.",
        "Ensemble members are clipped at 0 before averaging, as in Phase 2's scoring.",
        "The scenario table has an extra `kind` column (always `assumption`) so it can never be mixed up with forecasts.",
        "Validation results are also written to tables/validation.csv.",
        "Interval options: the pseudo-holdout uses each held-out fold's STORED Phase 2 forecast as the point forecast "
        "(no refit), so it is cheap and never reads data after the backtest; identical results keep the options off.",
        "interval_check.csv keeps coverage_80 / coverage_95 as the AFTER values and adds the before/after columns, "
        "miss counts and the data facts used for the causes; the tuning table is tables/interval_tuning.csv.",
        "The forecast files now use the chosen options, so drivers whose options changed have different paths "
        "from the first Phase 3 run.",
    ]
    if not any(r["manifest"]["errors_from"].startswith("rebuilt") for r in results):
        items.append("cv_residuals.parquet already held ensemble rows, so no ensemble errors had to be rebuilt.")
    return ["## 10. Deviations from the Phase 3 prompt", ""] + [f"- {i}" for i in items] + [""]
