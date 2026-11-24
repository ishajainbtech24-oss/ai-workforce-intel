"""Builds PHASE3_SUMMARY.md from the run's results (no hard-coded numbers, no placeholders)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config
import config_phase3 as P3
from tsaf.report import fmt, md_table


def _pct(x) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.0%}"


def s1_drivers(results, failed) -> list[str]:
    out = ["## 1. Drivers simulated", ""]
    rows = [{"driver": m["driver"], "model used": m["model_used"], "family": m["family"],
             "fallback": "yes" if m["fallback_used"] else "no", "horizon": m["horizon"], "unit": m["unit"],
             "folds": m["n_folds_used"], "errors": "relative" if m["relative_errors"] else "absolute",
             "clipped": _pct(m["clipped_share"])} for m in (r["manifest"] for r in results)]
    out += [md_table(pd.DataFrame(rows)), ""]
    fb = [r["manifest"] for r in results if r["manifest"]["fallback_used"]]
    out.append("Fallbacks to seasonal naive: " + ("none of the drivers." if not fb else ", ".join(
        f"`{m['driver']}` ({'; '.join(m['warnings'])})" for m in fb)))
    few = [r["manifest"]["driver"] for r in results if r["manifest"]["few_folds"]]
    if few:
        out.append(f"Few folds (fewer than {P3.MIN_FOLDS} usable): {', '.join(few)}.")
    for f in failed:
        out.append(f"- FAILED `{f['driver']}`: {f['reason']}")
    out += ["", "Future inputs (known in advance, checked to have exactly h rows):", ""]
    out += [f"- `{r['manifest']['driver']}`: {r['manifest']['future_inputs']}" for r in results]
    return out + [""]


def s2_schema(results) -> list[str]:
    r = results[0]
    t = r["table"]
    ex = pd.concat([t[t["sample_id"] == -1].head(2), t[t["sample_id"] == 0].head(2), t[t["sample_id"] == 1].head(2)])
    ex = ex.assign(value=ex["value"].round(1))
    return ["## 2. The standard forecast table", "",
            "Every driver is written to `forecasts/<driver>.parquet` and `.csv` with exactly these columns, in this order:",
            "", "`" + ", ".join(P3.COLUMNS) + "`", "",
            f"`sample_id` -1 is the point forecast, 0 to {P3.N_SAMPLES - 1} are the simulated paths; `calendar_month` is "
            "empty for BurstGPT (no calendar dates). Six example rows from "
            f"`{r['manifest']['driver']}`:", "", md_table(ex.astype({"period_index": int, "sample_id": int})), ""]


def s3_rules() -> list[str]:
    return ["## 3. How the paths are made (residual bootstrap)", "",
            f"- {P3.N_SAMPLES} paths per driver. Each path draws ONE backtest fold at random (with replacement) and "
            "adds that fold's whole vector of out-of-sample errors (actual minus forecast) to the point forecast, "
            "so the way errors hang together across steps is kept.",
            "- Strictly positive series use relative errors: each fold's errors are divided by that fold's level "
            "(mean of the last season of values before its origin) and multiplied by the current level (mean of "
            "the last season of the window). Series with zeros use the absolute errors.",
            f"- Beyond the backtest horizon, step h reuses the drawn fold's last-step error times sqrt(h / H_cv) "
            f"(growth rule `{config.GROWTH}`, switch `GROWTH` in src/config.py).",
            "- Every path is clipped at 0. Seed = 42 + the driver's position in the sorted driver names "
            "(numpy default_rng), so reruns give identical files.",
            "- Optional, chosen per driver without the final holdout (section 4a): recency weights and level matching.",
            f"- Phase 4 sensitivity: `uncertainty_multiplier` is {P3.UNCERTAINTY_MULTIPLIER:g} in the saved files; "
            f"inputs_for_phase4.json recommends re-running Phase 4 with multipliers {list(P3.SENSITIVITY_MULTIPLIERS)} "
            "(path = point + m x (path - point), clipped at 0).", ""]


def s4_check(check: pd.DataFrame, extras: dict, data_dir) -> list[str]:
    from tsaf.diagnose_phase3 import miss_cause, wildchat_end_check
    c = check.copy()
    out = ["## 4. Honest check: simulated intervals on the Phase 2 holdout", "",
           "Each driver was refitted on the data before the Phase 2 holdout, its paths were simulated with the "
           "same rules (errors only from folds ending before the holdout), and we counted how many actual holdout "
           "values fall inside the simulated bands. *Before* = equal fold weights, all folds; *after* = the options "
           "chosen per driver in section 4a (never using this holdout). Phase 2's own empirical intervals on the "
           "same holdout are shown for comparison.", ""]
    cols = ["driver", "segment", "n_holdout_points", "coverage_80_before", "coverage_80_after", "coverage_95_before",
            "coverage_95_after", "mean_width_80_before", "mean_width_80_after", "phase2_coverage_80", "options"]
    t = c[[x for x in cols if x in c.columns]].copy()
    t["flag after"] = c["flag"].map({True: "yes", False: "no"})
    out += [md_table(t.rename(columns={"mean_width_80_before": "width_80_before", "mean_width_80_after": "width_80_after"})),
            "", "Width = mean width of the 80% band divided by the current level.", ""]
    allr = c[c["segment"] == "all"]
    good, bad = allr[~allr["flag"]]["driver"].tolist(), allr[allr["flag"]]["driver"].tolist()
    changed = allr[allr["options"] != "recency=off, level_match=off"]["driver"].tolist()
    out.append(f"Reading: after the change the bands pass both thresholds (80% coverage at least "
               f"{P3.COVERAGE_FLAG[0.8]:.0%}, 95% at least {P3.COVERAGE_FLAG[0.95]:.0%}) for {', '.join(good) or 'no driver'} "
               f"and are still too narrow for {', '.join(bad) or 'no driver'}. The options changed the simulation for "
               f"{', '.join(changed) or 'no driver'}; for the others the pseudo-holdout found no option closer to 80%.")
    wide = allr[(~allr["flag"]) & (allr["mean_width_80_relative_to_level"] > 1.0)]
    if len(wide):
        out.append("Calibrated is not the same as useful: for " + ", ".join(
            f"{r.driver} (80% band on average {r.mean_width_80_relative_to_level:.1f} x the current level)"
            for r in wide.itertuples()) + " the band is wider than the level itself, because early, quiet folds "
            "had large errors relative to their small level and the relative-error rule scales them up to today's level.")
    hr = c[c["segment"] != "all"]
    for d, g in hr.groupby("driver"):
        a, b = g.iloc[0], g.iloc[1]
        out.append(f"Hourly `{d}`: {a['segment']} coverage {_pct(a['coverage_80'])} (80%) / {_pct(a['coverage_95'])} "
                   f"(95%); {b['segment']} {_pct(b['coverage_80'])} / {_pct(b['coverage_95'])}.")
    out += ["", "### Why the remaining drivers miss", ""]
    out += [f"- `{r['driver']}`: {miss_cause(r)}" for _, r in allr[allr["flag"]].iterrows()]
    out += ["", f"- {wildchat_end_check(data_dir)}", ""]
    return out + s4a_tuning(extras.get("tuning"))


def s4a_tuning(tun) -> list[str]:
    out = ["### 4a. How the options were chosen (pseudo-holdout, never the final holdout)", "",
           "Two switchable options (src/config.py): **recency weights** (a fold's chance of being drawn halves every "
           f"{config.RECENCY_HALF_LIFE} x n_folds folds of age) and **level matching** (positive series only use folds "
           f"whose level is within {config.LEVEL_MATCH[0]:g}x-{config.LEVEL_MATCH[1]:g}x of the current level; if fewer "
           f"than {P3.LEVEL_MATCH_MIN_FOLDS} qualify, the closest {P3.LEVEL_MATCH_MIN_FOLDS}). For each driver the last "
           f"{P3.PSEUDO_SHARE:.0%} of the backtest folds (at least {P3.PSEUDO_MIN}) were held out and simulated from the "
           "earlier folds only, using each fold's stored out-of-sample forecast. The combination with 80% coverage "
           "closest to 0.8 was chosen (tie: the narrower band; identical results keep the options off).", ""]
    if tun is None or tun.empty:
        return out + ["No driver had enough folds for a pseudo-holdout.", ""]
    t = tun[["driver", "option", "n_heldout_folds", "n_points", "coverage_80", "coverage_95",
             "mean_width_80_relative_to_level", "chosen"]].copy()
    t["chosen"] = t["chosen"].map({True: "**chosen**", False: ""})
    same = [d for d, g in tun.groupby("driver", sort=False)
            if g[["coverage_80", "coverage_95", "mean_width_80_relative_to_level"]].round(9).nunique().max() == 1]
    out += [md_table(t.rename(columns={"mean_width_80_relative_to_level": "width_80"})), ""]
    if same:
        out.append(f"For {', '.join(same)} all four combinations give the same result: with so few training folds "
                   "the bands are the smallest and largest fold error either way, and every fold level was within the "
                   "matching band (or there were fewer folds than the matching minimum).")
    return out + [""]


def s5_run_rate(extras) -> list[str]:
    out = ["## 5. BurstGPT 30-day token run-rate", ""]
    s = extras.get("run_rate_summary")
    if s is None:
        return out + ["Not produced (no BurstGPT daily token driver in this run).", ""]
    t = s[["driver", "p10", "p50", "p90", "point_forecast"]].copy()
    for c in ("p10", "p50", "p90", "point_forecast"):
        t[c] = (t[c] / 1e6).round(1)
    return out + ["Values in million tokens per 30 days.", "", md_table(t.rename(columns={
        c: f"{c} (M tokens)" for c in ("p10", "p50", "p90", "point_forecast")})), "",
        f"**Warning: only {P3.RUN_RATE['forecast_days']} days are forecast; the last "
        f"{P3.RUN_RATE['days'] - P3.RUN_RATE['forecast_days']} days are extrapolated** "
        f"({P3.RUN_RATE['days'] - P3.RUN_RATE['forecast_days']} x the mean of the last {P3.RUN_RATE['tail_days']} "
        "simulated days of the same path).", *_skew_note(s), ""]


def _skew_note(s: pd.DataFrame) -> list[str]:
    """Explain a run-rate median far from the point forecast (skewed relative errors)."""
    far = s[(s["p50"] > 1.5 * s["point_forecast"]) | (s["p50"] < s["point_forecast"] / 1.5)]
    if far.empty:
        return []
    return ["", "For " + ", ".join(f"{r.driver} (P50 {r.p50 / r.point_forecast:.1f} x the point forecast)"
                                   for r in far.itertuples())
            + " the median path is far from the point forecast: the resampled relative errors are strongly skewed "
            "(see the wide bands in section 4), so these run-rate ranges should be read as very uncertain."]


def s6_scenarios(extras) -> list[str]:
    sc = extras["scenarios"]
    out = ["## 6. Scenario inputs (assumptions, not forecasts)", ""]
    if sc.empty:
        return out + ["No scenario rows could be built."] + [f"- {n}" for n in extras["scenario_notes"]] + [""]
    out += [md_table(sc[["scenario", "parameter", "value", "unit", "status", "source"]]), "", "Derivations:", ""]
    out += [f"- {r.scenario} / {r.parameter}: {r.derivation}" for r in sc.itertuples()]
    nr = sc[sc["status"] == "needs_review"]
    out += ["", f"Rows needing review: {len(nr)}." + (" " + ", ".join(nr["parameter"]) if len(nr) else
            " Every column's meaning is documented in the preprocessing code (prep_fred.py, download.py)."),
            "Note: the downside rows (METR) measure the change in task completion time for experienced developers, "
            "while the expected and optimistic rows are time saved as a share of all work hours; Phase 4 must "
            "convert them to a common unit."]
    out += [f"- {n}" for n in extras["scenario_notes"]]
    return out + [""]


def s7_tokens(inputs) -> list[str]:
    v = inputs.get("input_token_share")
    txt = (f"Input (request) tokens are {_pct(v)} of all tokens in {inputs['window']} ({inputs['input_token_note']}); "
           f"API traffic is {_pct(inputs.get('api_token_share'))} and chat {_pct(inputs.get('chat_token_share'))} of "
           "total tokens." if v is not None else f"Input-token share not measurable: {inputs.get('input_token_note')}.")
    return ["## 7. Input-token share (for Phase 4)", "", txt, ""]


def write_summary(path: Path, results, failed, extras, manifest, inputs, validation, args) -> None:
    from tsaf.summary_phase3_text import deviations, limitations, review
    v = validation
    fails = v[v["status"] == "FAIL"]
    val = ["## Validation", "", md_table(v.assign(problems=v["problems"].replace("", "-"))), "",
           "All files PASS." if fails.empty else f"**{len(fails)} file(s) FAIL**: see the table above."]
    parts = (["# Phase 3 summary: standard forecast tables", "",
              f"Generated by `python src/run_phase3.py{' --fast' if args.fast else ''}`; every number comes from this run.", ""]
             + s1_drivers(results, failed) + s2_schema(results) + s3_rules() + s4_check(extras["check"], extras, args.data_dir)
             + s5_run_rate(extras) + s6_scenarios(extras) + s7_tokens(inputs)
             + review(results, extras, inputs) + limitations(results) + deviations(results, extras) + val)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
