"""Rupee display: the Indian-style formatter, one exchange rate in one place, the rupee inputs on "Try your own
numbers" (converted back to dollars for the engine), proportional scaling with the rate, and no dollar wording."""
import re

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from dashboard import charts, components, logic  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import currency as CUR  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import theme as T  # noqa: E402

from test_phase5_dashboard import INR_PER_USD, PAGES, TABLES, _inr, _money, _page_text, _run  # noqa: E402

needs_outputs = pytest.mark.skipif(not (TABLES / "totals_summary.csv").exists(), reason="Phase 4 outputs missing")
DOLLAR_RE = re.compile(r"\$|\bUSD\b|dollar", re.IGNORECASE)
KM_MONEY_RE = re.compile(r"₹\s?[0-9.,]+\s?[KM]\b")
MONEY_RE = re.compile(r"-?₹[0-9.,]+(?: (?:L|Cr))?")


def _value(text: str) -> float:
    """'-₹23.1 L' -> -2310000.0 (back from the screen format, for the scaling test)."""
    neg = text.startswith("-")
    body = text.lstrip("-").lstrip("₹")
    mult = 1e5 if body.endswith(" L") else 1e7 if body.endswith(" Cr") else 1.0
    num = float(body.replace(" L", "").replace(" Cr", "").replace(",", ""))
    return (-1 if neg else 1) * num * mult


def _scrub(text: str) -> str:
    """The rate note names the US dollar on purpose (it says what the rupees were converted from)."""
    return re.sub(r"Amounts are shown in Indian rupees, converted at the rate of .{1,40}? per US dollar", " ", text)


def _grain(text: str) -> float:
    """Half the smallest step a formatted amount can show (its rounding error)."""
    body = text.lstrip("-").lstrip("₹")
    if body.endswith(" L"):
        return 0.05e5
    if body.endswith(" Cr"):
        return 0.005e7 if len(body.split(".")[-1]) == 5 else 0.05e7
    return 0.5


def _doubled(a: str, b: str) -> bool:
    """b shows twice the amount a shows, up to the rounding of both strings."""
    return abs(_value(b) - 2 * _value(a)) <= _grain(b) + 2 * _grain(a) + 1e-6


# ------------------------------------------------------------------ the formatter and the one rate
@pytest.mark.parametrize("x, want", [(950, "₹950"), (12_345, "₹12,345"), (99_999, "₹99,999"),
                                     (2_310_000, "₹23.1 L"), (12_000_000, "₹1.2 Cr"),
                                     (-2_310_000, "-₹23.1 L"), (0, "₹0"), (-0.2, "₹0"),
                                     (99_999.6, "₹1.0 L"), (9_999_000, "₹1.0 Cr"), (26_060_640, "₹2.61 Cr"), (1_234_567_890, "₹123.46 Cr")])
def test_indian_formatter(x, want):
    assert CUR.fmt(x) == want == _inr(x)


def test_none_and_month_words():
    assert T.month(None) == "Not within 12 months" and T.month(float("nan"), 18) == "Not within 18 months"
    assert CUR.fmt(None) == "Not available" and T.money(None) == "Not available"


def test_indian_grouping():
    assert [CUR.group(n) for n in (0, 999, 1000, 12345, 123456, 1234567, 12345678)] == \
        ["0", "999", "1,000", "12,345", "1,23,456", "12,34,567", "1,23,45,678"]


def test_one_rate_in_one_place():
    assert CUR.INR_PER_USD == INR_PER_USD and CUR.CURRENCY == {"symbol": "₹", "code": "INR"}
    assert components.rate_note() == ("Amounts are shown in Indian rupees, converted at the rate of ₹94.1159 per "
                                      "US dollar (RBI reference rate, 16 Nov 2026).")
    src = __import__("pathlib").Path(CUR.__file__).parent
    hits = [p.name for p in src.rglob("*.py") if p.name != "currency.py" and "94.1159" in p.read_text(encoding="utf-8")]
    assert not hits, hits


