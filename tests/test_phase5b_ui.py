"""Phase 5B (UI polish): both themes render every page, the 3D switch and reduced motion give the still fallbacks,
the 3D pieces get their values from the data layer and those equal the saved Phase 4 tables, text contrast."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import charts, components  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.ui import components_3d as K3  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, PAGES, TABLES, _page_text  # noqa: E402

needs_outputs = pytest.mark.skipif(not (TABLES / "totals_summary.csv").exists(), reason="Phase 4 outputs missing")


def _run(page=None, **state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def _cfg(markup: str) -> dict:
    m = re.search(r'<script type="application/json" id="cfg">(.*?)</script>', markup, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def _visible(markup: str) -> str:
    return re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", markup, flags=re.S)


# ------------------------------------------------------------------ themes
@needs_outputs
@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("page", [None] + PAGES[1:])
def test_both_themes_render_every_page(page, dark):
    at = _run(page, **{T.THEME_KEY: dark})
    assert not at.exception, [e.value for e in at.exception]
    if page is None:  # AppTest keeps the entry script's own elements (styles, banner) only on the first page;
        # the browser check (outputs/phase5/ui_polish/browser_check.py) confirms the banner on every page
        css = " ".join(str(m.value) for m in at.markdown if "<style>" in str(m.value))
        assert T.TOKENS["dark" if dark else "light"]["bg"] in css
        assert C.BANNER in " ".join(str(m.value) for m in at.markdown)
    assert len(at.get("plotly_chart")) >= 1
    hit = BANNED_RE.search(_page_text(at))
    assert not hit, hit.group(0)


@needs_outputs
def test_charts_follow_the_theme(monkeypatch):
    monkeypatch.setattr(T, "mode", lambda: "dark")
    fig = charts.cost_stack({ln: D.monthly("expected", 1.0, ln) for ln in C.LINE})
    assert fig.layout.template.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.template.layout.font.color == T.TOKENS["dark"]["text"]
    monkeypatch.setattr(T, "mode", lambda: "light")
    fig = charts.cost_stack({ln: D.monthly("expected", 1.0, ln) for ln in C.LINE})
    assert fig.layout.template.layout.font.color == T.TOKENS["light"]["text"]


def _lum(hex_color: str) -> float:
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("m", ["light", "dark"])
def test_text_contrast_is_at_least_4_5(m):
    t = T.TOKENS[m]
    for fg in ("text", "muted", "faint", "warm", "accent", "good", "warm-text"):
        for bg in ("bg", "surface-solid"):
            assert _contrast(t[fg], t[bg]) >= 4.5, (m, fg, bg, round(_contrast(t[fg], t[bg]), 2))


# ------------------------------------------------------------------ 3D switch and reduced motion
def test_enable_3d_off_gives_the_still_versions(monkeypatch):
    monkeypatch.setattr(T, "ENABLE_3D", False)
    assert components.motion_on() is False
    items = [{"key": "expected", "label": "Expected outlook", "value": -1.0, "text": "-₹94"}]
    slices = [{"key": "enablement", "label": "Training and support", "tag": "Our estimate", "value": 1.0, "text": "₹94",
               "share": 1.0, "share_text": "100%"}]
    for markup in (components.hero_html(components.motion_on()), K3.money_flow_html(items, components.motion_on()),
                   K3.donut_html(slices, components.motion_on())):
        assert "<script" not in markup and K3.THREE_URL not in markup and 'class="fallback"' in markup
        assert not BANNED_RE.search(_visible(markup))


@needs_outputs
@pytest.mark.parametrize("page", [None, "app_pages/costs.py"])
def test_reduce_motion_switch_gives_still_page(page):
    at = _run(page, **{T.MOTION_KEY: True})
    assert not at.exception
    if page is None:
        html = " ".join(str(m.value) for m in at.markdown)
        assert "aiwi-still" in html and "animation: none" in html  # the reduced-motion rules are applied
    if page == "app_pages/costs.py":  # no 3D donut, so no 3D/flat switch; the flat donut is shown
        assert len(at.get("plotly_chart")) == 3


def test_live_versions_pause_and_clean_up():
    on = K3.hero_html(True)
    for needle in ("IntersectionObserver", "visibilitychange", "pagehide", "dispose", "Math.min(window.devicePixelRatio || 1, 2)",
                   "prefers-reduced-motion", "catch", K3.THREE_URL, "setClearColor(0x000000, 0)"):
        assert needle in on, needle


# ------------------------------------------------------------------ values of the 3D pieces
@needs_outputs
def test_3d_values_come_from_the_phase4_tables():
    tot = pd.read_csv(TABLES / "totals_summary.csv")
    items = logic.year_end_balances(1.0)
    for it in items:
        saved = tot[(tot.scenario == it["key"]) & (tot.multiplier == 1.0)].cum_net_T_p50.iloc[0]
        assert it["value"] == pytest.approx(saved, abs=1e-9) and it["text"] == T.money(saved)
    cfg = _cfg(K3.money_flow_html(items, True))
    assert [d["value"] for d in cfg["items"]] == [it["value"] for it in items]

    br = pd.read_csv(TABLES / "cost_breakdown.csv")
    for sc in D.outlooks():
        b = br[(br.scenario == sc) & (br.multiplier == 1.0)]
        slices = logic.cost_slices(b)
        cfg = _cfg(K3.donut_html(slices, True))
        assert {d["key"]: d["value"] for d in cfg["slices"]} == pytest.approx(dict(zip(b.line, b.p50_total)))
        assert sum(d["share"] for d in cfg["slices"]) == pytest.approx(1.0)
        for d in cfg["slices"]:
            assert d["share"] == pytest.approx(b.set_index("line").loc[d["key"], "p50_share_of_cost"], abs=0.005)

    se = pd.read_csv(TABLES / "sensitivity.csv").sort_values("swing_cum_net_T", ascending=False)
    bars = logic.lever_swings(6)
    assert [b["value"] for b in bars] == pytest.approx(list(se.swing_cum_net_T.head(6)))
    html = components.depth_bars_html(bars, T.ACCENT)
    for b in bars:
        assert b["text"] in html and b["label"] in html


@needs_outputs
def test_status_chips_follow_the_real_results():
    v = D.overview_kpis("expected", 1.0)
    chips = logic.card_status("expected", 1.0)
    assert chips["balance"][1] == (C.CHIP["good"] if v["balance"] >= 0 else C.CHIP["attention"])
    assert chips["payback"][1] == (C.CHIP["good"] if np.isfinite(v["payback"]) else C.CHIP["attention"])
    assert chips["benefit"][1] == C.CHIP["estimate"]  # the benefit stays labelled as an estimate


@needs_outputs
def test_chart_annotations_are_real_numbers():
    series = {s: D.monthly(s, 1.0, "cumulative_net") for s in D.outlooks()}
    be = pd.read_csv(TABLES / "break_even_summary.csv")
    pays = {s: (r.p50_month if r.prob_break_even_within_T >= 0.5 else None)
            for s, r in be[be.multiplier == 1.0].set_index("scenario").iterrows()}
    fig = charts.running_balance(series, True, 12, pays)
    notes = [a.text for a in fig.layout.annotations]
    assert C.LOWEST_POINT.format(value=T.money(series["expected"]["p50"].min())) in notes
    for s, m in pays.items():
        if m is not None:
            assert C.PAYS_MARK.format(month=int(m)) in notes
    assert not BANNED_RE.search(charts.text_of(fig).replace("customdata", ""))


def test_money_ticks_match_the_cards():
    from dashboard.core import currency as CUR
    vals, text = charts.money_ticks(-683_000, 61_000)  # dollars in, round rupee ticks out
    assert 0.0 in vals and "₹0" in text and "-₹2 Cr" in text and all("$" not in t for t in text)
    for v, t in zip(vals, text):
        assert CUR.tick(v * CUR.rate()) == t and t.endswith((" L", " Cr", "₹0"))
    assert T.money_tick(-2e7 / CUR.rate()) == "-₹2 Cr" and T.money_tick(5e6 / CUR.rate()) == "₹50 L"


def test_new_copy_is_plain():
    for s in (C.DARK_MODE, C.REDUCE_MOTION, C.FLOW_TITLE, C.FLOW_HINT, C.DONUT_HINT, C.DEPTH_TITLE, C.DEPTH_NOTE,
              C.LEVERS_CHART_TITLE, C.FLOW_TIP_GOOD, C.FLOW_TIP_BAD, *C.CHIP.values(), *C.DONUT_VIEW):
        assert not BANNED_RE.search(s), s
