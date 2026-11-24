"""Phase 4 runner: Monte Carlo cost-and-value engine for the example company (or --inputs file).

Usage:  python src/run_phase4.py [--fast] [--inputs config/example_company.json] [--horizon N]
                                 [--data-dir D] [--phase3-dir P3] [--out-dir O]

Runs every valid scenario (downside, expected, optimistic) at the uncertainty multipliers from
outputs/phase3/inputs_for_phase4.json (1.0, 1.5, 2.0), plus a tornado sensitivity on the expected
scenario at k = 1, and writes outputs/phase4/. --fast: 1,000 draws, no tornado chart.
A failed scenario is logged and the others continue; exit code 0 unless the program crashes.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import config_phase4 as P4  # noqa: E402
from engine import plots, report, sensitivity  # noqa: E402
from engine.drivers import MissingDriver, load_drivers  # noqa: E402
from engine.inputs import InputError, is_illustrative, load_inputs  # noqa: E402
from engine.simulate import ScenarioSkipped, run_engine, scenario_fraction, summarise  # noqa: E402
from engine.summary import write_summary  # noqa: E402
from engine.summary_text import sanity_checks  # noqa: E402
from run_phase1 import setup  # noqa: E402

log = logging.getLogger("phase4")


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fast", action="store_true", help="1,000 draws, no tornado chart")
    p.add_argument("--inputs", type=Path, default=P4.EXAMPLE_INPUTS)
    p.add_argument("--horizon", type=int, help="engine horizon T in months (6 to 24)")
    p.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    p.add_argument("--phase3-dir", type=Path, default=P4.PHASE3_DIR)
    p.add_argument("--out-dir", type=Path, default=P4.OUT_DIR)
    return p.parse_args(argv)


def check_roles(phase3: Path) -> None:
    """Every required engine role must point at a driver in the Phase 3 manifest and an existing file."""
    man = {d["driver"] for d in json.loads((phase3 / "manifest.json").read_text(encoding="utf-8"))["drivers"]}
    for role, spec in config.ENGINE_DRIVERS.items():
        found = (phase3 / spec["file"]).exists() and (spec["driver"] in man or spec["file"].endswith(".csv"))
        if spec["required"] and not found:
            raise MissingDriver(f"required engine role '{role}' needs {spec['file']} ({spec['driver']}); not found")
        log.info("engine role %-12s -> %-30s %s", role, spec["driver"], "found" if found else
                 "MISSING (optional, fallback used)")


def run_grid(inputs, drivers, sc_table, mults, n, seed) -> tuple[dict, list[str], dict]:
    runs, skipped, sc_info = {}, [], {}
    for sc in P4.SCENARIOS:
        try:
            frac, info = scenario_fraction(sc_table, sc, inputs)
            sc_info[sc] = {**info, "time_saved_fraction": frac}
        except ScenarioSkipped as exc:
            skipped.append(str(exc))
            log.warning("%s", exc)
            continue
        for k in mults:
            t0 = time.time()
            try:
                res = run_engine(inputs, sc, k, n, seed, drivers, sc_table)
                runs[(sc, float(k))] = (res, summarise(res))
                b = runs[(sc, float(k))][1]["break_even"]
                log.info("run %-10s k=%.1f  P(break-even)=%.2f  [%.2fs]", sc, k, b["prob_within_T"], time.time() - t0)
            except Exception as exc:  # noqa: BLE001 - one failed run must not stop the others
                skipped.append(f"{sc} k={k}: {type(exc).__name__}: {exc}")
                log.exception("run %s k=%s failed", sc, k)
    return runs, skipped, sc_info


def figures(runs, sens, tag, figs, fast) -> None:
    jobs = []
    for sc in P4.SCENARIOS:
        if (sc, 1.0) in runs:
            res = runs[(sc, 1.0)][0]
            jobs += [(f"cost_stack_{sc}", lambda r=res, s=sc: plots.cost_stack(r, s, tag, figs / f"cost_stack_{s}.png")),
                     (f"cumulative_net_{sc}", lambda r=res, s=sc: plots.cumulative_net(r, s, tag, figs / f"cumulative_net_{s}.png")),
                     (f"break_even_hist_{sc}", lambda r=res, s=sc: plots.break_even_hist(r, s, tag, figs / f"break_even_hist_{s}.png"))]
    jobs.append(("scenario_compare", lambda: plots.scenario_compare(
        {sc: r for (sc, k), (r, _) in runs.items() if k == 1.0}, tag, figs / "scenario_compare.png")))
    jobs.append(("multiplier_effect", lambda: plots.multiplier_effect(
        {k: s for (sc, k), (_, s) in runs.items() if sc == "expected"}, "expected", tag, figs / "multiplier_effect.png",
        T=next(iter(runs.values()))[0].meta["T"])))
    ref = runs.get(("expected", 1.0)) or next(iter(runs.values()))
    tot = sum(ref[1]["line_totals_p50"].values())
    by_type = {}
    for ln, v in ref[1]["line_totals_p50"].items():
        by_type[P4.LINE_TYPE[ln]] = by_type.get(P4.LINE_TYPE[ln], 0.0) + v / tot
    jobs.append(("cost_share_by_type", lambda: plots.cost_share_by_type(by_type, tag, figs / "cost_share_by_type.png")))
    if sens is not None and not fast:
        jobs.append(("tornado", lambda: plots.tornado(sens, tag, figs / "tornado.png")))
    for name, job in jobs:
        try:
            job()
        except Exception as exc:  # noqa: BLE001
            log.warning("figure %s failed: %s", name, exc)


def main(argv=None) -> int:
    args = parse_args(argv)
    t0 = time.time()
    tables, figs = setup(args.out_dir)
    try:
        overrides = {"horizon_months": args.horizon} if args.horizon else None
        inputs, raw = load_inputs(args.inputs, overrides)
        check_roles(args.phase3_dir)
        report.data_contract(args.phase3_dir, args.out_dir / "data_contract.md")
        drivers = load_drivers(int(inputs["horizon_months"]), args.phase3_dir, args.data_dir)
    except (InputError, MissingDriver, FileNotFoundError) as exc:
        log.error("Phase 4 cannot start: %s", exc)
        return 1
    p4in = json.loads((args.phase3_dir / "inputs_for_phase4.json").read_text(encoding="utf-8"))
    mults = p4in.get("uncertainty_sensitivity", {}).get("multipliers", list(P4.MULTIPLIERS_DEFAULT))
    sc_table = pd.read_csv(args.phase3_dir / "forecasts" / "scenario_tables.csv")
    n = P4.N_DRAWS_FAST if args.fast else P4.N_DRAWS
    illustrative = is_illustrative(raw)
    tag = "illustrative example company" if illustrative else "company inputs"
    log.info("Phase 4 start: T=%d, %d draws, multipliers %s, %s", inputs["horizon_months"], n, mults, tag)
    runs, skipped, sc_info = run_grid(inputs, drivers, sc_table, mults, n, P4.SEED)
    if not runs:
        log.error("no scenario could be run")
        return 0
    sens = None
    if "expected" in sc_info:
        t1 = time.time()
        sens = sensitivity.tornado(inputs, drivers, sc_table, "expected", 1.0, n, P4.SEED)
        log.info("sensitivity: %d inputs [%.1fs]", len(sens), time.time() - t1)
    t = report.write_tables(runs, sens, tables)
    figures(runs, sens, tag, figs, args.fast)
    asum = report.assumptions(raw, inputs, drivers, sc_info, args.inputs)
    (args.out_dir / "assumptions.json").write_text(json.dumps(asum, indent=2), encoding="utf-8")
    ctx = {"fast": args.fast, "illustrative": illustrative, "n_draws": n, "seed": P4.SEED, "assumptions": asum,
           "fallbacks": [r for r, d in drivers.drivers.items() if d.used_fallback], "skipped": skipped,
           "sanity": sanity_checks(runs), "input_token_share": p4in.get("input_token_share")}
    write_summary(args.out_dir / "PHASE4_SUMMARY.md", ctx, t)
    for c in ctx["sanity"]:
        log.info("sanity %-4s %s (%s)", "PASS" if c["passed"] else "FAIL", c["check"], c["detail"])
    log.info("done in %.1fs: %d runs, %d skipped", time.time() - t0, len(runs), len(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
