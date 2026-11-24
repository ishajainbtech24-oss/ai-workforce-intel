"""Phase 2 figures: leaderboard, hold-out forecast with intervals, residual checks, CV folds.

Same conventions as Phase 1 (tsaf.plots): 'Agg' backend, 150 dpi PNG, Okabe-Ito colour-blind
safe palette, titles and labelled axes with units, every figure closed after saving. Identity
is never colour alone: each series also has its own line style and a legend entry.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import EngFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.tsa.stattools import acf  # noqa: E402

from tsaf.plots import DPI, OKABE, _style  # noqa: E402

BLUE, ORANGE, GREEN, VERMILION, GREY, INK = OKABE[0], OKABE[1], OKABE[2], OKABE[5], "#8C8C8C", "#222222"


def _save(fig, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def _label(t) -> str:
    """Time label: date only for timestamps, the integer otherwise."""
    return str(t.date()) if isinstance(t, pd.Timestamp) else str(t)


def _axes_format(ax, x_is_date: bool) -> None:
    """Readable ticks: concise dates on the x axis, engineering notation (k, M) on the y axis."""
    if x_is_date:
        loc = mdates.AutoDateLocator(minticks=2, maxticks=4)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    ax.yaxis.set_major_formatter(EngFormatter(sep=""))


def _xlabel(cfg: dict) -> str:
    if cfg.get("source") == "burstgpt":
        return "hour since trace start" if cfg["grain"] == "hourly" else "day since trace start"
    return "date"


def plot_leaderboard(board: pd.DataFrame, chosen: str, name: str, path: Path) -> Path:
    """Horizontal bars of mean CV MASE; seasonal naive as a vertical line; chosen model highlighted."""
    _style(False)
    ok = board[(board["status"] == "ok") & np.isfinite(board["cv_mase"])].sort_values("cv_mase", ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, 0.32 * len(ok) + 1.6))
    colors = [BLUE if m == chosen else "#C9C9C9" for m in ok["model"]]
    ax.barh(ok["model"], ok["cv_mase"], color=colors, height=0.7, edgecolor="white", linewidth=1)
    sn = ok.loc[ok["model"] == "seasonal_naive", "cv_mase"]
    if len(sn):
        ax.axvline(float(sn.iloc[0]), color=VERMILION, ls="--", lw=1.5,
                   label=f"seasonal naive = {float(sn.iloc[0]):.3f}")
    for i, (m, v) in enumerate(zip(ok["model"], ok["cv_mase"])):
        if m in (chosen, "seasonal_naive"):
            ax.text(v, i, f" {v:.3f}", va="center", fontsize=8, color=INK)
    ax.barh([], [], color=BLUE, label=f"chosen: {chosen}")
    ax.set_xlabel("mean CV MASE (lower is better; < 1 beats in-sample seasonal naive)")
    ax.set_title(f"{name}: models ranked by rolling-origin CV MASE")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, path)


def _history_tail(pre: pd.Series, grain: str) -> pd.Series:
    return pre.iloc[-336:] if grain == "hourly" else pre


def plot_forecast(pre: pd.Series, test: pd.Series, fc: np.ndarray, sn_fc: np.ndarray | None,
                  hw: dict[int, np.ndarray] | None, cfg: dict, chosen: str, path: Path) -> Path:
    """History, hold-out actual, chosen forecast with 80%/95% intervals, seasonal naive."""
    _style(False)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    hist = _history_tail(pre, cfg["grain"])
    ax.plot(hist.index, hist.to_numpy(), color=INK, lw=1.2, label="history (before hold-out)")
    ax.plot(test.index, test.to_numpy(), color=INK, lw=1.6, marker="o", ms=3, ls="-",
            label="hold-out actual")
    if hw is not None:
        ax.fill_between(test.index, np.maximum(fc - hw[95], 0), fc + hw[95], color=BLUE, alpha=0.12,
                        lw=0, label="95% interval (empirical, from CV errors)")
        ax.fill_between(test.index, np.maximum(fc - hw[80], 0), fc + hw[80], color=BLUE, alpha=0.25,
                        lw=0, label="80% interval")
    ax.plot(test.index, fc, color=BLUE, lw=2, label=f"chosen model: {chosen}")
    if sn_fc is not None and chosen != "seasonal_naive":
        ax.plot(test.index, sn_fc, color=ORANGE, lw=1.6, ls="--", label="seasonal naive")
    ax.axvline(test.index[0], color=GREY, lw=1, ls=":")
    ax.set_title(f"{cfg['name']}: hold-out forecast ({len(test)} steps)")
    ax.set_xlabel(_xlabel(cfg))
    ax.set_ylabel(cfg["unit"])
    _axes_format(ax, isinstance(test.index, pd.DatetimeIndex))
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    note = "intervals: leave-one-fold-out |error| quantiles; steps beyond the CV horizon reuse its last step"
    fig.text(0.01, 0.01, note, fontsize=7, color="#555555")
    return _save(fig, path)


def plot_residuals(resid: pd.Series, cfg: dict, chosen: str, path: Path) -> Path:
    """Residuals over time, residual ACF, histogram and normal Q-Q plot."""
    _style(False)
    r = resid.dropna()
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    ax = axes[0, 0]
    ax.plot(r.index, r.to_numpy(), color=BLUE, lw=1)
    ax.axhline(0, color=GREY, lw=1)
    ax.set(title="in-sample residuals", xlabel=_xlabel(cfg), ylabel=f"residual ({cfg['unit']})")
    _axes_format(ax, isinstance(r.index, pd.DatetimeIndex))
    ax = axes[0, 1]
    nl = min(40, max(5, len(r) // 3))
    vals = acf(r, nlags=nl, fft=True)
    ax.vlines(range(1, nl + 1), 0, vals[1:], color=BLUE, lw=2)
    band = 1.96 / np.sqrt(len(r))
    ax.axhspan(-band, band, color=GREY, alpha=0.2, lw=0, label="95% band (white noise)")
    ax.axhline(0, color=GREY, lw=1)
    ax.set(title="residual ACF", xlabel="lag (steps)", ylabel="autocorrelation")
    ax.legend(fontsize=8)
    ax = axes[1, 0]
    ax.hist(r.to_numpy(), bins=min(30, max(8, len(r) // 5)), color=BLUE, edgecolor="white")
    ax.set(title="residual histogram", xlabel=f"residual ({cfg['unit']})", ylabel="count")
    ax = axes[1, 1]
    (osm, osr), (slope, icpt, _) = stats.probplot(r.to_numpy(), dist="norm")
    ax.plot(osm, osr, "o", ms=3, color=BLUE, label="residuals")
    ax.plot(osm, slope * osm + icpt, color=VERMILION, lw=1.5, ls="--", label="normal reference")
    ax.set(title="normal Q-Q plot", xlabel="theoretical quantile", ylabel="ordered residual")
    ax.legend(fontsize=8)
    fig.suptitle(f"{cfg['name']}: residual checks of the chosen model ({chosen}, fit before the hold-out)")
    return _save(fig, path)


def plot_cv_folds(pre: pd.Series, folds: pd.DataFrame, cfg: dict, chosen: str, path: Path) -> Path:
    """Small multiples of up to 4 folds (the last ones): recent training data, actual, forecast."""
    _style(False)
    ids = sorted(folds["fold"].unique())[-4:]
    fig, axes = plt.subplots(1, len(ids), figsize=(3.4 * len(ids), 3.4), sharey=True, squeeze=False)
    look = 72 if cfg["grain"] == "hourly" else 21
    for ax, k in zip(axes[0], ids):
        g = folds[folds["fold"] == k]
        o = int(g["origin_index"].iloc[0])
        tr = pre.iloc[max(0, o - look):o]
        ax.plot(tr.index, tr.to_numpy(), color=GREY, lw=1.2, label="training data (end)")
        ax.plot(g["time"], g["actual"], color=INK, lw=1.5, marker="o", ms=3, label="actual")
        ax.plot(g["time"], g["forecast"], color=BLUE, lw=2, ls="--", label=f"{chosen} forecast")
        ax.axvline(tr.index[-1], color=GREY, lw=1, ls=":")
        ax.set_title(f"fold {k} (train ends at {_label(tr.index[-1])})", fontsize=9)
        ax.set_xlabel(_xlabel(cfg))
        _axes_format(ax, isinstance(tr.index, pd.DatetimeIndex))
    axes[0, 0].set_ylabel(cfg["unit"])
    axes[0, 0].legend(fontsize=7, loc="best")
    fig.suptitle(f"{cfg['name']}: rolling-origin folds, chosen model {chosen}")
    return _save(fig, path)
