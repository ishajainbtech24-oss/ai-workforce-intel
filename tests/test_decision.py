"""Workstream D: input uncertainty in the Monte Carlo, decision figures, goal-seek, scenario file, Excel and memo."""
import datetime
import io
import json
import re

import numpy as np
import pandas as pd
import pytest

from dashboard.core import data as D
from dashboard.core import decision as X
from dashboard.ui import copy as C
from engine import model
from test_phase5_dashboard import TABLES, needs_outputs


def test_pert_stays_in_range_and_peaks_at_the_mode():
    x = model.pert(np.random.default_rng(0), 0.5, 1.0, 1.6, 20000)
    assert x.min() >= 0.5 and x.max() <= 1.6
    assert abs(np.mean(x) - (0.5 + 4 * 1.0 + 1.6) / 6) < 0.01  # PERT mean


def test_npv_by_hand():
    r = 1.1 ** (1 / 12) - 1
    assert X.npv([100, 100]) == pytest.approx(100 / (1 + r) + 100 / (1 + r) ** 2)
    assert X.npv([5, -5], 0.0) == pytest.approx(0.0)


@needs_outputs
def test_payback_chance_is_not_flat_in_the_example_or_is_explained():
    be = pd.read_csv(TABLES / "break_even_summary.csv").query("multiplier == 1.0").set_index("scenario")
    tot = pd.read_csv(TABLES / "totals_summary.csv").query("multiplier == 1.0").set_index("scenario")
    for s, p in be["prob_break_even_within_T"].items():
        if p in (0.0, 1.0):  # flat only where the benefit is below zero in every future (cautious outlook)
            assert p == 0.0 and tot.loc[s, "total_value_p90"] < 0, s


@needs_outputs
def test_goal_seek_hits_an_even_chance():
    from engine.simulate import run_engine
    g = X.goal_seek("expected")
    assert g["status"] == "ok" and g["needed"] > g["base"] > 0
    inp = D.active_inputs()
    T = int(inp["horizon_months"])
    hit = lambda f: np.isfinite(run_engine(inp, "expected", 1.0, X.GOAL_DRAWS, D.SEED, D.drivers(T), D.outlook_table(),  # noqa: E731
                                           time_saved_fraction=f).break_even).mean()
    assert hit(g["needed"]) >= 0.5 > hit(g["needed"] * 0.97)


@needs_outputs
def test_metrics_match_the_saved_tables():
    m = X.metrics("optimistic", 1.0)
    tot = pd.read_csv(TABLES / "totals_summary.csv").query("scenario == 'optimistic' and multiplier == 1.0").iloc[0]
    assert m["balance"] == pytest.approx(tot["cum_net_T_p50"]) and m["roi"] == pytest.approx(tot["cum_net_T_p50"] / tot["total_cost_p50"])


def test_scenario_file_round_trip_and_validation():
    fields = {"employees", "realisation_rate"}
    raw = X.scenario_payload({"preset": "small", "outlook": "expected", "caution": 1.0}, {"employees": 80, "realisation_rate": 40})
    doc, problem = X.read_scenario(raw, fields)
    assert problem is None and doc["figures"]["employees"] == 80 and doc["view"]["preset"] == "small"
    assert X.read_scenario(b"not json", fields)[1] == C.SCENARIO_BAD_FILE
    assert X.read_scenario(json.dumps({"format": "other"}).encode(), fields)[1] == C.SCENARIO_BAD_FILE
    bad = json.dumps({"format": X.SCENARIO_FORMAT, "figures": {"salary": 1}}).encode()
    assert X.read_scenario(bad, fields)[1] == C.SCENARIO_BAD_FIELDS
    neg = json.dumps({"format": X.SCENARIO_FORMAT, "figures": {"employees": -3}}).encode()
    assert X.read_scenario(neg, fields)[1] == C.SCENARIO_BAD_VALUES


@needs_outputs
def test_excel_and_memo_pdf():
    from dashboard.ui import report_pdf as PDF
    from dashboard.ui import report_xlsx
    b = D.run_all(D.example_inputs()[0])
    res = b["runs"][("expected", 1.0)]
    rows = X.all_metrics(1.0)
    xl = pd.read_excel(io.BytesIO(report_xlsx.build(rows, res, D.active_inputs())), sheet_name=None)
    assert list(xl) == list(C.XLSX_SHEETS.values()) and len(xl[C.XLSX_SHEETS["summary"]]) == 3
    pdf = PDF.build(res, "expected", b, False, datetime.date(2026, 11, 25), memo=X.memo("expected"))
    assert len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf)) == PDF.PAGES_WITH_MEMO
