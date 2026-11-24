"""Data layer: cached loaders for outputs/phase3 and phase4 and the live engine calls.

Every number on screen comes from here: the saved Phase 4 tables, or `engine.simulate.run_engine`. After a visitor
presses Update on Try your own numbers with figures of their own, `table()` answers from THEIR results (the same
tables, built by the same engine functions) until they press Reset or refresh the page: the results live in this
browser session only (`st.session_state`), never on disk.
A missing file raises `Missing`, which pages turn into a friendly message. The project root can be
redirected with the environment variable TSAF_DASH_ROOT (used by the tests).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
N_LIVE, N_SAVED, SEED = 2000, 5000, 42
YOURS_KEY = "co_tables"  # session key of the visitor's own results


def yours() -> dict | None:
    """The visitor's own results ({'tables', 'payback', 'inputs'}), or None while the example company shows."""
    try:
        return st.session_state.get(YOURS_KEY)
    except Exception:  # noqa: BLE001 - outside a Streamlit run there is no session
        return None


def clear_yours() -> None:
    """Back to the example company everywhere: drops the visitor's results and the form's values."""
    for key in [k for k in st.session_state if str(k).startswith("co_")]:
        del st.session_state[key]


class Missing(RuntimeError):
    """A result file the dashboard needs is not there."""


def root() -> Path:
    return Path(os.environ.get("TSAF_DASH_ROOT", DEFAULT_ROOT))


@st.cache_data(show_spinner=False)
def _csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def table(name: str) -> pd.DataFrame:
    """outputs/phase4/tables/<name>.csv (raises Missing), or the visitor's own version of it (see `yours`)."""
    y = yours()
    if y is not None and name in y["tables"]:
        return y["tables"][name]
    p = root() / "outputs" / "phase4" / "tables" / f"{name}.csv"
    if not p.exists():
        raise Missing(name)
    return _csv(str(p))


def horizon() -> int:
    return int(table("break_even_summary")["T"].iloc[0])


def row(name: str, scenario: str, k: float = 1.0) -> pd.Series:
    t = table(name)
    r = t[(t["scenario"] == scenario) & (np.isclose(t["multiplier"], k))]
    if r.empty:
        raise Missing(f"{name}:{scenario}:{k}")
    return r.iloc[0]


def monthly(scenario: str, k: float, line: str) -> pd.DataFrame:
    t = table("monthly_summary")
    out = t[(t["scenario"] == scenario) & np.isclose(t["multiplier"], k) & (t["line"] == line)].sort_values("month")
    if out.empty:
        raise Missing(f"monthly:{scenario}:{line}")
    return out


def overview_kpis(scenario: str = "expected", k: float = 1.0) -> dict:
    """Raw values of the four Overview cards (the page formats them)."""
    tot, be = row("totals_summary", scenario, k), row("break_even_summary", scenario, k)
    pays = be["p50_month"] if be["prob_break_even_within_T"] >= 0.5 else float("nan")
    return {"cost": float(tot["total_cost_p50"]), "benefit": float(tot["total_value_p50"]),
            "balance": float(tot["cum_net_T_p50"]), "payback": float(pays), "T": int(be["T"])}


def outlooks() -> list[str]:
    return [s for s in ("downside", "expected", "optimistic") if s in set(table("totals_summary")["scenario"])]


def cautions() -> list[float]:
    return sorted(float(k) for k in table("totals_summary")["multiplier"].unique())


def example_inputs() -> tuple[dict, dict]:
    """(plain values, raw file with notes) of the example company."""
    from engine.inputs import load_inputs
    p = root() / "config" / "example_company.json"
    if not p.exists():
        raise Missing("example_company")
    return load_inputs(p)


@st.cache_resource(show_spinner=False)
def _drivers(T: int, root_str: str):
    import logging
    logging.getLogger("engine").setLevel(logging.ERROR)  # the known price fallback is documented in Phase 4
    from engine.drivers import load_drivers
    r = Path(root_str)
    return load_drivers(T, r / "outputs" / "phase3", r / "data" / "processed")


def drivers(T: int):
    if not (root() / "outputs" / "phase3" / "manifest.json").exists():
        raise Missing("phase3")
    return _drivers(int(T), str(root()))


def outlook_table() -> pd.DataFrame:
    p = root() / "outputs" / "phase3" / "forecasts" / "scenario_tables.csv"
    if not p.exists():
        raise Missing("scenario_tables")
    return _csv(str(p))


def run(inputs: dict, scenario: str, k: float = 1.0, n: int = N_LIVE):
    """One live engine call (fixed starting number, so the same inputs give the same answer)."""
    from engine.simulate import run_engine
    return run_engine(inputs, scenario, k, n, SEED, drivers(int(inputs["horizon_months"])), outlook_table())


@st.cache_data(show_spinner=False)
def _payback_counts(scenario: str, k: float, root_str: str) -> tuple[list[int], int, int]:
    inputs, _ = example_inputs()
    res = run(inputs, scenario, k, N_SAVED)
    be, T = res.break_even, res.meta["T"]
    return [int((be == m).sum()) for m in range(1, T + 1)], int(np.isnan(be).sum()), len(be)


def payback_counts(scenario: str, k: float) -> tuple[list[int], int, int]:
    """Per-month counts of when the programme pays for itself, with the Phase 4 settings (5,000 runs)."""
    y = yours()
    if y is not None:
        return y["payback"][(scenario, float(k))]
    return _payback_counts(scenario, float(k), str(root()))