# ------------------------------------------------------------------ real numbers on screen
@needs_outputs
def test_cards_are_phase4_times_the_rate():
    t = pd.read_csv(TABLES / "totals_summary.csv").query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    want = {k: _inr(t[c] * INR_PER_USD) for k, c in (("cost", "total_cost_p50"), ("benefit", "total_value_p50"),
                                                     ("balance", "cum_net_T_p50"))}
    cards = logic.overview_cards("expected", 1.0)
    assert {k: cards[k] for k in want} == want
    at = _run("views/overview.py")
    html = " ".join(str(m.value) for m in at.markdown)
    for k, v in want.items():
        assert v in html, v
        assert f'data-count="{t[{"cost": "total_cost_p50", "benefit": "total_value_p50", "balance": "cum_net_T_p50"}[k]] * INR_PER_USD}"' in html


@needs_outputs
def test_download_is_in_rupees():
    base, _ = D.example_inputs()
    res = D.run(base, "expected")
    tab = D.monthly_result_table(res)
    assert list(tab.columns)[1:] == ["Total cost (₹)", "Estimated benefit (₹)", "Running balance (₹)"]
    assert tab.iloc[:, 1].to_numpy() == pytest.approx(np.median(res.total_cost, axis=0) * INR_PER_USD, abs=0.01)


# ------------------------------------------------------------------ Try your own numbers
@needs_outputs
def test_round_trip_of_rupee_inputs():
    base, _ = D.example_inputs()
    form = {f: round(base[f] * INR_PER_USD, 2) for f in logic.MONEY_FIELDS}
    assert form["base_hourly_wage_staff"] == pytest.approx(45 * INR_PER_USD, abs=0.01)
    inputs, msgs = logic.to_inputs(base, form)
    assert not msgs
    for f in logic.MONEY_FIELDS:
        assert inputs[f] == pytest.approx(base[f], rel=1e-5)
    res = D.run(inputs, "expected")
    saved = D.row("totals_summary", "expected", 1.0)["total_cost_p50"] * INR_PER_USD
    assert abs(np.median(res.total_cost.sum(axis=1)) * INR_PER_USD / saved - 1) < 0.01


@needs_outputs
def test_company_page_shows_rupee_inputs_and_results():
    at = _run("views/your_company.py")
    assert not at.exception, [e.value for e in at.exception]
    base, _ = D.example_inputs()
    boxes = {n.label: n.value for n in at.number_input}
    for f in logic.MONEY_FIELDS:
        label, unit, _ = C.FIELDS[f]
        assert "₹" in unit and boxes[f"{label} ({unit})"] == pytest.approx(base[f] * INR_PER_USD, abs=0.01)
    html = " ".join(str(m.value) for m in at.markdown)
    saved = D.row("totals_summary", "expected", 1.0)["total_cost_p50"] * INR_PER_USD
    shown = [_value(v) for v in MONEY_RE.findall(html)]
    assert any(abs(v / saved - 1) < 0.01 for v in shown), shown
    # change a rupee input, update, then reset to the example: the converted defaults come back
    at.number_input(key="co_base_hourly_wage_staff").set_value(6000.0)
    at.button(key="reset_btn").click().run()
    assert at.number_input(key="co_base_hourly_wage_staff").value == pytest.approx(base["base_hourly_wage_staff"] * INR_PER_USD,
                                                                                  abs=0.01)


