"""Phase 5D, step F: The big picture and When it pays for itself. Every new number is recomputed here from the saved
files (Phase 4 sensitivity and break-even tables, Phase 3 forecasts, Phase 2 held-back checks)."""
import math

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

from dashboard import charts, logic  # noqa: E402
from dashboard import copy as C  # noqa: E402
from dashboard import data as D  # noqa: E402
from dashboard import logic_forecasts as LF  # noqa: E402

from test_phase5_dashboard import APP, BANNED_RE, TABLES, _money, _page_text  # noqa: E402
from test_phase5d_loaders import FC_DIR, P2, needs  # noqa: E402
from test_phase5d_reliability import TECH_RE  # noqa: E402


def _page(path: str, **state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    at.switch_page(path)
    at.run()
    return at


@needs
def test_decision_list_is_the_top_three_levers():
    s = pd.read_csv(TABLES / "sensitivity.csv").sort_values("swing_cum_net_T", ascending=False).head(3)
    items = logic.decide_items(3)
    assert [it["label"] for it in items] == [C.LEVER[i] for i in s["input"]]
    for it, r in zip(items, s.itertuples()):
        assert it["gap"] == C.DECIDE_GAP.format(swing=_money(r.swing_cum_net_T))
        word = C.RAISE if r.median_cum_net_T_high > r.median_cum_net_T_low else C.LOWER
        assert it["helps"] == C.DECIDE_HELPS.format(phrase=f"{word} {C.LEVER[r.input].lower()}")


@needs
def test_cost_trends_strip_uses_the_saved_forecasts():
    want = {}
    for name, col, file in (("eci_wages_quarterly", "eci_wages_sa", "eci_quarterly"),
                            ("ppi_hosting_monthly", "ppi_hosting", "ppi_hosting_monthly")):
        hist = pd.read_csv(FC_DIR.parents[2] / "data" / "processed" / f"{file}.csv").dropna(subset=[col])
        fc = pd.read_csv(FC_DIR / f"{name}.csv")
        end = fc[fc["sample_id"] == -1].sort_values("period_index")["value"].iloc[-1]
        want[name] = end / float(hist[col].iloc[-1]) - 1
        got, _, _ = LF.expected_change(D.history(name), D.saved_forecast(name))
        assert got == pytest.approx(want[name])
    assert LF.change_text(want["eci_wages_quarterly"]) == "+6.8%" and LF.change_text(want["ppi_hosting_monthly"]) == "+1.5%"
    hold, chosen = pd.read_csv(P2 / "holdout.csv"), pd.read_csv(P2 / "chosen_models.csv").set_index("driver")
    for name in LF.STRIP_SERIES + LF.USAGE_SERIES:
        h = hold[(hold["driver"] == name) & (hold["model"] == chosen.loc[name, "chosen_model"])]
        assert LF.miss_share(hold, chosen.reset_index(), name) == pytest.approx(h["holdout_mae"].iloc[0] / h["actual"].mean(), rel=1e-6)


@needs
def test_big_picture_page():
    at = _page("views/overview.py")
    assert not at.exception, [e.value for e in at.exception]
    md = " ".join(str(m.value) for m in at.markdown)
    assert C.OVERVIEW_TITLE in md and C.HERO_TITLE not in md  # the promise lives on Welcome now
    for it in logic.decide_items(3):
        assert it["label"] in md and it["gap"] in md and it["helps"] in md
    for name in LF.STRIP_SERIES:
        change, end, when = LF.expected_change(D.history(name), D.saved_forecast(name))
        assert C.STRIP_CHANGE.format(change=LF.change_text(change), end=end) in md
        assert C.STRIP_MEANING.format(when=when) in md
    hold, chosen = D.phase_table(2, "holdout"), D.phase_table(2, "chosen_models")
    usage = [LF.miss_share(hold, chosen, s) for s in LF.USAGE_SERIES]
    assert C.STRIP_RELIABLE.format(pay=LF.pct(LF.miss_share(hold, chosen, "eci_wages_quarterly")),
                                   host=LF.pct(LF.miss_share(hold, chosen, "ppi_hosting_monthly")),
                                   lo=LF.pct(min(usage)), hi=LF.pct(max(usage))) in md
    assert [e.label for e in at.expander if e.label == C.SEE_3D]  # the 3D columns open on request
    text = _page_text(at)
    for regex in (BANNED_RE, TECH_RE):
        hit = regex.search(text)
        assert not hit, text[max(0, hit.start() - 80): hit.end() + 80]


@needs
@pytest.mark.parametrize("k", [1.0, 1.5, 2.0])
def test_payback_dots_follow_the_break_even_table(k):
    be = pd.read_csv(TABLES / "break_even_summary.csv")
    be = be[np.isclose(be["multiplier"], k)].set_index("scenario")
    rows = logic.payback_dots(k)
    assert [r["key"] for r in rows] == ["downside", "expected", "optimistic"]
    for r in rows:
        b = be.loc[r["key"]]
        pays = b["prob_break_even_within_T"] >= 0.5 and math.isfinite(b["p50_month"])
        assert (r["month"] == b["p50_month"]) if pays else (r["month"] is None)
        assert r["prob"] == pytest.approx(b["prob_break_even_within_T"])
    fig = charts.payback_dots(rows)
    xs = [tr.x[0] for tr in fig.data]
    for r, x in zip(rows, xs):
        assert x == (r["month"] if r["month"] is not None else r["horizon"] + 1.4)
    for tr in fig.data:
        for s in list(tr.customdata) + list(tr.text) + [tr.name]:
            assert not BANNED_RE.search(str(s)) and not TECH_RE.search(str(s)), s


@needs
def test_timing_page_shows_the_dots():
    at = _page("views/timing.py")
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("plotly_chart")) == 2
    md = " ".join(str(m.value) for m in at.markdown)
    assert C.TIMING_DOTS_TITLE in md
