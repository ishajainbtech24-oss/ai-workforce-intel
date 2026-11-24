"""Phase 3 runner: standard forecast tables with 200 simulated paths per driver.

Usage:  python src/run_phase3.py [--fast] [--drivers a b] [--data-dir D] [--phase1-dir P1]
                                 [--phase2-dir P2] [--out-dir O] [--quality-log Q]

Reads outputs/phase2/chosen_models.json (model + fixed parameters), cv_residuals.parquet
(backtest errors) and the Phase 1 handoff; refits each chosen model on the full window,
simulates paths by residual bootstrap, checks the method on the Phase 2 holdout, and writes
outputs/phase3/ (see README "Phase 3"). --fast only skips the thin sample paths on the fan
charts and draws smaller figures; the numbers are identical. A failing driver is logged and
skipped; the exit code is 0 unless the program itself crashes.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import config_phase3 as P3  # noqa: E402
from run_phase1 import setup  # noqa: E402
from tsaf import export, plots_phase3, scenarios, validate  # noqa: E402
from tsaf.chosen import clean  # noqa: E402
from tsaf.models.registry import build_registry, by_name  # noqa: E402
from tsaf.pipeline_phase3 import Phase2Inputs, process_driver  # noqa: E402

log = logging.getLogger("phase3")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fast", action="store_true", help="smaller figures without thin paths (same numbers)")
    p.add_argument("--drivers", nargs="+", help="only these drivers (from chosen_models.json)")
    p.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    p.add_argument("--phase1-dir", type=Path, default=P3.PHASE1_DIR)
    p.add_argument("--phase2-dir", type=Path, default=P3.PHASE2_DIR)
    p.add_argument("--out-dir", type=Path, default=P3.OUT_DIR)
    p.add_argument("--quality-log", type=Path, default=P3.QUALITY_LOG)
    return p.parse_args(argv)


def _optional_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def load_inputs(args) -> Phase2Inputs:
    """Read chosen_models.json, the handoff, cv_residuals and (if present) folds, leaderboard, holdout."""
    doc = json.loads((args.phase2_dir / "chosen_models.json").read_text(encoding="utf-8"))
    hand = json.loads((args.phase1_dir / "handoff.json").read_text(encoding="utf-8"))
    chosen = [d for d in doc["drivers"] if not args.drivers or d["name"] in set(args.drivers)]
    t = args.phase2_dir / "tables"
    return Phase2Inputs(chosen=chosen, handoff={d["name"]: d for d in hand["drivers"]},
                        residuals=pd.read_parquet(t / "cv_residuals.parquet"),
                        folds=_optional_csv(t / "cv_folds.csv"), leaderboard=_optional_csv(t / "leaderboard.csv"),
                        holdout=_optional_csv(t / "holdout.csv"))


def run_drivers(inp: Phase2Inputs, args, figs: Path) -> tuple[list[dict], list[dict]]:
    specs = by_name(build_registry())
    names = [c["name"] for c in inp.chosen]
    results, failed = [], []
    for chosen in inp.chosen:
        t0 = time.time()
        try:
            r = process_driver(chosen, inp, names, args.data_dir, args.out_dir, specs)
            results.append(r)
            m = r["manifest"]
            log.info("%-30s %-16s folds=%-3d relative=%-5s cover80=%.2f cover95=%.2f%s [%.1fs]", m["driver"],
                     m["model_used"], m["n_folds_used"], m["relative_errors"], m["coverage_80_holdout"],
                     m["coverage_95_holdout"], " FALLBACK" if m["fallback_used"] else "", time.time() - t0)
        except Exception as exc:  # noqa: BLE001 - one driver must not stop the others
            failed.append({"driver": chosen["name"], "reason": f"{type(exc).__name__}: {exc}"})
            log.exception("%s FAILED", chosen["name"])
    return results, failed


def fan_figures(results: list[dict], check: pd.DataFrame, figs: Path, fast: bool) -> None:
    for r in results:
        d = r["manifest"]["driver"]
        c = check[(check["driver"] == d) & (check["segment"] == "all")]
        txt = (f"holdout check: {c['coverage_80'].iloc[0]:.0%} of actual values inside the 80% band, "
               f"{c['coverage_95'].iloc[0]:.0%} inside the 95% band" if len(c) else "holdout check not available")
        try:
            plots_phase3.plot_fan(r, txt, figs / f"fan_{d}.png", thin=0 if fast else P3.FAN_THIN_PATHS)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fan chart failed: %s", d, exc)


def write_extras(results: list[dict], args, tables: Path, figs: Path) -> dict:
    """Run-rate, scenarios, interval check table and figures; returns them for the summary."""
    out: dict = {}
    fc_dir = args.out_dir / "forecasts"
    rr = [export.run_rate(r["paths"], r["point"], r["manifest"]["driver"]) for r in results
          if r["manifest"]["driver"] in P3.RUN_RATE_DRIVERS]
    if rr:
        out["run_rate"] = pd.concat(rr, ignore_index=True)
        out["run_rate"].to_csv(fc_dir / "burstgpt_monthly_run_rate.csv", index=False)
        out["run_rate_summary"] = export.run_rate_summary(out["run_rate"])
        out["run_rate_summary"].to_csv(fc_dir / "burstgpt_monthly_run_rate_summary.csv", index=False)
        (fc_dir / "burstgpt_monthly_run_rate_NOTE.md").write_text(
            "run_rate_30d = sum of the 14 simulated days + 16 x the mean of the last 7 simulated days of the "
            "same path. The last 16 days are EXTRAPOLATED, not forecast (extrapolated = True on every row). "
            "sample_id -1 is the point forecast; summary percentiles use the 200 paths only.\n", encoding="utf-8")
        plots_phase3.plot_run_rate(out["run_rate"], out["run_rate_summary"], figs / "run_rate_burstgpt.png")
    sc, notes = scenarios.build_scenarios(args.data_dir, args.quality_log)
    out["scenarios"], out["scenario_notes"] = sc, notes
    if len(sc):
        sc.to_csv(fc_dir / "scenario_tables.csv", index=False)
        plots_phase3.plot_scenarios(sc, figs / "scenarios.png")
    check = pd.DataFrame([row for r in results for row in r["check"]])
    first = ["driver", "n_holdout_points", "coverage_80", "coverage_95", "mean_width_80_relative_to_level", "flag"]
    check = check[first + [c for c in check.columns if c not in first]]
    check.to_csv(tables / "interval_check.csv", index=False)
    tun = [r["tuning"] for r in results if len(r["tuning"])]
    out["tuning"] = pd.concat(tun, ignore_index=True) if tun else pd.DataFrame()
    out["tuning"].to_csv(tables / "interval_tuning.csv", index=False)
    plots_phase3.plot_interval_check(check, figs / "interval_check.png")
    out["check"] = check
    return out


def write_jsons(results: list[dict], failed: list[dict], args) -> tuple[dict, dict]:
    manifest = {"phase": 3, "n_samples": P3.N_SAMPLES, "growth_rule": config.GROWTH,
                "uncertainty_multiplier": P3.UNCERTAINTY_MULTIPLIER,
                "interval_options": {"recency_half_life": config.RECENCY_HALF_LIFE, "level_match": config.LEVEL_MATCH,
                                     "chosen_by": "pseudo-holdout on the last backtest folds (tables/interval_tuning.csv)"},
                "drivers": [r["manifest"] for r in results], "failed": failed}
    (args.out_dir / "manifest.json").write_text(json.dumps(clean(manifest), indent=2), encoding="utf-8")
    shares = scenarios.token_shares(args.data_dir)
    inputs = {"phase": 3, "note": "Measured inputs for Phase 4; no cost calculations here.", **shares,
              "forecast_files": [{"driver": r["manifest"]["driver"], "file": r["manifest"]["file"],
                                  "unit": r["manifest"]["unit"], "grain": P3.GRAIN_NAME[r["manifest"]["grain"]],
                                  "horizon": r["manifest"]["horizon"]} for r in results],
              "scenario_file": "forecasts/scenario_tables.csv",
              "uncertainty_multiplier": P3.UNCERTAINTY_MULTIPLIER,
              "uncertainty_sensitivity": {
                  "multipliers": list(P3.SENSITIVITY_MULTIPLIERS),
                  "how": "path_m = point + m x (path - point), then clip at 0; sample_id -1 is the point. "
                         "The saved forecast files are NOT scaled (m = 1.0).",
                  "why": "the holdout check shows bands that are still too narrow for several drivers"}}
    (args.out_dir / "inputs_for_phase4.json").write_text(json.dumps(clean(inputs), indent=2), encoding="utf-8")
    return clean(manifest), clean(inputs)


def run_validation(results: list[dict], extras: dict, args, tables: Path) -> pd.DataFrame:
    rows = []
    for r in results:
        m = r["manifest"]
        df = pd.read_parquet(args.out_dir / m["file"])
        rows.append(validate.result_row(Path(m["file"]).name, validate.check_forecast_table(df, m["horizon"])))
    sc_path = args.out_dir / "forecasts" / "scenario_tables.csv"
    rows.append(validate.result_row("scenario_tables.csv", validate.check_scenarios(pd.read_csv(sc_path))
                                    if sc_path.exists() else ["file not written"]))
    v = pd.DataFrame(rows)
    v.to_csv(tables / "validation.csv", index=False)
    log.info("validation:\n%s", v.to_string(index=False))
    return v


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    t0 = time.time()
    tables, figs = setup(args.out_dir)
    log.info("Phase 3 start (fast=%s, growth=%s, %d samples)", args.fast, config.GROWTH, P3.N_SAMPLES)
    inp = load_inputs(args)
    results, failed = run_drivers(inp, args, figs)
    if not results:
        log.error("no driver could be simulated")
        return 0
    extras = write_extras(results, args, tables, figs)
    fan_figures(results, extras["check"], figs, args.fast)
    manifest, inputs = write_jsons(results, failed, args)
    v = run_validation(results, extras, args, tables)
    from tsaf.summary_phase3 import write_summary
    write_summary(args.out_dir / "PHASE3_SUMMARY.md", results, failed, extras, manifest, inputs, v, args)
    log.info("done in %.1fs: %d simulated, %d failed, validation %d PASS / %d FAIL", time.time() - t0,
             len(results), len(failed), int((v["status"] == "PASS").sum()), int((v["status"] == "FAIL").sum()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