# ------------------------------------------------------------------ the rate scales every amount, nothing else
@needs_outputs
def test_changing_the_rate_scales_amounts_only(monkeypatch):
    def snapshot():
        b = D.table("cost_breakdown").query("scenario == 'expected' and multiplier == 1.0")
        return (logic.overview_cards("expected", 1.0), logic.year_end_balances(1.0), logic.cost_slices(b),
                logic.lever_swings(6), logic.findings())
    cards1, flow1, slices1, levers1, find1 = snapshot()
    monkeypatch.setattr(CUR, "INR_PER_USD", INR_PER_USD * 2)
    cards2, flow2, slices2, levers2, find2 = snapshot()
    for k in ("cost", "benefit", "balance"):
        assert _doubled(cards1[k], cards2[k]), (cards1[k], cards2[k])
    assert cards2["payback"] == cards1["payback"]
    for a, b in zip(flow1 + slices1 + levers1, flow2 + slices2 + levers2):
        assert b["value"] == a["value"] and _doubled(a["text"], b["text"]), (a["text"], b["text"])
        assert b.get("share_text") == a.get("share_text")
    assert find2[0] == find1[0] and find2[2] == find1[2]  # percentages only
    m1, m2 = MONEY_RE.findall(find1[1]), MONEY_RE.findall(find2[1])
    assert _doubled(m1[0], m2[0])
    assert MONEY_RE.sub("", find1[1]) == MONEY_RE.sub("", find2[1])


# ------------------------------------------------------------------ no dollars anywhere on screen
def _copy_strings():
    from test_phase5_dashboard import _copy_text
    return _copy_text()


def test_copy_has_no_dollar_wording():
    hits = [s for s in _copy_strings() if s != C.RATE_NOTE and DOLLAR_RE.search(s)]
    assert not hits, hits


@needs_outputs
@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("page", [None] + PAGES[1:])
def test_rendered_pages_have_no_dollars(page, dark):
    from test_phase5b_ui import _run as run_state
    at = run_state(page, **{T.THEME_KEY: dark})
    assert not at.exception
    text = _scrub(_page_text(at) + " " + " ".join(str(m.value) for m in at.markdown))
    text = re.sub(r"<style.*?</style>|<script.*?</script>", " ", text, flags=re.S)
    hit = DOLLAR_RE.search(text) or KM_MONEY_RE.search(text)
    assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]
    if page is None:
        assert components.rate_note() in " ".join(str(m.value) for m in at.markdown)  # caption under the banner


@needs_outputs
def test_charts_have_no_dollars():
    b = D.table("cost_breakdown").query("scenario == 'expected' and multiplier == 1.0")
    items = logic.year_end_balances(1.0)
    base, _ = D.example_inputs()
    res = D.run(base, "expected")
    figs = [charts.running_balance({s: D.monthly(s, 1.0, "cumulative_net") for s in D.outlooks()}, True, 12),
            charts.year_end_bars(items), charts.cost_stack({ln: D.monthly("expected", 1.0, ln) for ln in C.LINE}),
            charts.donut(b), charts.benefit_vs_cost(D.monthly("expected", 1.0, "total_cost"), D.monthly("expected", 1.0, "value"),
                                                    T.ACCENT),
            charts.levers(D.table("sensitivity")), charts.balance_band(res.cum_net, T.ACCENT, "x")]
    for f in figs:
        custom = [np.ravel(np.asarray(tr.customdata, dtype=object)) for tr in f.data if getattr(tr, "customdata", None) is not None]
        text = charts.text_of(f) + " " + " ".join(str(x) for c in custom for x in c)
        assert not DOLLAR_RE.search(text) and not KM_MONEY_RE.search(text), text[:300]
    for f in figs[:3] + figs[4:]:
        title = str((f.layout.yaxis if f.layout.xaxis.title.text != C.AXIS_CHANGE else f.layout.xaxis).title.text)
        assert "₹" in title, title
    assert "₹" in str(figs[5].layout.xaxis.title.text)
    from dashboard import components_3d as K3
    for markup in (K3.money_flow_html(items, True), K3.donut_html(logic.cost_slices(b), True),
                   components.depth_bars_html(logic.lever_swings(6), T.ACCENT)):
        cfg = re.search(r'<script type="application/json" id="cfg">(.*?)</script>', markup, re.S)
        seen = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", markup, flags=re.S) + (cfg.group(1) if cfg else "")
        assert not DOLLAR_RE.search(seen) and "₹" in seen, seen[:300]
