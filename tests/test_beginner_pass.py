"""Beginner pass: every chart explains itself, every 'What it means' sentence is filled in from the saved results,
controls carry hints, suggestions are labelled as suggestions, technical names appear only in the closed technical
panels (each with a plain explanation), and the new 3D pieces have still versions."""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard.ui import components_3d as K3  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.ui import copy_technical as CT  # noqa: E402
from dashboard.core import data as D  # noqa: E402
from dashboard.core import explain as EX  # noqa: E402
from dashboard.core import logic  # noqa: E402
from dashboard.core import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, TABLES, _money  # noqa: E402
from test_phase5d_loaders import FC_DIR, P1, P2, P3, SEVEN, needs  # noqa: E402
from test_phase5d_reliability import TECH_RE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHART_PAGES = {None: 1, "app_pages/overview.py": 2, "app_pages/data_used.py": 2, "app_pages/forecast.py": 1,
               "app_pages/reliability.py": 2, "app_pages/costs.py": 3, "app_pages/timing.py": 2, "app_pages/levers.py": 2,
               "app_pages/your_company.py": 2}  # charts that explain themselves on each page (3D views count once)


def _page(path, **state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if path:
        at.switch_page(path)
        at.run()
    return at


def _guides(at: AppTest) -> list[str]:
    return [str(m.value) for m in at.markdown if '<div class="chart-guide' in str(m.value)]


@needs
@pytest.mark.parametrize("page", list(CHART_PAGES))
def test_every_chart_has_a_three_line_guide(page):
    at = _page(page)
    assert not at.exception, [e.value for e in at.exception]
    guides = _guides(at)
    assert len(guides) >= CHART_PAGES[page], (page, len(guides))
    for g in guides:
        assert all(label in g for label in C.GUIDE_LABELS)
        text = re.sub(r"<[^>]+>", " ", g)
        assert not BANNED_RE.search(text) and not TECH_RE.search(text), text
        assert not re.search(r"\{\w+\}|\bnan\b|None", text), text  # every blank filled in


@needs
def test_glossary_and_hints_are_on_the_page():
    at = _page("app_pages/forecast.py")
    md = " ".join(str(m.value) for m in at.markdown)
    for term in list(C.GLOSSARY) + list(C.GLOSSARY_MORE):
        assert term in md, term
    for d in list(C.GLOSSARY_MORE.values()):
        assert not BANNED_RE.search(d) and not TECH_RE.search(d), d
    helps = {w.label: getattr(w, "help", "") for w in list(at.get("button_group")) + list(at.toggle)}
    assert all(helps.values()), helps  # every switch and choice carries a hint


@needs
def test_guide_sentences_match_the_saved_numbers():
    # Welcome: hosting prices (index December 2000 = 100 in the source file)
    d = LF.hosting_hero(pd.read_csv(ROOT / "data" / "processed" / "ppi_hosting_monthly.csv"),
                        pd.read_csv(FC_DIR / "ppi_hosting_monthly.csv"))
    fc = pd.read_csv(FC_DIR / "ppi_hosting_monthly.csv")
    end = fc.loc[(fc["sample_id"] == -1) & (fc["period_index"] == 12), "value"].iloc[0]
    means = EX.welcome(d)[1]
    assert f"by {LF.pct(end / d['hist_values'][-1] - 1)}" in means and f"{LF.pct(end / 100 - 1)} above" in means
    # running balance: lowest point and year end of the expected outlook
    m = pd.read_csv(TABLES / "monthly_summary.csv").query("multiplier == 1.0 and line == 'cumulative_net'")
    e = m[m["scenario"] == "expected"].sort_values("month")
    series = {sc: D.monthly(sc, 1.0, "cumulative_net") for sc in D.outlooks()}
    be = pd.read_csv(TABLES / "break_even_summary.csv").query("multiplier == 1.0").set_index("scenario")
    pays = {sc: (be.loc[sc, "p50_month"] if be.loc[sc, "prob_break_even_within_T"] >= 0.5 else None) for sc in be.index}
    story = EX.balance(series, pays, 12)[1]
    i = int(np.argmin(e["p50"].to_numpy()))
    assert _money(e["p50"].iloc[i]) in story and f"month {int(e['month'].iloc[i])}" in story and _money(e["p50"].iloc[-1]) in story
    # cost peak, largest cost type, month the benefit first beats the cost
    tc = D.monthly("expected", 1.0, "total_cost")
    assert _money(tc["p50"].max()) in EX.cost_stack(tc)[1]
    b = pd.read_csv(TABLES / "cost_breakdown.csv").query("scenario == 'expected' and multiplier == 1.0")
    top = b.loc[b["p50_total"].idxmax()]
    assert C.LINE[top["line"]] in EX.donut(b)[1]
    val = D.monthly("expected", 1.0, "value")
    above = val["p50"].to_numpy() > tc["p50"].to_numpy()
    want = f"month {int(tc['month'].to_numpy()[np.argmax(above)])}" if above.any() else C.STORY_BENEFIT_BELOW
    assert want in EX.benefit_cost(tc, val)[1]
    # levers: the top choice and its gap
    s = pd.read_csv(TABLES / "sensitivity.csv").sort_values("swing_cum_net_T", ascending=False)
    assert _money(s["swing_cum_net_T"].iloc[0]) in EX.levers_depth(logic.lever_swings(6))[1]
    assert _money(s["base_median_cum_net_T"].iloc[0]) in EX.levers_chart(s)[1]


@needs
@pytest.mark.parametrize("name", SEVEN)
def test_forecast_and_reliability_guides_per_trend(name):
    fc = pd.read_csv(FC_DIR / f"{name}.csv")
    g, saved = LF.grain(fc), LF.saved_horizon(fc)
    h = D.history(name)
    v = LF.forecast_view(name, saved, h, D.saved_forecast(name), pd.read_csv(P3 / "interval_check.csv"))
    means, why = EX.forecast(name, v, float(h["value"].iloc[-1]))[1:]
    exp, lo, hi = v["chart"]["expected"][-1], v["chart"]["low"][-1], v["chart"]["high"][-1]
    spread = (hi - lo) / 2 / abs(exp)
    word = "narrow" if spread < 0.05 else "moderate" if spread < 0.25 else "wide" if spread <= 1 else "very wide"
    assert f"likely range is {word} " in means
    assert why == C.FEEDS.get(name, C.FEEDS["other"])
    rv = LF.reliability_view(name, h, g, pd.read_csv(P2 / "chosen_models.csv"), pd.read_csv(P2 / "holdout.csv"),
                             pd.read_csv(P3 / "interval_check.csv"), pd.read_csv(P2 / "leaderboard.csv"))
    hold = pd.read_csv(P2 / "holdout.csv")
    ho = hold[(hold["driver"] == name) & (hold["model"] == rv["approach"])]
    low_share = float((ho["actual"] > ho["forecast"]).mean())
    bias = "too low" if low_share >= 2 / 3 else "too high" if low_share <= 1 / 3 else "sometimes too low"
    assert bias in EX.past(rv)[1]
    dv = LF.data_view(name, h, g, D.source_points(name), pd.read_csv(P1 / "anomalies.csv"), pd.read_csv(P1 / "decomposition.csv"))
    vals = np.asarray(dv["pattern"]["values"], float)
    assert LF.pct(1 - vals.min() / vals.max()) in EX.data_pattern(dv, g)[1]


@needs
def test_findings_and_ideas_are_kept_apart():
    at = _page("app_pages/overview.py")
    md = " ".join(str(m.value) for m in at.markdown)
    assert C.INSIGHTS_DATA_TITLE in md and C.INSIGHTS_IDEAS_TITLE in md and C.INSIGHTS_IDEAS_NOTE in md
    assert md.index(C.INSIGHTS_DATA_TITLE) < md.index(C.INSIGHTS_IDEAS_TITLE)
    tot = pd.read_csv(TABLES / "totals_summary.csv").query("scenario == 'expected' and multiplier == 1.0").iloc[0]
    ideas = logic.ideas()
    assert any(_money(tot["peak_investment_p50"]) in i for i in ideas)
    for i in ideas:
        assert i in md


@needs
@pytest.mark.parametrize("page", ["app_pages/forecast.py", "app_pages/reliability.py", "app_pages/data_used.py", "app_pages/timing.py",
                                  "app_pages/levers.py"])
def test_technical_panels_explain_every_term(page):
    at = _page(page)
    panels = [e for e in at.expander if e.label == C.TECH_TITLE]
    assert len(panels) == 1
    text = " ".join(str(getattr(n, "value", "")) for n in panels[0].children.values())
    for term, meaning in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", text):
        assert len(meaning.split()) >= 6, (term, meaning)  # every technical name comes with a plain explanation


def test_technical_words_live_only_in_the_technical_text():
    for name in CT.TECH_NAME.values():
        assert name not in " ".join(str(v) for v in vars(C).values() if isinstance(v, str))
    for key, (term, meaning) in CT.TERMS.items():
        if key == "approach":  # pairs the plain name with the technical one: '{plain} (technical name: {tech})'
            assert "{plain}" in meaning and "{tech}" in meaning
            continue
        assert len(meaning.split()) >= 6, term


def test_remaining_3d_pieces_have_still_versions():
    """UI v3 keeps three 3D pieces (Welcome banner, year-end columns, cost donut); the cone and the pattern bars that
    repeated flat charts are gone."""
    assert not hasattr(K3, "cone_html") and not hasattr(K3, "pattern_bars_html")
    items = [{"key": "expected", "label": "Expected outlook", "value": -1.0, "text": "-₹94"}]
    slices = [{"key": "enablement", "label": "Training and support", "tag": "Our estimate", "value": 1.0, "text": "₹94",
               "share": 1.0, "share_text": "100%"}]
    for still in (K3.hero_html(False), K3.money_flow_html(items, False), K3.donut_html(slices, False)):
        assert "<script" not in still and K3.THREE_URL not in still and 'class="fallback"' in still
        vis = re.sub(r"<style.*?</style>|<[^>]+>", " ", still, flags=re.S)
        assert not BANNED_RE.search(vis) and not TECH_RE.search(vis)
    hero = K3.hero_html(True)
    assert "background-clip:text" not in hero and "GridHelper" in hero and "grid.visible = false" in hero
