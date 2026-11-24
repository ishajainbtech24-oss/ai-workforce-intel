"""Plotly figure builders. Every title, axis and hover label is plain language from copy.py.

Colours and fonts come from the current theme (theme.template(), theme.outlook_color()); money axes use the
same rupee format as the cards ("-₹2 Cr", "₹50 L"), so the reader sees one style everywhere. The plotted values
stay in dollars as saved; tick positions are chosen as round rupee amounts and labels and hover text are rupees.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard import copy as C
from dashboard import currency as CUR
from dashboard import theme as T


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def money_ticks(lo: float, hi: float, n: int = 5) -> tuple[list[float], list[str]]:
    """Tick positions (in the plotted dollar units) at round rupee amounts covering [lo, hi], always including 0
    when inside, and their rupee labels."""
    r = CUR.rate()
    lo, hi = lo * r, hi * r
    span = (hi - lo) or abs(hi) or 1.0
    raw = span / n
    mag = 10 ** np.floor(np.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    vals = list(np.arange(np.floor(lo / step) * step, hi + step * 0.999, step))
    vals = [float(round(v, 6)) for v in vals]
    return [v / r for v in vals], [CUR.tick(v) for v in vals]


def _money_axis(fig: go.Figure, values, axis: str = "y", pad: float = 0.06, n: int = 5) -> None:
    v = np.asarray([float(x) for x in values if np.isfinite(x)])
    lo, hi = float(v.min()), float(v.max())
    span = (hi - lo) or abs(hi) or 1.0
    vals, text = money_ticks(lo, hi, n)
    rng = [min(lo - span * pad, vals[0]), max(hi + span * pad, vals[-1])]
    upd = dict(tickmode="array", tickvals=vals, ticktext=text, range=rng)
    (fig.update_yaxes if axis == "y" else fig.update_xaxes)(**upd)


def _base(title: str, height: int = 380) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(template=T.template(), title=title, height=height, hovermode="x unified")
    fig.update_xaxes(title="Month", dtick=1)
    return fig


def _zero_line(fig: go.Figure) -> None:
    fig.add_hline(y=0, line=dict(color=T.tok("faint"), width=1, dash="dot"), annotation_text=C.ZERO_LINE,
                  annotation_position="top left", annotation_font=dict(color=T.tok("muted"), size=12))


def running_balance(series: dict, show_range: bool, horizon: int, paybacks: dict | None = None,
                    focus: str = "expected") -> go.Figure:
    """series: outlook -> DataFrame(month, p10, p50, p90) of the running balance. `focus` is drawn strongest."""
    fig = _base(C.OVERVIEW_CHART_TITLE, 440)
    allv = []
    for sc, df in series.items():
        col, name = T.outlook_color(sc), C.OUTLOOK[sc]
        strong = sc == focus
        if show_range:
            fig.add_trace(go.Scatter(x=np.r_[df["month"], df["month"][::-1]], y=np.r_[df["p90"], df["p10"][::-1]],
                                     fill="toself", fillcolor=_rgba(col, 0.16 if strong else 0.07), line=dict(width=0),
                                     hoverinfo="skip", showlegend=False, name=f"{name} likely range"))
            allv += list(df["p90"]) + list(df["p10"])
        fig.add_trace(go.Scatter(x=df["month"], y=df["p50"], name=name, mode="lines", line_shape="spline",
                                 line=dict(color=col, width=3.5 if strong else 2.2), opacity=1 if strong else 0.55,
                                 customdata=[T.money(v) for v in df["p50"]],
                                 hovertemplate=f"{name}: %{{customdata}}<extra></extra>"))
        allv += list(df["p50"])
    lo_df = series.get(focus)
    if lo_df is not None:
        i = int(np.argmin(lo_df["p50"].to_numpy()))
        x, y = float(lo_df["month"].iloc[i]), float(lo_df["p50"].iloc[i])
        if y < 0:
            fig.add_annotation(x=x, y=y, text=C.LOWEST_POINT.format(value=T.money(y)), showarrow=True, arrowhead=0,
                               ax=0, ay=36, font=dict(size=12, color=T.tok("text")), bgcolor=T.tok("hover-bg"),
                               bordercolor=T.tok("border-strong"), borderpad=5, arrowcolor=T.tok("faint"))
    for sc, pb in (paybacks or {}).items():
        if pb is None or not np.isfinite(pb) or sc not in series:
            continue
        df, col, name = series[sc], T.outlook_color(sc), C.OUTLOOK[sc]
        y = float(np.interp(pb, df["month"], df["p50"]))
        fig.add_trace(go.Scatter(x=[pb], y=[y], mode="markers", meta="pays", showlegend=False, name=f"{name} pays for itself",
                                 marker=dict(size=14, color=col, line=dict(color=T.tok("surface-solid"), width=3)),
                                 hovertemplate=C.PAYS_MARK.format(month=int(pb)) + f" ({name})<extra></extra>"))
        fig.add_annotation(x=pb, y=y, text=C.PAYS_MARK.format(month=int(pb)), showarrow=True, arrowhead=0, ax=-60, ay=-36,
                           font=dict(size=12, color=col), bgcolor=T.tok("hover-bg"), bordercolor=_rgba(col, 0.5),
                           borderpad=5, arrowcolor=_rgba(col, 0.6))
    _zero_line(fig)
    _money_axis(fig, allv + [0.0])
    fig.update_yaxes(title=C.AXIS_BALANCE)
    fig.update_xaxes(range=[0.7, horizon + 0.3])
    return fig


def year_end_bars(items: list[dict]) -> go.Figure:
    """The plain 2D version of the 3D 'money flow' columns (same values)."""
    fig = go.Figure(go.Bar(x=[C.OUTLOOK_SHORT.get(d["key"], d["label"]) for d in items], y=[d["value"] for d in items],
                           marker=dict(color=[T.outlook_color(d["key"]) for d in items]),
                           text=[d["text"] for d in items], textposition="outside", cliponaxis=False,
                           customdata=[d["text"] for d in items], hovertemplate="%{x}: %{customdata}<extra></extra>"))
    fig.update_layout(template=T.template(), title=C.FLOW_FLAT_TITLE, height=380, showlegend=False,
                      margin=dict(l=16, r=16, t=56, b=40), hovermode="closest")
    _money_axis(fig, [d["value"] for d in items] + [0.0], pad=0.18)
    fig.update_yaxes(title=C.AXIS_AMOUNT)
    fig.add_hline(y=0, line=dict(color=T.tok("faint"), width=1, dash="dot"))
    fig.update_xaxes(showgrid=False)
    return fig


def cost_stack(lines: dict) -> go.Figure:
    """lines: engine line name -> DataFrame(month, p50)."""
    fig = _base(C.COST_STACK_TITLE)
    tot = None
    for ln, df in lines.items():
        name = f"{C.LINE[ln]} ({C.LINE_TAG[ln]})"
        fig.add_trace(go.Bar(x=df["month"], y=df["p50"], name=name, marker=dict(color=T.line_color(ln), line=dict(width=0), pattern=T.line_pattern(ln)),
                             customdata=[T.money(v) for v in df["p50"]],
                             hovertemplate=f"{C.LINE[ln]}: %{{customdata}}<extra></extra>"))
        tot = df["p50"].to_numpy() if tot is None else tot + df["p50"].to_numpy()
    fig.update_layout(barmode="stack", bargap=0.3, legend=dict(y=-0.3))  # clear of the month label when the legend is one row
    _money_axis(fig, list(tot if tot is not None else [0.0]) + [0.0])
    fig.update_yaxes(title=C.AXIS_COST_MONTH)
    return fig


def _slice_labels(values) -> list[str]:
    """Whole-percent labels; slices under 3% get no label (their share is in the hover text)."""
    v = np.asarray(values, dtype=float)
    p = v / v.sum() if v.sum() > 0 else v
    return [f"{x:.0%}" if x >= 0.03 else "" for x in p]


def donut(shares: pd.DataFrame) -> go.Figure:
    """shares: line, p50_total, type."""
    fig = go.Figure(go.Pie(labels=[f"{C.LINE[l]} ({C.TYPE_TAG[t]})" for l, t in zip(shares["line"], shares["type"])],
                           values=shares["p50_total"], hole=0.64, sort=False,
                           marker=dict(colors=[T.line_color(l) for l in shares["line"]],
                                       line=dict(color=T.tok("surface-solid"), width=3),
                                       pattern=dict(shape=[T.LINE_PATTERNS.get(l, "") for l in shares["line"]],
                                                    fillmode="overlay", fgcolor=T.tok("surface-solid"), fgopacity=0.55,
                                                    solidity=0.25, size=7)),
                           customdata=[T.money(v) for v in shares["p50_total"]],
                           hovertemplate="%{label}<br>%{customdata} (%{percent})<extra></extra>",
                           texttemplate=_slice_labels(shares["p50_total"]), textposition="inside"))
    fig.update_layout(template=T.template(), title=C.DONUT_TITLE, height=420, showlegend=True,
                      legend=dict(orientation="h", yanchor="top", y=-0.05, x=0))
    return fig


def benefit_vs_cost(cost: pd.DataFrame, benefit: pd.DataFrame, color: str) -> go.Figure:
    fig = _base(C.BENEFIT_COST_TITLE)
    fig.add_trace(go.Bar(x=cost["month"], y=cost["p50"], name="Cost", marker_color=T.tok("neutral-bar"),
                         customdata=[T.money(v) for v in cost["p50"]], hovertemplate="Cost: %{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=benefit["month"], y=benefit["p50"], name="Estimated benefit", mode="lines",
                             line=dict(color=color, width=3.5), line_shape="spline", fill="tozeroy", fillcolor=_rgba(color, 0.10),
                             customdata=[T.money(v) for v in benefit["p50"]],
                             hovertemplate="Estimated benefit: %{customdata}<extra></extra>"))
    _money_axis(fig, list(cost["p50"]) + list(benefit["p50"]) + [0.0])
    fig.update_yaxes(title=C.AXIS_AMOUNT)
    return fig


def payback_bars(counts: list[int], none: int, total: int, horizon: int, color: str) -> go.Figure:
    labels = [str(m) for m in range(1, horizon + 1)] + [C.NOT_WITHIN.format(months=horizon).replace(" ", "<br>", 2)]
    shares = [c / total for c in counts] + [none / total]
    colors = [color] * horizon + [T.outlook_color("downside")]
    names = [C.MONTH.format(month=m) for m in range(1, horizon + 1)] + [C.NOT_WITHIN.format(months=horizon)]
    fig = go.Figure(go.Bar(x=labels, y=shares, marker_color=colors, customdata=names,
                           text=[f"{s:.0%}" if s >= 0.005 else "" for s in shares], textposition="outside", cliponaxis=False,
                           textfont=dict(color=T.tok("muted"), size=12),
                           hovertemplate="%{customdata}: %{y:.0%} of futures<extra></extra>"))
    fig.update_layout(template=T.template(), title=C.TIMING_CHART_TITLE, height=380, bargap=0.25,
                      margin=dict(l=16, r=34, t=56, b=70), hovermode="closest")
    fig.update_xaxes(title=C.TIMING_AXIS_X, type="category", tickangle=0, tickfont=dict(size=11))
    fig.update_yaxes(title=C.TIMING_AXIS_Y, tickformat=".0%", rangemode="tozero", range=[0, 1.12])
    return fig


def payback_dots(rows: list[dict]) -> go.Figure:
    """One row per outlook: a dot at the typical month it pays for itself, or in the 'not within' column."""
    horizon = rows[0]["horizon"] if rows else 12
    none_x = horizon + 1.4
    fig = go.Figure()
    for r in rows:
        x = r["month"] if r["month"] is not None else none_x
        text = C.MONTH.format(month=int(round(r["month"]))) if r["month"] is not None else C.DOT_NONE.format(months=horizon)
        fig.add_trace(go.Scatter(x=[x], y=[r["label"]], mode="markers+text", name=r["label"],
                                 marker=dict(color=T.outlook_color(r["key"]), size=16, line=dict(width=0)),
                                 text=[text], textposition="middle left" if r["month"] is None else "middle right",
                                 textfont=dict(color=T.tok("muted"), size=12), cliponaxis=False,
                                 customdata=[r["tip"]], hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    fig.add_vline(x=horizon + 0.7, line=dict(color=T.tok("border-strong"), width=1, dash="dot"))
    fig.update_layout(template=T.template(), height=90 + 52 * len(rows), margin=dict(l=16, r=40, t=16, b=48),
                      hovermode="closest")
    ticks = list(range(1, horizon + 1, 1 if horizon <= 12 else 2))
    fig.update_xaxes(title=C.TIMING_AXIS_X, tickmode="array", tickvals=ticks + [none_x],
                     ticktext=[str(t) for t in ticks] + [C.NOT_WITHIN.format(months=horizon).replace(" ", "<br>", 2)],
                     range=[0.4, none_x + 0.9], tickangle=0, tickfont=dict(size=11))
    fig.update_yaxes(autorange="reversed", automargin=True)
    return fig


def levers(sens: pd.DataFrame) -> go.Figure:
    """Change in the year-end balance when each choice is 20% lower / higher."""
    s = sens.iloc[::-1]
    base = float(s["base_median_cum_net_T"].iloc[0])
    names = [C.LEVER.get(i, i) for i in s["input"]]
    fig = go.Figure()
    for col, label, color, direction in (("median_cum_net_T_low", C.LEVER_LOW, T.outlook_color("downside"), "20% lower"),
                                         ("median_cum_net_T_high", C.LEVER_HIGH, T.tok("accent"), "20% higher")):
        fig.add_trace(go.Bar(y=names, x=s[col] - base, orientation="h", name=label, marker_color=color,
                             customdata=np.stack([[T.money(v) for v in s[col]]], axis=-1),
                             hovertemplate=C.LEVER_TIP.format(direction=direction, value="%{customdata[0]}")
                             + "<extra></extra>"))
    fig.update_layout(template=T.template(), title=C.LEVERS_CHART_TITLE, barmode="overlay", height=460, legend=dict(y=-0.3),
                      hovermode="closest", bargap=0.35)
    allx = list(s["median_cum_net_T_low"] - base) + list(s["median_cum_net_T_high"] - base) + [0.0]
    _money_axis(fig, allx, axis="x", n=2)  # three short ticks fit a phone
    fig.update_xaxes(tickangle=0)
    fig.update_layout(margin=dict(r=36))  # room for the last tick label at tablet width
    fig.update_xaxes(title=C.AXIS_CHANGE)
    fig.update_yaxes(automargin=True, showgrid=False)
    fig.add_vline(x=0, line=dict(color=T.tok("faint"), width=1))
    return fig


def balance_band(cum: np.ndarray, color: str, title: str) -> go.Figure:
    """Running balance (typical case and likely range) of a live run."""
    m = np.arange(1, cum.shape[1] + 1)
    p10, p50, p90 = np.percentile(cum, [10, 50, 90], axis=0)
    fig = _base(title, 380)
    fig.add_trace(go.Scatter(x=np.r_[m, m[::-1]], y=np.r_[p90, p10[::-1]], fill="toself", fillcolor=_rgba(color, 0.16),
                             line=dict(width=0), hoverinfo="skip", name="Likely range"))
    fig.add_trace(go.Scatter(x=m, y=p50, name="Typical case", mode="lines", line_shape="spline", line=dict(color=color, width=3.5),
                             customdata=[T.money(v) for v in p50], hovertemplate="Typical case: %{customdata}<extra></extra>"))
    _zero_line(fig)
    _money_axis(fig, list(p10) + list(p90) + [0.0])
    fig.update_yaxes(title=C.AXIS_BALANCE)
    return fig


def text_of(fig: go.Figure) -> str:
    """All visible text of a figure (titles, axis titles, trace names, hover templates) for the wording test."""
    parts = [str(fig.layout.title.text or "")]
    for ax in (fig.layout.xaxis, fig.layout.yaxis):
        parts.append(str(ax.title.text or ""))
        parts += [str(t) for t in (ax.ticktext or [])]
    for tr in fig.data:
        parts += [str(getattr(tr, "name", "") or ""), str(getattr(tr, "hovertemplate", "") or "")]
        if isinstance(tr, (go.Pie,)):
            parts += [str(x) for x in tr.labels]
        if isinstance(tr, go.Bar) and tr.orientation == "h":
            parts += [str(y) for y in tr.y]
    parts += [str(a.text or "") for a in fig.layout.annotations]
    return " ".join(parts)
