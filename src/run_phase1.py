"""Phase 1 runner: exploration and baseline forecasts for every driver.

Usage:  python src/run_phase1.py [--fast] [--drivers name1 name2] [--data-dir D] [--out-dir O]

One failing driver is logged and skipped; the others continue. Exit code 0 unless the
program itself crashes. Outputs go to outputs/phase1/ (see README "Phase 1").
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from tsaf import dependence, eda, plots, report  # noqa: E402
from tsaf.handoff import write_handoff  # noqa: E402
from tsaf.loaders import SkipDriver, read_table  # noqa: E402
from tsaf.pipeline import analyse_driver  # noqa: E402

log = logging.getLogger("phase1")
WINDOW = "BurstGPT days 0-86 (in_model_window == True, 87 days); dated sources use their full span"
DEVIATIONS = [
    "ECI and PPI were fetched with the unmodified download.py / prep_fred.py functions, pointed at "
    "this folder at run time (common.py hard-codes the nested folder). FRED stalls requests with "
    "download.py's custom User-Agent, so a browser-compatible one was set at run time; no file changed.",
    "Epoch is a manual download (no CSV in data/raw/epoch), so it is skipped; its config uses the real "
    "column name from prep_epoch.py and runs once the file exists.",
    "ECI uses the seasonally adjusted column as specified, so its seasonal strength is about 0; the "
    "D=1 chosen by the decision order is flagged as an over-differencing risk for Phase 2.",
    "WildChat (25 shards): partial weeks are treated as missing, because their totals are undercounts "
    "(two inside the series contain days with no data at all). No filling is allowed, so a gap inside "
    "the series skips the weekly drivers even though there are 62 complete weeks in total.",
    "wildchat_conversations_daily is added so WildChat is still covered. Its window is the longest run "
    "where both model families have data (like BurstGPT's in_model_window), and the file's last date "
    "is dropped because the shard download cuts it off.",
    "BurstGPT API and chat tokens are sums of the ChatGPT and GPT-4 columns of burstgpt_daily_wide "
    "(no column holds them directly); neither has zero days in the window.",
    "Anomaly screen: for drivers judged multiplicative the seasonal-naive residual is taken on the "
    "log scale (a ratio), consistent with the decomposition; the 3.5 threshold is not tuned.",
    "The hold-out is forecast in one go from the end of the pre-hold-out data (h = hold-out length).",
    "Hourly ACF/PACF follow nlags = min(40, n//3), so the 168-hour weekly lag is not on the plot; "
    "it is captured by MSTL instead.",
]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--drivers", nargs="+", help="only these driver names")
    p.add_argument("--fast", action="store_true", help="3 folds max, no cross-correlation, small plots")
    p.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=config.OUT_DIR)
    return p.parse_args(argv)


def setup(out: Path) -> tuple[Path, Path]:
    """Create output folders and configure logging to console and run.log."""
    tables, figs = out / "tables", out / "figures"
    for d in (tables, figs):
        d.mkdir(parents=True, exist_ok=True)
    for h in list(logging.root.handlers):
        logging.root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(out / "run.log", mode="w", encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    for h in (fh, sh):
        h.setFormatter(fmt)
        logging.root.addHandler(h)
    logging.root.setLevel(logging.INFO)
    for noisy in ("matplotlib", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return tables, figs


def run_drivers(args, figs: Path) -> tuple[list[dict], list[dict]]:
    """Analyse each selected driver; collect results and skip reasons."""
    cfgs = config.DRIVERS if not args.drivers else [config.driver_by_name(n) for n in args.drivers]
    results, skipped = [], []
    for cfg in cfgs:
        t0 = time.time()
        try:
            r = analyse_driver(cfg, config.CV_SETTINGS[cfg["grain"]], args.data_dir, figs,
                               args.fast, config.FAST_MAX_FOLDS if args.fast else None)
            results.append(r)
            log.info("%-34s OK   n=%-5d folds=%d best=%s (CV MASE %.3f) [%.1fs]", cfg["name"],
                     r["summary"]["n"], r["n_folds"], r["best"]["baseline"], r["best"]["cv_mase"],
                     time.time() - t0)
        except SkipDriver as exc:
            skipped.append({"name": cfg["name"], "reason": str(exc)})
            log.info("%-34s SKIPPED: %s", cfg["name"], exc)
        except Exception as exc:  # noqa: BLE001 - one driver must not stop the others
            skipped.append({"name": cfg["name"], "reason": f"error: {type(exc).__name__}: {exc}"})
            log.exception("%-34s FAILED: %s", cfg["name"], exc)
    return results, skipped


def trend_and_ccf(results: list[dict], args, tables: Path, figs: Path) -> pd.DataFrame | None:
    """Trend-method comparison on TREND_DRIVER and the requests/tokens cross-correlation."""
    by = {r["cfg"]["name"]: r for r in results}
    trend = None
    if config.TREND_DRIVER in by:
        r = by[config.TREND_DRIVER]
        trend, lines = eda.trend_methods(r["series"], r["cfg"]["season"])
        trend.to_csv(tables / "trend_methods.csv", index=False)
        plots.plot_trend_methods(lines, r["cfg"], figs / "trend_methods_burstgpt.png", args.fast)
    if args.fast:
        log.info("cross-correlation skipped (--fast)")
        return trend
    try:
        df = read_table(args.data_dir, config.CCF_FILE)
        if "in_model_window" in df:
            df = df[df["in_model_window"].astype(bool)]
        if {config.CCF_X, config.CCF_Y} <= set(df.columns):
            df = df.set_index("day_index").sort_index()
            cc = dependence.cross_correlation(df[config.CCF_X].diff(), df[config.CCF_Y].diff())
            cc.to_csv(tables / "cross_correlation.csv", index=False)
            plots.plot_ccf(cc, config.CCF_X, config.CCF_Y, figs / "ccf_burstgpt_requests_tokens.png")
            log.info("cross-correlation: max |r| %.2f at lag %d", cc["ccf"].abs().max(),
                     int(cc.loc[cc["ccf"].abs().idxmax(), "lag"]))
    except SkipDriver as exc:
        log.info("cross-correlation skipped: %s", exc)
    return trend


def write_tables(results: list[dict], tables: Path) -> tuple[pd.DataFrame, dict]:
    """All per-driver tables; returns the leaderboard and the day-77 check text."""
    def stack(key: str) -> pd.DataFrame:
        frames = [r[key].assign(driver=r["cfg"]["name"]) for r in results]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return df[["driver"] + [c for c in df.columns if c != "driver"]] if len(df) else df
    pd.DataFrame([{"driver": r["cfg"]["name"], "unit": r["cfg"]["unit"], **r["summary"]}
                  for r in results]).to_csv(tables / "summary_stats.csv", index=False)
    pd.DataFrame([{"driver": r["cfg"]["name"], **r["decomp"]} for r in results]).to_csv(
        tables / "decomposition.csv", index=False)
    pd.concat([r["stationarity"] for r in results], ignore_index=True).to_csv(
        tables / "stationarity.csv", index=False)
    day77 = check_day77(results)
    an = stack("anomalies")
    an["note"] = ""
    an = pd.concat([an, pd.DataFrame([{"driver": config.TREND_DRIVER, "time": 77,
                                        "robust_z": day77.get("z"),
                                        "note": f"day-77 check: {day77['status']}"}])],
                   ignore_index=True)
    an.to_csv(tables / "anomalies.csv", index=False)
    cv, ho = stack("cv"), stack("holdout")
    cv.to_csv(tables / "baseline_cv.csv", index=False)
    ho.to_csv(tables / "baseline_holdout.csv", index=False)
    stack("folds").to_csv(tables / "baseline_folds.csv", index=False)
    lb = pd.DataFrame([{"driver": r["cfg"]["name"], "best_baseline": r["best"]["baseline"],
                        "cv_mase": r["best"]["cv_mase"], "holdout_mase": r["best"]["holdout_mase"],
                        "seasonal_naive_cv_mase": r["snaive_cv_mase"], "n_folds": r["n_folds"]}
                       for r in results]).sort_values("cv_mase", kind="stable").reset_index(drop=True)
    lb.insert(0, "rank", range(1, len(lb) + 1))
    lb.to_csv(tables / "leaderboard_baselines.csv", index=False)
    return lb, day77


def check_day77(results: list[dict]) -> dict:
    """PASS if the anomaly screen flags day 77 of BurstGPT total tokens, else FAIL (never raised)."""
    r = next((r for r in results if r["cfg"]["name"] == config.TREND_DRIVER), None)
    if r is None:
        return {"status": "not run (driver not analysed)"}
    z = r["robust_z"].abs()
    if 77 not in z.index or pd.isna(z.loc[77]):
        return {"status": "FAIL (day 77 has no robust z-score)"}
    ok = 77 in set(r["anomalies"]["time"].tolist())
    log_scale = r["decomp"]["type"] == "multiplicative"
    stl = eda.stl_remainder_z(r["series"], r["cfg"]["season"], log_scale).abs()
    chk = {"z": float(z.loc[77]), "rank": int((z > z.loc[77]).sum()) + 1, "n": int(z.notna().sum()),
           "scale": "log" if log_scale else "raw", "threshold": eda.ANOMALY_Z,
           "n_flagged": len(r["anomalies"]),
           "top": [(int(t), float(v)) for t, v in z.sort_values(ascending=False).head(3).items()],
           "stl_z": float(stl.loc[77]), "stl_flagged": int((stl > eda.ANOMALY_Z).sum()),
           "n_stl": int(stl.notna().sum())}
    chk["stl_share"] = chk["stl_flagged"] / chk["n_stl"]
    detail = (f"|robust z| = {chk['z']:.2f} vs threshold {eda.ANOMALY_Z}, rank {chk['rank']} of "
              f"{chk['n']} days, {chk['scale']} scale")
    chk["status"] = f"PASS (day 77 flagged; {detail})" if ok else f"FAIL (day 77 not flagged; {detail})"
    (log.info if ok else log.warning)("day-77 anomaly check: %s", chk["status"])
    return chk


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    t0 = time.time()
    tables, figs = setup(args.out_dir)
    log.info("Phase 1 start (fast=%s) data=%s", args.fast, args.data_dir)
    report.write_data_contract(args.data_dir, args.out_dir / "data_contract.md")
    results, skipped = run_drivers(args, figs)
    if not results:
        log.error("no driver could be analysed; see reasons above")
        return 0
    trend = trend_and_ccf(results, args, tables, figs)
    lb, day77 = write_tables(results, tables)
    write_handoff(results, skipped, WINDOW, args.out_dir / "handoff.json")
    log.info("handoff.json written and schema-checked (%d drivers)", len(results))
    report.write_summary(args.out_dir / "PHASE1_SUMMARY.md", results, skipped, WINDOW, trend, lb,
                         day77, DEVIATIONS)
    log.info("\n%s", lb.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    log.info("done in %.1fs: %d analysed, %d skipped", time.time() - t0, len(results), len(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
