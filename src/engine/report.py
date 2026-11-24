"""Phase 4 tables, the data contract and assumptions.json (every number read from the runs)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
import config_phase4 as P4
from tsaf.chosen import clean


def data_contract(phase3: Path, path: Path) -> None:
    """Phase 3 files Phase 4 reads: forecasts (from the manifest), scenario rows, inputs_for_phase4."""
    man = json.loads((phase3 / "manifest.json").read_text(encoding="utf-8"))
    rows = [{"driver": d["driver"], "unit": d["unit"], "grain": d["grain"], "horizon": d["horizon"],
             "paths": d["n_samples"], "model": d["model_used"], "file": d["file"]} for d in man["drivers"]]
    sc = pd.read_csv(phase3 / "forecasts" / "scenario_tables.csv")
    inp = json.loads((phase3 / "inputs_for_phase4.json").read_text(encoding="utf-8"))
    roles = "\n".join(f"| {r} | {s['driver']} | {s['file']} | {'yes' if s['required'] else 'no (optional)'} | "
                      f"{'found' if (phase3 / s['file']).exists() else 'MISSING'} |"
                      for r, s in config.ENGINE_DRIVERS.items())
    txt = ["# Phase 4 data contract", "", "## Phase 3 forecast files", "",
           _md_table(pd.DataFrame(rows)),
           "", "## Engine roles (src/config.py ENGINE_DRIVERS)", "",
           "| role | driver | file | required | status |", "|---|---|---|---|---|", roles, "",
           "## scenario_tables.csv (every row)", ""]
    txt += [f"- **{r.scenario}** / `{r.parameter}` = {r.value} {r.unit} (status {r.status}); source: {r.source}; "
            f"derivation: {r.derivation}" for r in sc.itertuples()]
    txt += ["", "## inputs_for_phase4.json", "", "```json", json.dumps(inp, indent=2), "```", ""]
    path.write_text("\n".join(txt), encoding="utf-8")


def _md_table(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(df.columns) + " |"
    return "\n".join([head, "|" + "---|" * len(df.columns)] + ["| " + " | ".join(map(str, r)) + " |"
                                                              for r in df.itertuples(index=False)])


def monthly_table(runs: dict) -> pd.DataFrame:
    frames = []
    for (sc, k), (res, summ) in runs.items():
        m = summ["monthly"].copy()
        m["type"] = m["line"].map(lambda ln: P4.LINE_TYPE.get(ln, "Total" if ln == "total_cost" else "Net"))
        frames.append(m.assign(scenario=sc, multiplier=k))
    df = pd.concat(frames, ignore_index=True)
    return df[["scenario", "multiplier", "month", "line", "type", "p10", "p50", "p90"]]


def totals_table(runs: dict) -> pd.DataFrame:
    rows = []
    for (sc, k), (_, s) in runs.items():
        row = {"scenario": sc, "multiplier": k}
        for key in ("total_cost", "total_value", "peak_investment", "cum_net_T"):
            row.update({f"{key}_{q}": s[key][q] for q in ("p10", "p50", "p90")})
        rows.append(row)
    return pd.DataFrame(rows)


def break_even_table(runs: dict) -> pd.DataFrame:
    return pd.DataFrame([{"scenario": sc, "multiplier": k, "prob_break_even_within_T": s["break_even"]["prob_within_T"],
                          "p10_month": s["break_even"]["p10"], "p50_month": s["break_even"]["p50"],
                          "p90_month": s["break_even"]["p90"], "share_no_break_even": s["break_even"]["share_none"],
                          "T": res.meta["T"]} for (sc, k), (res, s) in runs.items()])


def cost_breakdown(runs: dict) -> pd.DataFrame:
    rows = []
    for (sc, k), (_, s) in runs.items():
        tot = sum(s["line_totals_p50"].values())
        rows += [{"scenario": sc, "multiplier": k, "line": ln, "type": P4.LINE_TYPE[ln], "p50_total": v,
                  "p50_share_of_cost": v / tot if tot > 0 else np.nan} for ln, v in s["line_totals_p50"].items()]
    return pd.DataFrame(rows)


def extrapolation_table(res) -> pd.DataFrame:
    ex = res.meta["extrapolation"]
    rows = [{"role": r, "driver": d["driver"], "months_covered_by_forecast": d["covered"],
             "months_extrapolated": d["extrapolated"], "share_of_total_cost_in_extrapolated_months": d["share_of_total_cost"],
             "used_fallback": d["used_fallback"]} for r, d in ex["per_driver"].items()]
    rows.append({"role": "any", "driver": "any extrapolated driver", "months_covered_by_forecast": np.nan,
                 "months_extrapolated": np.nan, "share_of_total_cost_in_extrapolated_months": ex["share_any"],
                 "used_fallback": False})
    return pd.DataFrame(rows)


def draws_sample(res, n: int = P4.SAMPLE_DRAWS) -> pd.DataFrame:
    k = min(n, res.cum_net.shape[0])
    T = res.cum_net.shape[1]
    return pd.DataFrame({"draw": np.repeat(np.arange(k), T), "month": np.tile(np.arange(1, T + 1), k),
                         "cumulative_net": res.cum_net[:k].reshape(-1)})


def assumptions(raw: dict, inputs: dict, drivers, sc_info: dict, inputs_path: Path) -> dict:
    """Every input and parameter with value, unit, evidence type, source and note."""
    out = {"illustrative_example_company": any(isinstance(v, dict) and v.get("illustrative") for v in raw.values()),
           "inputs": {}, "forecast_drivers": {}, "scenarios": sc_info}
    for k, v in inputs.items():
        meta = raw.get(k, {}) if isinstance(raw.get(k), dict) else {}
        out["inputs"][k] = {"value": v, "unit": meta.get("unit", ""),
                            "evidence_type": "illustrative" if meta.get("illustrative") else "estimate",
                            "source": str(inputs_path.name), "note": meta.get("note", "")}
    for role, d in drivers.drivers.items():
        out["forecast_drivers"][role] = {"driver": d.name, "evidence_type": "estimate" if d.used_fallback else "forecast",
                                         "covered_months": d.covered_months, "extrapolated_months": d.extrapolated_months,
                                         "used_fallback": d.used_fallback, "note": d.note}
    return clean(out)


def write_tables(runs: dict, sens: pd.DataFrame | None, tables: Path) -> dict:
    t = {"monthly": monthly_table(runs), "totals": totals_table(runs), "break_even": break_even_table(runs),
         "breakdown": cost_breakdown(runs)}
    t["monthly"].to_csv(tables / "monthly_summary.csv", index=False)
    t["totals"].to_csv(tables / "totals_summary.csv", index=False)
    t["break_even"].to_csv(tables / "break_even_summary.csv", index=False)
    t["breakdown"].to_csv(tables / "cost_breakdown.csv", index=False)
    ref = runs.get(("expected", 1.0)) or next(iter(runs.values()))
    t["extrapolation"] = extrapolation_table(ref[0])
    t["extrapolation"].to_csv(tables / "extrapolation.csv", index=False)
    draws_sample(ref[0]).to_parquet(tables / "draws_sample.parquet", index=False)
    if sens is not None:
        sens.to_csv(tables / "sensitivity.csv", index=False)
        t["sensitivity"] = sens
    return t
