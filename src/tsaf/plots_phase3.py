"""Phase 3 figures: fan charts, holdout interval check, BurstGPT run-rate, scenario values.

Same conventions as Phases 1-2: 'Agg', 150 dpi PNG, Okabe-Ito palette, titles and labelled
axes with units, every figure closed after saving.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config_phase3 as P3  # noqa: E402
from tsaf.models.base import future_index  # noqa: E402
from tsaf.plots import OKABE, _style  # noqa: E402
from tsaf.plots_phase2 import _axes_format, _save, _xlabel  # noqa: E402

BLUE, ORANGE, GREEN, VERMILION, INK, GREY = OKABE[0], OKABE[1], OKABE[2], OKABE[5], "#222222", "#8C8C8C"


def plot_fan(r: dict, coverage_text: str, path: Path, thin: int = P3.FAN_THIN_PATHS) -> Path:
    """History tail, point forecast, 50/80/95% bands of the paths and some thin sample paths."""
    _style(False)
    s, cfg, grain = r["series"], r["cfg"], r["entry"]["grain"]
    hist = s.iloc[-P3.FAN_HISTORY.get(grain, 60):]
    fut = future_index(s.index, len(r["point"]), grain)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(hist.index, hist.to_numpy(), color=INK, lw=1.2, label="history (modelling window)")
    for lv, alpha in ((0.95, 0.12), (0.80, 0.22), (0.50, 0.35)):
        a = (1 - lv) / 2 * 100
        lo, hi = np.percentile(r["paths"], [a, 100 - a], axis=0)
        ax.fill_between(fut, lo, hi, color=BLUE, alpha=alpha, lw=0, label=f"{lv:.0%} band of {P3.N_SAMPLES} paths")
    for k in range(min(thin, len(r["paths"]))):
        ax.plot(fut, r["paths"][k], color=GREY, lw=0.5, alpha=0.5, label="sample paths" if k == 0 else None)
    ax.plot(fut, r["point"], color=BLUE, lw=2, label=f"point forecast ({r['manifest']['model_used']})")
    ax.axvline(fut[0], color=GREY, lw=1, ls=":")
    ax.set_title(f"{cfg['name']}: {len(fut)}-step forecast fan\n{coverage_text}", fontsize=10)
    ax.set_xlabel(_xlabel(cfg))
    ax.set_ylabel(r["unit"].replace("_", " ") + f" (per {P3.GRAIN_NAME[grain]})")
    _axes_format(ax, isinstance(fut, pd.DatetimeIndex))
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    return _save(fig, path)


def plot_interval_check(check: pd.DataFrame, path: Path) -> Path:
    """Holdout coverage of the simulated 80% and 95% bands per driver against the targets."""
    _style(False)
    c = check.copy()
    c["label"] = np.where(c["segment"] == "all", c["driver"], c["driver"] + " (" + c["segment"] + ")")
    y = np.arange(len(c))
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(c) + 1.6))
    ax.barh(y - 0.2, c["coverage_80"], height=0.38, color=BLUE, label="80% band coverage")
    ax.barh(y + 0.2, c["coverage_95"], height=0.38, color=ORANGE, label="95% band coverage")
    ax.axvline(0.80, color=BLUE, ls="--", lw=1.2, label="target 80%")
    ax.axvline(0.95, color=VERMILION, ls=":", lw=1.5, label="target 95%")
    ax.set_yticks(y, c["label"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("share of actual holdout values inside the simulated band")
    ax.set_title("Holdout check of the simulated intervals (refit before the holdout)")
    ax.grid(axis="y", visible=False)
    ax.legend(fontsize=8, loc="lower right")
    return _save(fig, path)


def plot_run_rate(rr: pd.DataFrame, summary: pd.DataFrame, path: Path) -> Path:
    """Histogram of the 30-day run-rate paths per BurstGPT token driver with P10/P50/P90."""
    _style(False)
    drivers = list(summary["driver"])
    fig, axes = plt.subplots(1, len(drivers), figsize=(4.2 * len(drivers), 3.6), squeeze=False)
    for ax, d in zip(axes[0], drivers):
        v = rr[(rr["driver"] == d) & (rr["sample_id"] >= 0)]["run_rate_30d"] / 1e6
        ax.hist(v, bins=25, color=BLUE, edgecolor="white")
        q = summary.set_index("driver").loc[d]
        for key, ls in (("p10", ":"), ("p50", "--"), ("p90", ":")):
            ax.axvline(q[key] / 1e6, color=VERMILION, ls=ls, lw=1.5, label=f"{key.upper()} {q[key] / 1e6:,.0f}M")
        ax.set_title(d.replace("burst_tokens_", "").replace("_daily", "") + " tokens", fontsize=10)
        ax.set_xlabel("30-day run-rate (million tokens)")
        ax.legend(fontsize=7)
    axes[0, 0].set_ylabel("number of paths")
    fig.suptitle("BurstGPT 30-day token run-rate: 14 simulated days + last 16 days extrapolated", fontsize=11)
    return _save(fig, path)


def plot_scenarios(sc: pd.DataFrame, path: Path) -> Path:
    """Scenario parameter values (rows with status needs_review left out), unit in each label."""
    _style(False)
    s = sc[sc["status"] != "needs_review"].reset_index(drop=True)
    colors = {"downside": VERMILION, "expected": BLUE, "optimistic": GREEN}
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(s) + 1.6))
    y = np.arange(len(s))
    ax.barh(y, s["value"], color=[colors.get(x, GREY) for x in s["scenario"]], height=0.6)
    for i, v in enumerate(s["value"]):
        ax.text(v, i, f" {v:+.1f}" if v < 0 else f" {v:.1f}", va="center", fontsize=8, color=INK)
    hint = {"pct_change_in_task_time": "% MORE task time with AI, i.e. slower",
            "pct_of_work_hours": "% of work hours saved"}
    ax.set_yticks(y, [f"{a}: {b}\n({hint.get(u, u)})" for a, b, u in zip(s["scenario"], s["parameter"], s["unit"])],
                  fontsize=8)
    ax.axvline(0, color=GREY, lw=1)
    ax.invert_yaxis()
    ax.set_xlabel("value in the row's unit (percent)")
    ax.set_title("Scenario inputs (assumptions, not forecasts)")
    ax.grid(axis="y", visible=False)
    return _save(fig, path)
