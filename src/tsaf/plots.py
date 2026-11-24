"""Phase 1 figures (syllabus Module 1: time plots, decomposition plots, correlograms).

Matplotlib with the non-interactive 'Agg' backend, 150 dpi PNG, the Okabe-Ito
colour-blind-safe palette, and every figure closed after saving.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OKABE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"]
FLAG_STYLE = {"copied_day": ("#E69F00", "copied days (excluded)"),
              "low_activity": ("#999999", "low-activity regime (excluded)"),
              "anomaly_low_day": ("#D55E00", "anomaly (kept, marked)"),
              "partial_day": ("#CC79A7", "partial day"),
              "missing_day": ("#CC79A7", "a model family has no data (excluded)")}
DPI = 150


def _style(fast: bool) -> None:
    plt.rcParams.update({"font.size": 9 if fast else 10, "axes.titlesize": 11,
                         "axes.grid": True, "grid.alpha": 0.3, "axes.prop_cycle":
                         matplotlib.cycler(color=OKABE)})


def _save(fig, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def _xlabel(cfg: dict) -> str:
    if cfg.get("source") == "burstgpt":
        return "hour since trace start" if cfg["grain"] == "hourly" else "day since trace start"
    return "date"


def _shade_flags(ax, flags: pd.DataFrame, step: float) -> None:
    """Shade runs of flagged points; one legend entry per flag type."""
    for col, (color, label) in FLAG_STYLE.items():
        if col not in flags or not flags[col].any():
            continue
        first = True
        for t in flags.index[flags[col].to_numpy()]:
            lo = t - step / 2 if not isinstance(t, pd.Timestamp) else t - pd.Timedelta(hours=12)
            hi = t + step / 2 if not isinstance(t, pd.Timestamp) else t + pd.Timedelta(hours=12)
            ax.axvspan(lo, hi, color=color, alpha=0.25, lw=0, label=label if first else None)
            first = False


def plot_series(full: pd.Series, s: pd.Series, flags: pd.DataFrame, cfg: dict, holdout: int,
                path: Path, fast: bool = False) -> Path:
    """Raw series: full trace in grey, modelling window in blue, flags shaded, hold-out marked."""
    _style(fast)
    fig, ax = plt.subplots(figsize=(8, 3.6) if fast else (11, 4.5))
    hourly = cfg["grain"] == "hourly"
    if len(full) > len(s):
        ax.plot(full.index, full.to_numpy(), color="#999999", lw=0.8, label="outside window")
    ax.plot(s.index, s.to_numpy(), color=OKABE[0], lw=0.7 if hourly else 1.4, label="modelling window")
    _shade_flags(ax, flags, step=1.0)
    ax.axvline(s.index[-holdout], color="#000000", ls="--", lw=1, label="hold-out starts")
    ax.set(title=f"{cfg['name']}: raw series (graphic trend = the eye-fitted line through it)",
           xlabel=_xlabel(cfg), ylabel=cfg["unit"])
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, path)


def plot_decomposition(comps: dict, cfg: dict, info: dict, path: Path, fast: bool = False) -> Path | None:
    """Trend, seasonal and remainder panels; classical and STL side by side when both exist."""
    if not comps:
        return None
    _style(fast)
    keys = [k for k in ("classical", "stl") if k in comps]
    fig, axes = plt.subplots(4, len(keys), figsize=((7 if fast else 11), 8), sharex=True, squeeze=False)
    titles = {"classical": f"classical ({info['classical']})",
              "stl": f"{info['method']} on {info['stl_scale']} scale"}
    hourly = cfg["grain"] == "hourly"
    for j, key in enumerate(keys):
        df = comps[key]
        for i, part in enumerate(["observed", "trend", "seasonal", "remainder"]):
            ax = axes[i, j]
            if part == "remainder":
                ax.plot(df.index, df[part], ".", ms=1.5 if hourly else 4, color=OKABE[5])
                ax.axhline(0 if key == "stl" or info["classical"] == "additive" else 1,
                           color="#000000", lw=0.8)
            else:
                ax.plot(df.index, df[part], lw=0.6 if hourly else 1.2, color=OKABE[i % 3])
            on_log = key == "stl" and info["stl_scale"] == "log"
            is_factor = (key == "classical" and info["classical"] == "multiplicative"
                         and part in ("seasonal", "remainder"))
            unit = "ratio" if is_factor else f"{'log ' if on_log else ''}{cfg['unit']}"
            ax.set_ylabel(f"{part}\n({unit})", fontsize=8)
            if i == 0:
                ax.set_title(titles[key])
        axes[-1, j].set_xlabel(_xlabel(cfg))
    fig.suptitle(f"{cfg['name']}: decomposition (seasonal strength {info['seasonal_strength']:.2f}, "
                 f"trend strength {info['trend_strength']:.2f})")
    return _save(fig, path)


def _correlogram(ax, lags, vals, band, title):
    ax.vlines(lags, 0, vals, color=OKABE[0], lw=1.5)
    ax.plot(lags, vals, "o", ms=3, color=OKABE[0])
    ax.axhspan(-band, band, color=OKABE[4], alpha=0.25, label="95% band")
    ax.axhline(0, color="#000000", lw=0.8)
    ax.set(title=title, xlabel="lag", ylabel="correlation", ylim=(-1.05, 1.05))
    ax.legend(loc="upper right", fontsize=8)


def plot_acf_pacf(orig: dict, diff: dict, diff_label: str, cfg: dict, path: Path,
                  fast: bool = False) -> Path:
    """2x2 grid: ACF and PACF of the original and of the differenced series."""
    _style(fast)
    fig, axes = plt.subplots(2, 2, figsize=(8, 5.5) if fast else (11, 7))
    for row, (res, lab) in enumerate([(orig, "original"), (diff, diff_label)]):
        _correlogram(axes[row, 0], res["lags"], res["acf"], res["band"], f"ACF, {lab} (n={res['n']})")
        _correlogram(axes[row, 1], res["lags"][1:], res["pacf"][1:], res["band"], f"PACF, {lab}")
    fig.suptitle(f"{cfg['name']}: sample ACF and PACF")
    return _save(fig, path)


def plot_trend_methods(lines: pd.DataFrame, cfg: dict, path: Path, fast: bool = False) -> Path:
    """The raw series with the four fitted trend lines on one chart."""
    _style(fast)
    fig, ax = plt.subplots(figsize=(8, 4) if fast else (11, 5))
    ax.plot(lines.index, lines["actual"], color="#999999", lw=1, label="actual (graphic method: by eye)")
    styles = {"semi_averages": "-", "centred_moving_average": "-",
              "least_squares_linear": "--", "least_squares_quadratic": ":"}
    for c, (col, ls) in zip(OKABE[0:4], styles.items()):
        ax.plot(lines.index, lines[col], ls, color=c, lw=2, label=col.replace("_", " "))
    ax.set(title=f"{cfg['name']}: four trend-measurement methods", xlabel=_xlabel(cfg), ylabel=cfg["unit"])
    ax.legend(fontsize=8)
    return _save(fig, path)


def plot_baselines(series: pd.Series, last_fold: pd.DataFrame, cfg: dict, path: Path,
                   fast: bool = False) -> Path:
    """Last backtest fold: recent history, the actual test window and the five forecasts."""
    _style(fast)
    fig, ax = plt.subplots(figsize=(8, 4) if fast else (11, 5))
    origin = int(last_fold["origin_index"].iloc[0])
    hist = series.iloc[max(0, origin - 4 * max(cfg["season"] or 1, cfg["horizon"])):origin]
    ax.plot(hist.index, hist.to_numpy(), color="#999999", lw=1.2, label="training history")
    first = last_fold[last_fold["baseline"] == last_fold["baseline"].iloc[0]]
    ax.plot(first["time"], first["actual"], "o-", color="#000000", lw=1.5, ms=3, label="actual")
    colors = [OKABE[i] for i in (0, 1, 2, 3, 5)]
    for c, (name, g) in zip(colors, last_fold.groupby("baseline", sort=False)):
        ax.plot(g["time"], g["forecast"], "--", color=c, lw=1.6, label=name)
    ax.set(title=f"{cfg['name']}: baselines on the last backtest fold (origin {origin})",
           xlabel=_xlabel(cfg), ylabel=cfg["unit"])
    ax.legend(fontsize=8, ncol=2)
    return _save(fig, path)


def plot_ccf(table: pd.DataFrame, xname: str, yname: str, path: Path, fast: bool = False) -> Path:
    """Bar chart of cross-correlation by lag with the 95% band."""
    _style(fast)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(table["lag"], table["ccf"], color=OKABE[0], width=0.6)
    band = float(table["band"].iloc[0])
    ax.axhspan(-band, band, color=OKABE[4], alpha=0.25, label="95% band")
    ax.set(title=f"Cross-correlation: {xname} (t) vs {yname} (t+k), first differences",
           xlabel="lag k (days; k > 0 means requests lead tokens)", ylabel="correlation", ylim=(-1.05, 1.05))
    ax.legend(fontsize=8)
    return _save(fig, path)
