"""Phase 4 figures. 'Agg', 150 dpi, Okabe-Ito palette, USD axes, closed after saving.

Every title carries `tag` ("illustrative example company" when the inputs are illustrative).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import EngFormatter  # noqa: E402

import config_phase4 as P4  # noqa: E402
from tsaf.plots import OKABE, _style  # noqa: E402
from tsaf.plots_phase2 import _save  # noqa: E402

BLUE, ORANGE, GREEN, PINK, SKY, VERMILION = OKABE[0], OKABE[1], OKABE[2], OKABE[3], OKABE[4], OKABE[5]
LINE_COLOR = {"token_expenditure": SKY, "hosting": BLUE, "enablement": ORANGE, "integration": PINK}
SC_COLOR = {"downside": VERMILION, "expected": BLUE, "optimistic": GREEN}
USD = EngFormatter(unit="", sep="")


def _usd(ax, axis="y") -> None:
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(USD)


def cost_stack(res, scenario: str, tag: str, path: Path) -> Path:
    """Monthly P50 cost by line item (stacked) and the P10-P90 band of total cost."""
    _style(False)
    T = res.total_cost.shape[1]
    m = np.arange(1, T + 1)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    bottom = np.zeros(T)
    for ln in P4.LINES:
        med = np.median(res.lines[ln], axis=0)
        ax.bar(m, med, bottom=bottom, color=LINE_COLOR[ln], edgecolor="white", linewidth=1,
               label=f"{P4.LINE_LABEL[ln]} ({P4.LINE_TYPE[ln]})")
        bottom += med
    lo, hi = np.percentile(res.total_cost, [10, 90], axis=0)
    ax.fill_between(m, lo, hi, color="#222222", alpha=0.12, step="mid", label="total cost P10-P90")
    ax.set(xlabel="month", ylabel="cost per month (USD)", title=f"Monthly cost by line item, {scenario} scenario ({tag})")
    _usd(ax)
    ax.legend(fontsize=8, loc="upper right")
    return _save(fig, path)


def cumulative_net(res, scenario: str, tag: str, path: Path, n_paths: int = P4.FAN_PATHS) -> Path:
    """Fan chart of cumulative net with the zero line and the break-even range shaded."""
    _style(False)
    T = res.cum_net.shape[1]
    m = np.arange(1, T + 1)
    p10, p50, p90 = np.percentile(res.cum_net, [10, 50, 90], axis=0)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for i in range(min(n_paths, len(res.cum_net))):
        ax.plot(m, res.cum_net[i], color="#8C8C8C", lw=0.5, alpha=0.5, label="sample draws" if i == 0 else None)
    ax.fill_between(m, p10, p90, color=BLUE, alpha=0.2, label="P10-P90")
    ax.plot(m, p50, color=BLUE, lw=2, label="median (P50)")
    ax.axhline(0, color="#222222", lw=1)
    be = res.break_even[np.isfinite(res.break_even)]
    share = len(be) / len(res.break_even)
    if len(be):
        lo, hi = np.percentile(be, [10, 90])
        ax.axvspan(lo - 0.5, hi + 0.5, color=GREEN, alpha=0.15, label=f"break-even P10-P90 (months {lo:.0f}-{hi:.0f})")
    ax.set(xlabel="month", ylabel="cumulative net (USD)",
           title=f"Cumulative net, {scenario} scenario ({tag})\nbreak-even within {T} months in {share:.0%} of draws")
    _usd(ax)
    ax.legend(fontsize=8, loc="best")
    return _save(fig, path)


def break_even_hist(res, scenario: str, tag: str, path: Path) -> Path:
    """Break-even months, with 'no break-even within T' as its own bar."""
    _style(False)
    T = res.cum_net.shape[1]
    be = res.break_even
    counts = [int((be == k).sum()) for k in range(1, T + 1)] + [int(np.isnan(be).sum())]
    labels = [str(k) for k in range(1, T + 1)] + [f"none\nwithin {T}"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.bar(range(len(counts)), counts, color=[BLUE] * T + [VERMILION], edgecolor="white")
    ax.set_xticks(range(len(counts)), labels, fontsize=8)
    ax.set(xlabel="break-even month", ylabel="number of draws",
           title=f"Break-even month over {len(be):,} draws, {scenario} scenario ({tag})")
    return _save(fig, path)


def scenario_compare(results: dict, tag: str, path: Path) -> Path:
    """P50 cumulative net (with P10-P90) for each scenario at multiplier 1.0."""
    _style(False)
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for sc, res in results.items():
        T = res.cum_net.shape[1]
        m = np.arange(1, T + 1)
        p10, p50, p90 = np.percentile(res.cum_net, [10, 50, 90], axis=0)
        ax.fill_between(m, p10, p90, color=SC_COLOR.get(sc, "#888"), alpha=0.15)
        ax.plot(m, p50, color=SC_COLOR.get(sc, "#888"), lw=2, label=f"{sc} (P50, band P10-P90)",
                ls={"downside": ":", "expected": "-", "optimistic": "--"}.get(sc, "-"))
    ax.axhline(0, color="#222222", lw=1)
    ax.set(xlabel="month", ylabel="cumulative net (USD)", title=f"Cumulative net by scenario, multiplier 1.0 ({tag})")
    _usd(ax)
    ax.legend(fontsize=8)
    return _save(fig, path)


def multiplier_effect(summ: dict, scenario: str, tag: str, path: Path, T: int = 12) -> Path:
    """Break-even range and cumulative net at T for each multiplier k (one scenario)."""
    _style(False)
    ks = sorted(summ)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6))
    for i, k in enumerate(ks):
        be, cn = summ[k]["break_even"], summ[k]["cum_net_T"]
        if be["prob_within_T"] > 0:
            a1.plot([be["p10"], be["p90"]], [i, i], color=BLUE, lw=6, solid_capstyle="butt")
            a1.plot(be["p50"], i, "o", color="#222222")
            txt = f"P(break-even) {be['prob_within_T']:.0%}"
        else:
            txt = f"no break-even within {T} months (P = 0%)"
        a1.text(0.02, i + 0.25, txt, fontsize=8, transform=a1.get_yaxis_transform())
        a2.plot([cn["p10"], cn["p90"]], [i, i], color=ORANGE, lw=6, solid_capstyle="butt")
        a2.plot(cn["p50"], i, "o", color="#222222")
        a2.text(0.02, i + 0.25, f"P10-P90 spread ${cn['p90'] - cn['p10']:,.0f}", fontsize=8,
                transform=a2.get_yaxis_transform())
    a1.set_xlim(0.5, T + 0.5)
    for ax in (a1, a2):
        ax.set_yticks(range(len(ks)), [f"k = {k:g}" for k in ks])
        ax.set_ylim(-0.6, len(ks) - 0.4)
    a1.set(xlabel="break-even month (P10-P90, dot = P50)", title="Break-even range")
    a2.set(xlabel="cumulative net at the horizon (USD, P10-P90)", title="Cumulative net at T")
    _usd(a2, "x")
    a2.axvline(0, color="#222222", lw=1)
    fig.suptitle(f"Effect of the uncertainty multiplier k, {scenario} scenario ({tag})", fontsize=11)
    return _save(fig, path)


def tornado(table: pd.DataFrame, tag: str, path: Path) -> Path:
    """Change in median cumulative net at T for each input at -20% / +20%."""
    _style(False)
    t = table.iloc[::-1]
    base = float(t["base_median_cum_net_T"].iloc[0])
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(t) + 1.8))
    ax.barh(y, t["median_cum_net_T_low"] - base, color=VERMILION, height=0.6, label="input -20%")
    ax.barh(y, t["median_cum_net_T_high"] - base, color=BLUE, height=0.6, label="input +20%")
    ax.set_yticks(y, t["input"])
    ax.axvline(0, color="#222222", lw=1)
    ax.set(xlabel="change in median cumulative net at T (USD)",
           title=f"Which inputs matter (illustrative +-20% stress range, not a measured uncertainty)\n{tag}")
    _usd(ax, "x")
    ax.legend(fontsize=8, loc="lower right")
    return _save(fig, path)


def cost_share_by_type(shares: dict, tag: str, path: Path) -> Path:
    """Share of total cost by evidence type (P50 totals)."""
    _style(False)
    fig, ax = plt.subplots(figsize=(7, 2.8))
    left = 0.0
    for typ, s in shares.items():
        ax.barh([0], [s], left=left, color=BLUE if typ == "Forecast-driven" else ORANGE, edgecolor="white",
                label=f"{typ} {s:.0%}")
        left += s
    ax.set_yticks([])
    ax.set_xlim(0, 1)
    ax.set(xlabel="share of total cost (P50 line totals)", title=f"Cost by evidence type ({tag})")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=2)
    return _save(fig, path)
