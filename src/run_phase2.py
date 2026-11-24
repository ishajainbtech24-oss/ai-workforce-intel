"""Phase 2 runner: forecasting models compared by rolling-origin backtesting.

Usage:  python src/run_phase2.py [--fast] [--with-lstm] [--drivers a b] [--data-dir D]
                                 [--out-dir O] [--handoff outputs/phase1/handoff.json]

Reads the drivers and their decisions (season, d, D, decomposition, CV settings) from the
Phase 1 handoff, runs every registered model through the same folds and hold-out, chooses a
model per driver, checks its residuals, and writes outputs/phase2/ (see README "Phase 2").
A failing model or driver is logged and recorded; the exit code is 0 unless the program crashes.
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
import config_phase2 as P2  # noqa: E402
from run_phase1 import setup  # noqa: E402
from tsaf import chosen as chosen_mod  # noqa: E402
from tsaf import diagnostics, evaluate, plots_phase2, report_phase2  # noqa: E402
from tsaf.loaders import SkipDriver  # noqa: E402
from tsaf.models.registry import build_registry, by_name  # noqa: E402
from tsaf.pipeline_phase2 import model_driver  # noqa: E402

log = logging.getLogger("phase2")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fast", action="store_true",
                   help="3 folds, 8 ARIMA candidates, 100 trees, no hourly SARIMAX, no Prophet/LSTM")
    p.add_argument("--with-lstm", action="store_true", help="also run the LSTM challenger (needs torch)")
    p.add_argument("--drivers", nargs="+", help="only these driver names (from the handoff)")
    p.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=P2.OUT_DIR)
    p.add_argument("--handoff", type=Path, default=P2.HANDOFF)
    return p.parse_args(argv)


def driver_entries(args) -> tuple[list[dict], list[dict]]:
    """Drivers to model (from handoff.json) and the drivers Phase 1 already skipped."""
    doc = json.loads(Path(args.handoff).read_text(encoding="utf-8"))
    entries = doc["drivers"]
    if args.drivers:
        entries = [e for e in entries if e["name"] in set(args.drivers)]
    skipped = [{"name": s["name"], "reason": f"skipped in Phase 1: {s['reason']}"} for s in doc.get("skipped", [])]
    return entries, skipped


def chosen_row(dr: dict) -> dict:
    """chosen_models.csv row: rule applied, scores and whether it beat seasonal naive."""
    b = dr["board"].set_index("model")
    name = dr["chosen"]
    sn = float(b.loc["seasonal_naive", "cv_mase"]) if "seasonal_naive" in b.index else np.nan
    cv = float(b.loc[name, "cv_mase"])
    return {"driver": dr["entry"]["name"], "chosen_model": name, "family": b.loc[name, "family"],
            "why": dr["why"], "cv_mase": cv, "holdout_mase": float(b.loc[name, "holdout_mase"]),
            "seasonal_naive_cv_mase": sn,
            "beats_seasonal_naive": bool(name != "seasonal_naive" and np.isfinite(sn) and cv < sn)}


def diagnose(dr: dict, specs: dict) -> dict:
    """Residual checks (pre-hold-out fit) and anomalies (full-window fit) for the chosen model."""
    name, ctx, e = dr["chosen"], dr["ctx"], dr["entry"]
    out = {"driver": e["name"], "model": name, "anomalies": pd.DataFrame(), "day77": None, "table": None}
    ins, table = diagnostics.insample(name, specs, dr["results"], dr["pre"], ctx)
    out["resid"] = dr["pre"] - ins
    out["stats"] = {"driver": e["name"], "model": name, **diagnostics.residual_stats(out["resid"], e["season"])}
    out["table"] = table
    ins_full, _ = diagnostics.insample(name, specs, dr["results"], dr["series"], ctx)
    resid_full = dr["series"] - ins_full
    out["anomalies"] = diagnostics.anomalies(resid_full, dr["series"], e["name"], name)
    if e["name"] == P2.DAY77["driver"]:
        out["day77"] = diagnostics.day77_check(resid_full, name)
    return out


def figures(dr: dict, diag: dict | None, figs: Path) -> None:
    """The four figures of one driver (each wrapped so a plotting error is only logged)."""
    e, name = dr["entry"], dr["chosen"]
    cfg = {**config.driver_by_name(e["name"]), **e}
    res, folds = dr["results"], dr["folds"].get(name)
    hw = (evaluate.holdout_halfwidths(folds, len(dr["test"]))
          if folds is not None and dr["n_folds"] >= P2.MIN_FOLDS_FOR_INTERVALS else None)
    sn = res["seasonal_naive"].holdout_fc if res["seasonal_naive"].status == "ok" else None
    jobs = [("leaderboard", lambda p: plots_phase2.plot_leaderboard(dr["board"], name, e["name"], p)),
            ("forecast", lambda p: plots_phase2.plot_forecast(dr["pre"], dr["test"], res[name].holdout_fc,
                                                              sn, hw, cfg, name, p)),
            ("cv_folds", lambda p: plots_phase2.plot_cv_folds(dr["pre"], folds, cfg, name, p))]
    if diag is not None and "resid" in diag:
        jobs.append(("residuals", lambda p: plots_phase2.plot_residuals(diag["resid"], cfg, name, p)))
    for kind, job in jobs:
        try:
            job(figs / f"{kind}_{e['name']}.png")
        except Exception as exc:  # noqa: BLE001 - a figure must never stop the run
            log.warning("%s: figure %s failed: %s", e["name"], kind, exc)


def run_all(entries: list[dict], args, figs: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Model, diagnose and plot each driver; returns results, diagnostics and skipped drivers."""
    specs = build_registry()
    sb = by_name(specs)
    results, diags, skipped = [], [], []
    for e in entries:
        t0 = time.time()
        log.info("driver %s (%s, season %s, d=%s, D=%s)", e["name"], e["grain"], e["season"], e["d"], e["D"])
        try:
            dr = model_driver(e, specs, args, args.data_dir)
        except SkipDriver as exc:
            skipped.append({"name": e["name"], "reason": str(exc)})
            log.info("%s SKIPPED: %s", e["name"], exc)
            continue
        except Exception as exc:  # noqa: BLE001 - one driver must not stop the others
            skipped.append({"name": e["name"], "reason": f"error: {type(exc).__name__}: {exc}"})
            log.exception("%s FAILED", e["name"])
            continue
        try:
            diag = diagnose(dr, sb)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: diagnostics failed: %s", e["name"], exc)
            diag = {"driver": e["name"], "model": dr["chosen"], "anomalies": pd.DataFrame(),
                    "day77": None, "table": None, "stats": {"driver": e["name"], "model": dr["chosen"],
                                                            "error": str(exc)}}
        figures(dr, diag, figs)
        results.append(dr)
        diags.append(diag)
        log.info("driver %s done: chosen %s (%s) [%.1fs]", e["name"], dr["chosen"], dr["why"], time.time() - t0)
    return results, diags, skipped


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    t0 = time.time()
    tables, figs = setup(args.out_dir)
    log.info("Phase 2 start (fast=%s, with_lstm=%s) handoff=%s", args.fast, args.with_lstm, args.handoff)
    entries, skipped = driver_entries(args)
    log.info("drivers from handoff: %s", ", ".join(e["name"] for e in entries))
    results, diags, skipped_now = run_all(entries, args, figs)
    skipped += skipped_now
    if not results:
        log.error("no driver could be modelled; see reasons above")
        return 0
    chosen_rows = [chosen_row(dr) for dr in results]
    report_phase2.write_tables(results, diags, chosen_rows, tables)
    doc = chosen_mod.write([chosen_mod.make_entry(dr, cr) for dr, cr in zip(results, chosen_rows)],
                           skipped, args.out_dir / "chosen_models.json")
    log.info("chosen_models.json written and schema-checked (%d drivers)", len(doc["drivers"]))
    report_phase2.write_summary(args.out_dir / "PHASE2_SUMMARY.md", results, diags, chosen_rows,
                                skipped, args)
    log.info("\n%s", pd.DataFrame(chosen_rows)[["driver", "chosen_model", "cv_mase", "holdout_mase",
                                                 "beats_seasonal_naive"]].to_string(index=False))
    log.info("done in %.1fs: %d modelled, %d skipped", time.time() - t0, len(results), len(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
