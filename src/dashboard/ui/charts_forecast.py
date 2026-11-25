"""Plotly figures of the saved forecasts: what happened (solid), a divider at the last real value ("Today" on the
Welcome page), what we expect (dashed) and the likely range (shaded band that widens with time). Every label is
plain language from copy.py; numbers use the Indian style (lakh, crore) or one decimal for levels; colours come
from the current theme.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.ui import copy as C
from dashboard.core import logic_forecasts as LF
from dashboard.ui import theme as T
from dashboard.ui.charts import _rgba


def count_ticks(lo: float, hi: float, unit: str, n: int = 5) -> tuple[list[float], list[str]]:
    """Round tick positions covering [lo, hi] with labels in the same style as the page text."""
    span = (hi - lo) or abs(hi) or 1.0
    raw = span / n
    mag = 10 ** np.floor(np.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    vals = [float(round(v, 6)) for v in np.arange(np.floor(lo / step) * step, hi + step * 0.999, step)]
    if unit == "points":
        return vals, [f"{v:g}" for v in vals]
    return vals, [LF.amount(v) for v in vals]


def time_controls(fig: go.Figure, xs: list, dated: bool, grain: str | None) -> None:
    """History charts: 6M / 1Y / 5Y / All buttons and a range slider on dated series; 'last N' buttons on series that
    count days or hours from the start (BurstGPT has no calendar dates)."""
    style = dict(bgcolor=T.tok("bg-2"), activecolor=T.tok("accent-soft"), bordercolor=T.tok("border"), borderwidth=1,
                 font=dict(color=T.tok("text"), size=12))
    if dated:
        buttons = [dict(count=n, label=lab, step=step, stepmode="backward") for lab, n, step in C.RANGE_BUTTONS_DATED]
        fig.update_xaxes(rangeselector=dict(buttons=buttons + [dict(step="all", label=C.RANGE_ALL)], x=0, y=1.0,
                                            xanchor="left", yanchor="bottom", **style),
                         rangeslider=dict(visible=True, thickness=0.06, bgcolor=T.tok("bg-2")))
        fig.update_layout(margin=dict(t=56))
        return
    steps = C.RANGE_BUTTONS_STEPS.get("hour" if grain == "hour" else "day")
    if not steps or not xs:
        return
    last = float(xs[-1])
    buttons = [dict(label=lab, method="relayout", args=[{"xaxis.range": [last - n + 0.5, last + 0.5]}]) for lab, n in steps
               if n < len(xs)]
    buttons.append(dict(label=C.RANGE_ALL, method="relayout", args=[{"xaxis.autorange": True}]))
    fig.update_layout(updatemenus=[dict(type="buttons", direction="right", x=0, y=1.0, xanchor="left", yanchor="bottom",
                                        showactive=False, pad=dict(t=0, b=4), buttons=buttons,
                                        **{k: v for k, v in style.items() if k != "activecolor"})],
                      margin=dict(t=56))


def shocks(fig: go.Figure, first, last) -> None:
    """Mark known shocks (COVID-19, ChatGPT launch) on dated charts whose span covers them."""
    try:
        lo, hi = pd.Timestamp(first), pd.Timestamp(last)
    except (TypeError, ValueError):
        return
    for day, text in C.SHOCKS.items():
        t = pd.Timestamp(day)
        if lo <= t <= hi:
            fig.add_shape(type="line", x0=t, x1=t, xref="x", y0=0, y1=1, yref="paper",
                          line=dict(color=T.tok("faint"), width=1, dash="dash"))
            fig.add_annotation(x=t, y=0.98, xref="x", yref="paper", text=text, showarrow=False, xanchor="right",
                               yanchor="top", xshift=-4, bgcolor=T.tok("surface-solid"), borderpad=2,
                               font=dict(color=T.tok("muted"), size=11))


def series_chart(v: dict, height: int = 420, title: str = "") -> go.Figure:
    """v: hist_x, hist_y, fc_x, expected, low, high, unit, y_title, x_title, divider, hist_tips, fc_tips, dated.

    The expected line and the band start at the last real value, so the future visibly grows out of the past."""
    hist_c, fc_c = T.chart_color("history"), T.chart_color("forecast")
    last_x, last_y = v["hist_x"][-1], v["hist_y"][-1]
    xs = [last_x] + list(v["fc_x"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[last_y] + list(v["high"]) + list(v["low"])[::-1] + [last_y],
                             fill="toself", mode="lines", fillcolor=_rgba(fc_c, 0.16), line=dict(width=0), hoverinfo="skip",
                             name=C.LEGEND_RANGE, legendrank=3))
    if v.get("low50") is not None:
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[last_y] + list(v["high50"]) + list(v["low50"])[::-1] + [last_y],
                                 fill="toself", mode="lines", fillcolor=_rgba(fc_c, 0.30), line=dict(width=0),
                                 hoverinfo="skip", name=C.LEGEND_RANGE_50, legendrank=3))
    fig.add_trace(go.Scatter(x=list(v["hist_x"]), y=list(v["hist_y"]), name=C.LEGEND_HAPPENED, mode="lines",
                             line=dict(color=hist_c, width=2.2 if len(v["hist_x"]) < 200 else 1.4),
                             customdata=v["hist_tips"], hovertemplate="%{customdata}<extra></extra>", legendrank=1))
    fig.add_trace(go.Scatter(x=xs, y=[last_y] + list(v["expected"]), name=C.LEGEND_EXPECT, mode="lines",
                             line=dict(color=fc_c, width=2.8, dash="dash"), customdata=[v["hist_tips"][-1]] + list(v["fc_tips"]),
                             hovertemplate="%{customdata}<extra></extra>", legendrank=2))
    end_text = LF.amount(v["expected"][-1], v["unit"])
    fig.add_trace(go.Scatter(x=[v["fc_x"][-1]], y=[v["expected"][-1]], mode="markers+text", marker=dict(color=fc_c, size=8),
                             text=[end_text], textposition="top left", textfont=dict(color=fc_c, size=13),
                             hoverinfo="skip", showlegend=False, name=C.LEGEND_EXPECT, legendrank=4))
    fig.add_shape(type="line", x0=last_x, x1=last_x, xref="x", y0=0, y1=1, yref="paper",
                  line=dict(color=T.tok("faint"), width=1, dash="dot"))
    fig.add_annotation(x=last_x, y=1, xref="x", yref="paper", text=f"<b>{v['divider']}</b>", showarrow=False,
                       xanchor="right", yanchor="top", xshift=-6, font=dict(color=T.tok("text"), size=12))
    fig.update_layout(template=T.template(), title=title or None, height=height, hovermode="closest",
                      margin=dict(l=16, r=24, t=48 if title else 24, b=64))
    lo = float(min(min(v["hist_y"]), min(v["low"])))
    hi = float(max(max(v["hist_y"]), max(v["high"])))
    pad = (hi - lo) * 0.06 or 1.0
    bottom = lo - pad
    if v["unit"] != "points" and lo >= 0:  # counts never go below zero: no negative ticks
        bottom = max(bottom, 0.0)
    vals, text = count_ticks(bottom, hi + pad, v["unit"])
    vals, text = zip(*[(a, b) for a, b in zip(vals, text) if a >= bottom - 1e-9]) if vals else ((), ())
    fig.update_yaxes(title=v.get("y_title") or None, tickmode="array", tickvals=list(vals), ticktext=list(text),
                     range=[bottom - (pad * 0.25 if bottom == 0 else 0), hi + pad * 1.6])
    first = v["hist_x"][0]
    span = v["fc_x"][-1] - first
    fig.update_xaxes(title=v.get("x_title") or None, range=[first - span * 0.01, v["fc_x"][-1] + span * 0.03])
    if v.get("dated"):
        fig.update_xaxes(tickformat=v.get("tickformat", "%b %Y"))
        shocks(fig, v["hist_x"][0], v["fc_x"][-1])
    time_controls(fig, list(v["hist_x"]) + list(v["fc_x"]), bool(v.get("dated")), v.get("grain"))
    return fig


RANK_ROWS = 8  # approaches shown before "Show every approach"


def past_check_chart(v: dict, height: int = 400) -> go.Figure:
    """What was predicted (dotted) next to what really happened (solid), with the range given at the time and a dot per
    held-back real value: inside the range (green) or outside it (amber)."""
    real_c, band_c, pred_c = T.chart_color("history"), T.chart_color("predicted"), T.chart_color("predicted")
    px = list(v["pred_x"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=px + px[::-1], y=list(v["high"]) + list(v["low"])[::-1], fill="toself", mode="lines",
                             fillcolor=_rgba(band_c, 0.14), line=dict(width=0), hoverinfo="skip",
                             name=C.LEGEND_RANGE_THEN, legendrank=3))
    fig.add_trace(go.Scatter(x=list(v["real_x"]), y=list(v["real_y"]), mode="lines", name=C.LEGEND_REAL,
                             line=dict(color=real_c, width=2.2 if len(v["real_x"]) < 200 else 1.4),
                             customdata=v["real_tips"], hovertemplate="%{customdata}<extra></extra>", legendrank=1))
    fig.add_trace(go.Scatter(x=px, y=list(v["pred_y"]), mode="lines", name=C.LEGEND_PREDICTED,
                             line=dict(color=pred_c, width=2.6, dash="dot"), hoverinfo="skip", legendrank=2))
    n_pre = v["n_pre"]
    act = list(v["real_y"])[n_pre:]
    for inside, name, col, rank in ((True, C.LEGEND_INSIDE, T.tok("good"), 4), (False, C.LEGEND_OUTSIDE, T.tok("warm"), 5)):
        idx = [i for i, ok in enumerate(v["inside"]) if bool(ok) == inside]
        if not idx:
            continue
        fig.add_trace(go.Scatter(x=[px[i] for i in idx], y=[act[i] for i in idx], mode="markers", name=name,
                                 marker=dict(color=col, size=7 if len(px) < 40 else 4, line=dict(width=0)),
                                 hoverinfo="skip", legendrank=rank))
    cut = px[0]
    fig.add_shape(type="line", x0=cut, x1=cut, xref="x", y0=0, y1=1, yref="paper",
                  line=dict(color=T.tok("faint"), width=1, dash="dot"))
    fig.add_annotation(x=cut, y=1, xref="x", yref="paper", text=f"<b>{C.PREDICTED_HERE}</b>", showarrow=False,
                       xanchor="right", yanchor="top", xshift=-6, font=dict(color=T.tok("text"), size=12))
    fig.update_layout(template=T.template(), height=height, hovermode="closest", margin=dict(l=16, r=24, t=24, b=64))
    lo = float(min(min(v["real_y"]), min(v["low"])))
    hi = float(max(max(v["real_y"]), max(v["high"])))
    pad = (hi - lo) * 0.06 or 1.0
    bottom = max(lo - pad, 0.0) if v["unit"] != "points" and lo >= 0 else lo - pad
    vals, text = count_ticks(bottom, hi + pad, v["unit"])
    keep = [(a, b) for a, b in zip(vals, text) if a >= bottom - 1e-9]
    fig.update_yaxes(title=v.get("y_title") or None, tickmode="array", tickvals=[a for a, _ in keep],
                     ticktext=[b for _, b in keep], range=[bottom - (pad * 0.25 if bottom == 0 else 0), hi + pad * 1.6])
    fig.update_xaxes(title=v.get("x_title") or None)
    if v.get("dated"):
        fig.update_xaxes(tickformat=v.get("tickformat", "%b %Y"))
    return fig


def _wrap(s: str, width: int = 30) -> str:
    import textwrap
    return "<br>".join(textwrap.wrap(s, width)) or s


def ranking_chart(rk, unit: str, show_all: bool = False) -> go.Figure:
    """Horizontal bars of average miss, closest at the top; the approach used in accent, the simple yardstick in amber."""
    rows = rk if show_all else rk[(rk.index < RANK_ROWS) | rk["reference"] | rk["chosen"]]
    labels, colors, texts = [], [], []
    for r in rows.itertuples():
        tag = f" ({C.RANK_USED})" if r.chosen else f" ({C.RANK_REFERENCE})" if r.reference else ""
        labels.append(_wrap(r.label + tag))
        colors.append(T.tok("accent") if r.chosen else T.tok("warm") if r.reference else T.tok("neutral-bar"))
        texts.append(f"{r.average_miss:.2f}" if unit == "points" else LF.amount(r.average_miss, unit))  # small gaps show
    fig = go.Figure(go.Bar(x=list(rows["average_miss"]), y=labels, orientation="h", marker=dict(color=colors),
                           text=texts, textposition="outside", cliponaxis=False,
                           customdata=[f"{lab.replace('<br>', ' ')}: {t} {unit}" for lab, t in zip(labels, texts)],
                           hovertemplate="%{customdata}<extra></extra>", name=C.RANK_TITLE, showlegend=False))
    fig.update_layout(template=T.template(), height=max(220, 44 * len(rows) + 70), margin=dict(l=16, r=72, t=16, b=48),
                      bargap=0.32, hovermode="closest")
    fig.update_yaxes(autorange="reversed", automargin=True, tickfont=dict(size=12))
    top = float(rows["average_miss"].max())
    vals, text = count_ticks(0.0, top, unit, 4)
    keep = [(a, b) for a, b in zip(vals, text) if a >= 0]
    fig.update_xaxes(title=C.AXIS_MISS.format(unit=unit), tickmode="array", tickvals=[a for a, _ in keep],
                     ticktext=[b for _, b in keep], range=[0, top * 1.18], showgrid=True)
    return fig


def _count_axis(fig: go.Figure, values, unit: str, title: str | None) -> None:
    lo, hi = float(min(values)), float(max(values))
    pad = (hi - lo) * 0.06 or 1.0
    bottom = max(lo - pad, 0.0) if unit != "points" and lo >= 0 else lo - pad
    vals, text = count_ticks(bottom, hi + pad, unit)
    keep = [(a, b) for a, b in zip(vals, text) if a >= bottom - 1e-9]
    fig.update_yaxes(title=title or None, tickmode="array", tickvals=[a for a, _ in keep], ticktext=[b for _, b in keep],
                     range=[bottom - (pad * 0.25 if bottom == 0 else 0), hi + pad * 1.6])


def data_chart(v: dict, height: int = 400) -> go.Figure:
    """Every real value used (solid), with Phase 1's unusual points and the known outage marked."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(v["x"]), y=list(v["y"]), mode="lines", name=C.LEGEND_HAPPENED,
                             line=dict(color=T.chart_color("history"), width=2 if len(v["x"]) < 400 else 1.1),
                             customdata=v["tips"], hovertemplate="%{customdata}<extra></extra>", legendrank=1))
    if v["unusual_x"]:
        fig.add_trace(go.Scatter(x=list(v["unusual_x"]), y=list(v["unusual_y"]), mode="markers", name=C.MARK_UNUSUAL,
                                 marker=dict(color=T.tok("warm"), size=7 if len(v["unusual_x"]) < 50 else 4),
                                 customdata=v["unusual_tips"], hovertemplate="%{customdata}<extra></extra>", legendrank=2))
    if v["outage_x"]:
        fig.add_trace(go.Scatter(x=list(v["outage_x"]), y=list(v["outage_y"]), mode="markers", name=C.MARK_OUTAGE,
                                 marker=dict(color=T.tok("accent"), size=9 if len(v["outage_x"]) < 5 else 4, symbol="x"),
                                 hoverinfo="skip", legendrank=3))
    fig.update_layout(template=T.template(), height=height, hovermode="closest", margin=dict(l=16, r=24, t=24, b=64))
    _count_axis(fig, v["y"], v["unit"], v.get("y_title"))
    fig.update_xaxes(title=v.get("x_title") or None)
    if v.get("dated"):
        shocks(fig, v["x"][0], v["x"][-1])
    time_controls(fig, list(v["x"]), bool(v.get("dated")), v.get("grain"))
    return fig