def run_all(inputs: dict, n: int = N_SAVED) -> dict:
    """Every outlook x caution level for these inputs, plus the 'what matters most' runs, exactly as Phase 4 builds
    its saved results (same futures, starting number, draws and table functions from `engine.report`). With the
    example company's inputs this gives the saved tables back. Returns the tables the pages read, the per-month
    payback counts, and the run of each (outlook, caution level) for the page that called it."""
    from engine import report, sensitivity
    from engine.simulate import ScenarioSkipped, run_engine, summarise
    T = int(inputs["horizon_months"])
    dr, sc = drivers(T), outlook_table()
    names = [s for s in ("downside", "expected", "optimistic")]
    levels = cautions()
    runs = {}
    for s in names:
        for k in levels:
            try:
                res = run_engine(inputs, s, k, n, SEED, dr, sc)
            except ScenarioSkipped:
                continue
            runs[(s, float(k))] = (res, summarise(res))
    sens = sensitivity.tornado(inputs, dr, sc, "expected", 1.0, n, SEED)
    tables = {"monthly_summary": report.monthly_table(runs), "totals_summary": report.totals_table(runs),
              "break_even_summary": report.break_even_table(runs), "cost_breakdown": report.cost_breakdown(runs),
              "sensitivity": sens}
    payback = {key: ([int((r.break_even == m).sum()) for m in range(1, T + 1)], int(np.isnan(r.break_even).sum()),
                     len(r.break_even)) for key, (r, _) in runs.items()}
    return {"tables": tables, "payback": payback, "inputs": dict(inputs), "runs": {k: r for k, (r, _) in runs.items()}}


def monthly_result_table(res) -> pd.DataFrame:
    """Plain table of a live run for the download: month, median cost, benefit and running balance, in rupees
    (the engine's dollar results converted here, at the last step)."""
    from dashboard import copy as C
    from dashboard import currency as CUR
    T = res.meta["T"]
    return pd.DataFrame({C.DOWNLOAD_COLS["month"]: np.arange(1, T + 1),
                         C.DOWNLOAD_COLS["cost"]: CUR.to_inr(np.median(res.total_cost, axis=0)).round(2),
                         C.DOWNLOAD_COLS["benefit"]: CUR.to_inr(np.median(res.value, axis=0)).round(2),
                         C.DOWNLOAD_COLS["balance"]: CUR.to_inr(np.median(res.cum_net, axis=0)).round(2)})


def processed(name: str) -> pd.DataFrame:
    """data/processed/<name>.csv, the real series the forecasts were built on (read only; raises Missing)."""
    p = root() / "data" / "processed" / f"{name}.csv"
    if not p.exists():
        raise Missing(name)
    return _csv(str(p))


def saved_forecast(series: str) -> pd.DataFrame:
    """outputs/phase3/forecasts/<series>.csv: the central line (sample_id -1) and the simulated futures (0 and up)."""
    p = root() / "outputs" / "phase3" / "forecasts" / f"{series}.csv"
    if not p.exists():
        raise Missing(series)
    return _csv(str(p))


# ---------------------------------------------------------------- Phase 1 to 3 results (read only, Phase 5D)
def phase_table(phase: int, name: str) -> pd.DataFrame:
    """outputs/phase<phase>/tables/<name>.csv (raises Missing). Used for Phases 1 to 3."""
    p = root() / "outputs" / f"phase{int(phase)}" / "tables" / f"{name}.csv"
    if not p.exists():
        raise Missing(f"phase{phase}:{name}")
    return _csv(str(p))


def forecast_series() -> list[str]:
    """The series with a saved forecast, in the order the pages list them (see logic_forecasts.SERIES)."""
    from dashboard import logic_forecasts as LF
    folder = root() / "outputs" / "phase3" / "forecasts"
    return [s for s in LF.SERIES if (folder / f"{s}.csv").exists()]


@st.cache_data(show_spinner=False)
def _history(name: str, data_dir: str) -> pd.DataFrame:
    import config
    from tsaf.loaders import SkipDriver, load_driver
    try:
        ld = load_driver(config.driver_by_name(name), Path(data_dir))
    except (SkipDriver, KeyError, FileNotFoundError) as exc:
        raise Missing(f"history:{name}") from exc
    s = ld.series
    flags = ld.flags.reindex(s.index)
    outage = flags["anomaly_low_day"].fillna(False).astype(bool) if "anomaly_low_day" in flags else False
    out = pd.DataFrame({"x": s.index, "value": s.to_numpy(dtype=float)})
    out["known_outage"] = np.asarray(outage, dtype=bool) if not isinstance(outage, bool) else False
    return out, int(ld.full.notna().sum())  # (series used, points with a value in the source before the window)


def history(name: str) -> pd.DataFrame:
    """The real series the forecast was built on (x = date, or a step number when the source has no dates), loaded
    exactly as Phases 1 to 3 loaded it (`tsaf.loaders.load_driver`); nothing is filled or changed."""
    d = root() / "data" / "processed"
    if not d.exists():
        raise Missing("processed")
    return _history(name, str(d))[0].copy()


def source_points(name: str) -> int:
    """How many points with a value the source file holds for this series (the forecasts use a window of them)."""
    d = root() / "data" / "processed"
    if not d.exists():
        raise Missing("processed")
    return _history(name, str(d))[1]


def assumptions_notes() -> dict:
    p = root() / "outputs" / "phase4" / "assumptions.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
