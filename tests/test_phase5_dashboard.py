"""Phase 5 dashboard: real numbers, plain wording, every page renders, missing data, live engine, speed."""
import math
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import charts, components  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "src" / "dashboard" / "app.py")
TABLES = ROOT / "outputs" / "phase4" / "tables"
PAGES = ["app_pages/welcome.py", "app_pages/overview.py", "app_pages/data_used.py", "app_pages/forecast.py", "app_pages/reliability.py", "app_pages/costs.py", "app_pages/timing.py", "app_pages/levers.py", "app_pages/your_company.py"]
BANNED = ["model", "algorithm", "forecast model", "ARIMA", "SARIMA", "Holt", "XGBoost", "Prophet", "LSTM", "ensemble",
          "backtest", "MASE", "RMSE", "MAE", "sMAPE", "stationarity", "ADF", "KPSS", "decomposition", "seasonality",
          "lag", "residual", "quantile", "percentile", "P10", "P50", "P90", "Monte Carlo", "simulation", "draw", "path",
          "bootstrap", "multiplier", "parquet", "CSV", "JSON", "API", "driver", "index", "ECI", "PPI", "BurstGPT",
          "WildChat", "METR", "Epoch", "token", "run_engine", "seed"]
BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b", re.IGNORECASE)
needs_outputs = pytest.mark.skipif(not (TABLES / "totals_summary.csv").exists(), reason="Phase 4 outputs missing")


def _strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _strings(v)]
    if isinstance(obj, (list, tuple)):
        return [s for v in obj for s in _strings(v)]
    return []


def _copy_text() -> list[str]:
    return [s for name, v in vars(C).items() if not name.startswith("_") for s in _strings(v)]


INR_PER_USD = 94.1159  # written out here on purpose: the test must not borrow the dashboard's own constant


def _inr(x: float) -> str:
    """Independent Indian-style formatter of a rupee amount (lakh = 1,00,000; crore = 1,00,00,000)."""
    a = abs(x)
    if round(a) < 100_000:
        n = str(round(a))
        if len(n) > 3:
            head, tail = n[:-3], n[-3:]
            head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
            n = f"{head},{tail}"
        body = "₹" + n
    elif round(a / 1e5, 1) < 100:
        body = f"₹{a / 1e5:.1f} L"
    else:
        cr = f"{a / 1e7:.2f}"
        body = f"₹{cr[:-1] if cr.endswith('0') else cr} Cr"
    return ("-" if x < 0 and body != "₹0" else "") + body


def _money(usd: float) -> str:  # a saved dollar value as the screen must show it
    return _inr(usd * INR_PER_USD)


def _page_text(at: AppTest) -> str:
    """Text of every rendered element except chart specs (charts are scanned through charts.text_of)."""
    parts = []
    for node in at.main.children.values() if hasattr(at.main, "children") else []:
        parts.append(_node_text(node))
    return " ".join(parts)


def _node_text(node) -> str:
    if getattr(node, "type", "") == "plotly_chart":
        return ""
    # the closed "Explore technical details" panels are the one place technical names may appear, each explained
    # in the same sentence (tests/test_beginner_pass.py checks that); everything else stays in plain words
    if getattr(node, "type", "") == "expander" and getattr(node, "label", "") == C.TECH_TITLE:
        return ""
    kids = getattr(node, "children", None)
    if kids:
        return " ".join(_node_text(k) for k in kids.values())
    proto = getattr(node, "proto", None)
    if proto is None:
        return ""
    raw = str(proto).encode().decode("unicode_escape", errors="ignore")
    # only what a reader sees: the text fields of the element, without <style>/<script> blocks and tags
    fields = re.findall(r'^\s*(?:body|label|help|placeholder|value|text|caption|options|default|alt|data)'
                        r':\s*"(.*)"\s*$', raw, flags=re.M)
    visible = " ".join(fields)
    return re.sub(r"<style.*?</style>|<script.*?</script>|<[^>]+>", " ", visible, flags=re.S)


def _run(page: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


@needs_outputs
def test_overview_kpis_are_the_real_numbers():
    tot = pd.read_csv(TABLES / "totals_summary.csv")
    be = pd.read_csv(TABLES / "break_even_summary.csv")
    t = tot[(tot["scenario"] == "expected") & (tot["multiplier"] == 1.0)].iloc[0]
    b = be[(be["scenario"] == "expected") & (be["multiplier"] == 1.0)].iloc[0]
    pays = f"Month {int(round(b['p50_month']))}" if b["prob_break_even_within_T"] >= 0.5 else f"Not within {int(b['T'])} months"
    expect = {"cost": _money(t["total_cost_p50"]), "benefit": _money(t["total_value_p50"]),
              "balance": _money(t["cum_net_T_p50"]), "payback": pays}
    assert logic.overview_cards("expected", 1.0) == expect
    at = _run("app_pages/overview.py")
    html = " ".join(str(m.value) for m in at.markdown)
    for v in expect.values():
        assert v in html, v


def test_copy_has_no_banned_words():
    hits = [(s, BANNED_RE.search(s).group(0)) for s in _copy_text() if BANNED_RE.search(s)]
    assert not hits, hits[:5]


@needs_outputs
@pytest.mark.parametrize("page", [None] + PAGES[1:])
def test_every_page_renders_plainly(page):
    at = _run(page)
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("plotly_chart")) >= 1
    text = _page_text(at)
    assert not re.search(r"\b(nan|None|Traceback)\b", text)
    hit = BANNED_RE.search(text)
    assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]


