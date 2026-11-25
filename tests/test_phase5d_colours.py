"""Phase 5D, step G: the palette. Text reaches 4.5:1 on every surface (glass cards measured as drawn over the page),
chart marks reach 3:1 on cards, colours drawn together on one chart stay clearly apart with normal, red-weak,
green-weak and blue-weak vision, and the four cost types never rely on colour alone."""
from pathlib import Path

import pytest

pytest.importorskip("plotly")

from dashboard.ui import charts, charts_forecast  # noqa: E402
from dashboard.ui import colour_check as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.ui import theme as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("m", ["light", "dark"])
def test_every_colour_check_passes(m):
    failed = [(check, round(value, 2), need) for check, value, need in K.report(m) if value < need]
    assert not failed, failed


@pytest.mark.parametrize("m", ["light", "dark"])
def test_text_on_every_surface(m):
    t = T.TOKENS[m]
    surfaces = {"page": t["bg"], "card": K.over(t["surface"], t["bg"]), "solid card": t["surface-solid"],
                "raised card": K.over(t["elevated"], t["bg"])}
    for fg in ("text", "muted", "faint", "accent", "warm", "warm-text", "good"):
        for name, bg in surfaces.items():
            assert K.contrast(t[fg], bg) >= 4.5, (m, fg, name, round(K.contrast(t[fg], bg), 2))


def test_contrast_and_distance_maths():
    assert K.contrast("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert K.contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)
    assert K.over("rgba(255,255,255,0.5)", "#000000") == "#808080"
    assert K.distance("#123456", "#123456", "deutan") == pytest.approx(0.0)
    # red and green, far apart for most viewers, collapse for red-weak vision: the simulation must show that
    normal, protan = K.distance("#D62728", "#2CA02C"), K.distance("#D62728", "#2CA02C", "protan")
    assert normal > 100 and protan < normal / 3


@pytest.mark.parametrize("m", ["light", "dark"])
def test_chart_groups_stay_apart(m):
    for chart, colours in K.chart_groups(m).items():
        d, pair = K.min_distance(colours)
        assert d >= K.APART_MIN, (m, chart, pair, round(d, 1))


def test_charts_use_the_named_colour_roles(monkeypatch):
    for m in ("light", "dark"):
        monkeypatch.setattr(T, "mode", lambda m=m: m)
        v = {"hist_x": [1, 2, 3], "hist_y": [1.0, 2.0, 3.0], "fc_x": [4, 5], "expected": [3.0, 3.5], "low": [2.0, 2.5],
             "high": [4.0, 4.5], "unit": "points", "divider": C.LAST_REAL, "hist_tips": ["a", "b", "c"], "fc_tips": ["d", "e"],
             "dated": False}
        fig = charts_forecast.series_chart(v)
        by = {tr.name: tr for tr in fig.data if tr.mode == "lines"}
        assert by[C.LEGEND_HAPPENED].line.color == T.CHART_COLORS[m]["history"]
        assert by[C.LEGEND_EXPECT].line.color == T.CHART_COLORS[m]["forecast"]
        past = charts_forecast.past_check_chart({"real_x": [1, 2, 3], "real_y": [1.0, 2.0, 3.0], "real_tips": ["a", "b", "c"],
                                                 "n_pre": 1, "pred_x": [2, 3], "pred_y": [2.1, 2.9], "low": [1.5, 2.5],
                                                 "high": [2.5, 3.5], "inside": [True, True], "unit": "points"})
        by = {tr.name: tr for tr in past.data}
        assert by[C.LEGEND_PREDICTED].line.color == T.CHART_COLORS[m]["predicted"]
        assert by[C.LEGEND_REAL].line.color == T.CHART_COLORS[m]["history"]
        assert T.OUTLOOK_COLORS[m]["expected"] == T.TOKENS[m]["accent"]  # 'what we expect' reads the same everywhere


def test_cost_types_carry_a_pattern_as_well_as_a_colour():
    import pandas as pd
    df = pd.DataFrame({"month": [1, 2], "p50": [1.0, 2.0]})
    fig = charts.cost_stack({ln: df for ln in C.LINE})
    shapes = {tr.name: tr.marker.pattern.shape or "" for tr in fig.data}
    assert len(set(shapes.values())) == len(C.LINE)  # every cost type has its own pattern (one is solid)
    pie = charts.donut(pd.DataFrame({"line": list(C.LINE), "p50_total": [1.0, 2.0, 3.0, 4.0],
                                     "type": ["Forecast-driven", "Forecast-driven", "Estimate", "Estimate"]}))
    assert list(pie.data[0].marker.pattern.shape) == [T.LINE_PATTERNS[ln] for ln in C.LINE]
    for m in ("light", "dark"):
        assert not K.cost_types_told_apart(m)


def test_streamlit_theme_matches_the_accent():
    cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert f'primaryColor = "{T.TOKENS["light"]["accent"]}"' in cfg


def test_no_hard_coded_white_text():
    """Text on the accent gradients takes the theme's on-accent colour (dark text in dark mode, where the gradient is
    light); white written into the stylesheet would fail there."""
    import re
    css = (ROOT / "src" / "dashboard" / "ui" / "styles.css").read_text(encoding="utf-8")
    assert not re.search(r"(?<![-\w])color:\s*#fff\b", css, flags=re.IGNORECASE)