def pattern_chart(p: dict, height: int = 320) -> go.Figure:
    """Average of the real values in each place of the repeating cycle (hour of day, day of week, month, quarter)."""
    texts = [LF.amount(x, p["unit"]) for x in p["values"]]
    fig = go.Figure(go.Bar(x=list(p["labels"]), y=list(p["values"]), marker=dict(color=T.tok("accent")),
                           customdata=[f"{lab}: {t} {p['unit']}" for lab, t in zip(p["labels"], texts)],
                           hovertemplate="%{customdata}<extra></extra>", name=p["title"], showlegend=False))
    fig.update_layout(template=T.template(), height=height, margin=dict(l=16, r=16, t=24, b=56), hovermode="closest")
    _count_axis(fig, list(p["values"]) + [0.0] if p["unit"] != "points" else p["values"], p["unit"], None)
    fig.update_xaxes(type="category", title=p.get("x_title") or None)  # Plotly tilts labels itself when space is short
    return fig


def history_forecast(d: dict, title: str = "", height: int = 360, y_title: str = "") -> go.Figure:
    """The Welcome chart. d: output of logic_forecasts.hosting_hero (dates and values of history, expected, range)."""
    tips_h = [f"{LF.month_year(x)}: {LF.level(y)}" for x, y in zip(d["hist_dates"], d["hist_values"])]
    tips_f = [f"{LF.month_year(x)}: " + C.HOVER_EXPECT.format(value=LF.level(e), low=LF.level(lo), high=LF.level(hi))
              for x, e, lo, hi in zip(d["fc_dates"], d["expected"], d["low"], d["high"])]
    v = {"hist_x": d["hist_dates"], "hist_y": d["hist_values"], "fc_x": d["fc_dates"], "expected": d["expected"],
         "low": d["low"], "high": d["high"], "unit": "points", "y_title": y_title, "divider": C.TODAY,
         "hist_tips": tips_h, "fc_tips": tips_f, "dated": True}
    fig = series_chart(v, height, title)
    fig.update_xaxes(dtick="M12")
    return fig