@needs_outputs
def test_components_and_charts_have_no_banned_words():
    html = components.hero_html(True) + components.kpi_card("Total cost over the year", "₹1,000", "x", components.sparkline_svg([1, 2, 3]))
    visible = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
    assert not BANNED_RE.search(visible)
    figs = [charts.running_balance({s: D.monthly(s, 1.0, "cumulative_net") for s in D.outlooks()}, True, 12),
            charts.cost_stack({ln: D.monthly("expected", 1.0, ln) for ln in C.LINE}),
            charts.donut(D.table("cost_breakdown").query("scenario == 'expected' and multiplier == 1.0")),
            charts.payback_bars([1] * 12, 3, 15, 12, T.ACCENT), charts.levers(D.table("sensitivity"))]
    for f in figs:
        hit = BANNED_RE.search(charts.text_of(f).replace("customdata", ""))
        assert not hit, hit.group(0)


def test_missing_data_shows_friendly_message(tmp_path, monkeypatch):
    monkeypatch.setenv("TSAF_DASH_ROOT", str(tmp_path))
    for page in [None] + PAGES[1:]:
        at = _run(page)
        assert not at.exception, (page, [e.value for e in at.exception])
        assert any(C.MISSING in str(i.value) for i in at.info), page


@needs_outputs
def test_your_company_matches_phase4_and_is_monotone():
    base, _ = D.example_inputs()
    res = D.run(base, "expected")
    saved = D.row("totals_summary", "expected", 1.0)["total_cost_p50"]
    assert abs(np.median(res.total_cost.sum(axis=1)) / saved - 1) < 0.01
    big = D.run(dict(base, employees=2 * base["employees"]), "expected")
    assert np.median(big.lines["token_expenditure"].sum(axis=1)) > np.median(res.lines["token_expenditure"].sum(axis=1))
    assert np.median(big.value.sum(axis=1)) > np.median(res.value.sum(axis=1))


@needs_outputs
def test_invalid_inputs_give_messages_and_skip_the_engine():
    base, _ = D.example_inputs()
    def boom(*a, **k):
        raise AssertionError("the engine must not be called")
    for form, msg in (({"employees": -5}, C.ERRORS["employees"]), ({"adoption_target": 140}, C.ERRORS["share"])):
        res, msgs = logic.submit(base, form, "expected", boom)
        assert res is None and msg in msgs


@needs_outputs
def test_every_engine_name_maps_to_a_plain_label_and_back():
    for name in ("totals_summary", "break_even_summary"):
        t = D.table(name)
        assert set(t["scenario"]) <= set(C.OUTLOOK) and set(t["multiplier"].astype(float)) <= set(C.CAUTION)
    assert set(D.table("cost_breakdown")["line"]) <= set(C.LINE)
    assert set(D.table("sensitivity")["input"]) <= set(C.LEVER)
    for mapping in (C.OUTLOOK, C.CAUTION, C.LINE, C.LEVER):
        back = {v: k for k, v in mapping.items()}
        assert len(back) == len(mapping) and all(back[mapping[k]] == k for k in mapping)


def test_formatters():
    from dashboard.core import currency as CUR
    assert CUR.fmt(950) == "₹950" and CUR.fmt(12_345) == "₹12,345" and CUR.fmt(2_310_000) == "₹23.1 L"
    assert CUR.fmt(12_000_000) == "₹1.2 Cr" and CUR.fmt(-2_310_000) == "-₹23.1 L" and CUR.fmt(0) == "₹0"
    assert T.month(None) == "Not within 12 months"
    assert T.money(276_899) == _money(276_899) == "₹2.61 Cr" and T.money(-96_640.8) == "-₹91.0 L"
    assert T.month(float("nan")) == "Not within 12 months" and T.month(None, 18) == "Not within 18 months"
    assert T.month(9.0) == "Month 9" and T.share(0.65) == "65%" and T.share(0.088) == "8.8%"


def test_hero_fallback_without_3d():
    off, on = components.hero_html(use_3d=False), components.hero_html(use_3d=True)
    assert components.THREE_URL not in off and "linear-gradient" in off and "<script" not in off
    assert components.THREE_URL in on and "prefers-reduced-motion" in on and "catch" in on


@needs_outputs
def test_live_engine_speed():
    base, _ = D.example_inputs()
    t0 = time.time()
    D.run(base, "expected")
    assert time.time() - t0 < 3.0


@needs_outputs
def test_timing_counts_match_saved_probability():
    for sc in D.outlooks():
        counts, none, total = D.payback_counts(sc, 1.0)
        prob = D.row("break_even_summary", sc, 1.0)["prob_break_even_within_T"]
        assert math.isclose(sum(counts) / total, prob, abs_tol=1e-12) and none + sum(counts) == total
