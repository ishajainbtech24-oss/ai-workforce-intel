"""Analyst-mode charts: decomposition, autocorrelation, residual checks, error by horizon and interval coverage.
Plain titles, theme colours, values from artifacts/ only."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.ui import copy_technical as CT
from dashboard.ui import theme as T
from dashboard.ui.charts import _rgba


def _layout(fig: go.Figure, height: int, title: str | None = None) -> go.Figure:
    fig.update_layout(template=T.template(), height=height, title=title, hovermode="x unified",
                      margin=dict(l=16, r=16, t=48 if title else 24, b=40), showlegend=False)
    return fig


def stl_chart(d: pd.DataFrame, dated: bool) -> go.Figure:
    """Four stacked panels: the series, its trend, its repeating pattern and what is left over."""
    x = pd.to_datetime(d["x"]) if dated else d["x"]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=CT.STL_PANELS)
    colours = (T.chart_color("history"), T.tok("accent"), T.tok("accent-2"), T.tok("muted"))
    for i, (col, c) in enumerate(zip(("value", "trend", "seasonal", "remainder"), colours), 1):
        fig.add_trace(go.Scatter(x=x, y=d[col], mode="lines", line=dict(color=c, width=1.4), name=CT.STL_PANELS[i - 1]), i, 1)
    for a in fig.layout.annotations:
        a.update(font=dict(size=12, color=T.tok("muted")), x=0, xanchor="left")
    return _layout(fig, 560)


def correlogram(values: list[float], band: float, title: str, partial: bool = False) -> go.Figure:
    """Bars at each lag with the ±band line (about 95% for no correlation)."""
    lags = list(range(1, len(values)))
    vals = list(values[1:])
    fig = go.Figure(go.Bar(x=lags, y=vals, marker_color=[T.tok("accent") if abs(v) > band else T.tok("faint") for v in vals],
                           name=title, hovertemplate=f"{CT.LAG} %{{x}}: %{{y:.2f}}<extra></extra>"))
    for s in (band, -band):
        fig.add_hline(y=s, line=dict(color=T.tok("marigold"), width=1, dash="dash"))
    fig.update_xaxes(title=CT.LAG)
    fig.update_yaxes(title=CT.PACF_AXIS if partial else CT.ACF_AXIS, range=[-1.05, 1.05])
    return _layout(fig, 260, title)


def subseries(d: pd.DataFrame, period: int, dated: bool) -> go.Figure:
    """Average of each position in the cycle (month of year, day of week, hour of day) with its spread."""
    v = d["value"].to_numpy()
    if dated:
        pos = pd.to_datetime(d["x"]).dt.month.to_numpy() if period == 12 else pd.to_datetime(d["x"]).dt.quarter.to_numpy()
    else:
        pos = (np.arange(len(v)) % period) + 1
    g = pd.DataFrame({"pos": pos, "v": v}).groupby("pos")["v"].agg(["mean", "min", "max"]).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["pos"], y=g["max"], mode="lines", line=dict(width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g["pos"], y=g["min"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(T.tok("accent"), 0.14), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g["pos"], y=g["mean"], mode="lines+markers", line=dict(color=T.tok("accent"), width=2),
                             name=CT.SUBSERIES_MEAN, hovertemplate="%{x}: %{y:,.2f}<extra></extra>"))
    fig.update_xaxes(title=CT.CYCLE_POS, dtick=1)
    return _layout(fig, 280, CT.SUBSERIES_TITLE)


def residual_line(values: list[float]) -> go.Figure:
    fig = go.Figure(go.Scatter(x=list(range(1, len(values) + 1)), y=values, mode="lines+markers",
                               line=dict(color=T.tok("accent"), width=1.4), marker=dict(size=4),
                               hovertemplate="%{x}: %{y:,.3f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=T.tok("faint"), width=1, dash="dot"))
    fig.update_xaxes(title=CT.FOLD_AXIS)
    fig.update_yaxes(title=CT.ERROR_AXIS)
    return _layout(fig, 260, CT.RESID_TITLE)


def qq(points: dict) -> go.Figure:
    t, s = np.asarray(points["theoretical"]), np.asarray(points["sample"])
    fig = go.Figure(go.Scatter(x=t, y=s, mode="markers", marker=dict(color=T.tok("accent"), size=6),
                               hovertemplate="%{x:.2f}, %{y:.3f}<extra></extra>"))
    if len(t) > 1:
        slope, icpt = np.polyfit(t, s, 1)
        fig.add_trace(go.Scatter(x=[t.min(), t.max()], y=[icpt + slope * t.min(), icpt + slope * t.max()], mode="lines",
                                 line=dict(color=T.tok("marigold"), dash="dash"), hoverinfo="skip"))
    fig.update_xaxes(title=CT.QQ_X)
    fig.update_yaxes(title=CT.QQ_Y)
    return _layout(fig, 260, CT.QQ_TITLE)


def horizon_chart(h: pd.DataFrame, chosen: str, labels: dict) -> go.Figure:
    """Typical miss (MASE) by how far ahead, the chosen approach in colour, others faint."""
    fig = go.Figure()
    for model, g in h.groupby("model"):
        mine = model == chosen
        fig.add_trace(go.Scatter(x=g["step"], y=g["mase"], mode="lines+markers", name=labels.get(model, model),
                                 line=dict(color=T.tok("accent") if mine else T.tok("faint"), width=2.6 if mine else 1),
                                 marker=dict(size=5 if mine else 3), opacity=1 if mine else 0.55,
                                 hovertemplate=f"{labels.get(model, model)}: %{{y:.2f}}<extra></extra>"))
    fig.add_hline(y=1, line=dict(color=T.tok("marigold"), width=1, dash="dash"),
                  annotation_text=CT.MASE_ONE, annotation_position="top left",
                  annotation_font=dict(color=T.tok("muted"), size=12))
    fig.update_xaxes(title=CT.STEP_AXIS, dtick=1)
    fig.update_yaxes(title="MASE", rangemode="tozero")
    return _layout(fig, 320, CT.HORIZON_TITLE)


def coverage_chart(cov: dict) -> go.Figure:
    """Nominal vs. real coverage of the calibrated ranges: on the diagonal means honest ranges."""
    lv = sorted(float(k) for k in cov)
    real = [cov[str(k)] if str(k) in cov else cov[f"{k}"] for k in lv]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0.4, 1], y=[0.4, 1], mode="lines", line=dict(color=T.tok("faint"), dash="dot"),
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=lv, y=real, mode="lines+markers", line=dict(color=T.tok("accent"), width=2.2),
                             marker=dict(size=8), hovertemplate=f"{CT.NOMINAL} %{{x:.0%}} → {CT.REAL} %{{y:.0%}}<extra></extra>"))
    fig.update_xaxes(title=CT.NOMINAL, tickformat=".0%", range=[0.4, 1])
    fig.update_yaxes(title=CT.REAL, tickformat=".0%", range=[0, 1.02])
    return _layout(fig, 300, CT.COVERAGE_TITLE)
