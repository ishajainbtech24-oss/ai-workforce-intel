"""Phase 3 notebook sections (simulated paths and the standard forecast table)."""
from __future__ import annotations

from _nb_common import NB


def part_why(nb: NB) -> None:
    nb.md("""
    ## 1. Why simulate?
    A forecast is one line, but the future is a range. The cost engine in Phase 4 needs many possible
    futures, not one, so for every series we draw **200 sample paths** around the point forecast.
    The paths come from the model's own past mistakes, so their spread is an honest guess of the real uncertainty.
    """)


def part_table(nb: NB) -> None:
    nb.md("""
    ## 2. The standard table
    Every series, whatever model produced it, is written in **the same ten-column format**, so Phase 4 can
    read all of them with one piece of code. `sample_id = -1` is the point forecast; `0` to `199` are the paths.
    Below: the columns, then real rows (the point forecast and the first two paths) for one series.
    """)
    nb.code(r'''
    with step("standard table"):
        import config_phase3 as P3
        meaning = {"driver": "series name", "period_index": "1 .. horizon, in the native grain",
                   "calendar_month": "first day of the month of the step (empty for BurstGPT: no dates)",
                   "sample_id": "-1 = point forecast, 0..199 = simulated path", "value": "the number",
                   "unit": "tokens, requests, conversations, index_points ...", "model": "model actually used",
                   "source": "dataset", "grain": "hour, day, month, quarter", "kind": "always 'forecast' here"}
        show_table(pd.DataFrame({"column": P3.COLUMNS, "meaning": [meaning[c] for c in P3.COLUMNS]}), n=10)
        name = "burst_tokens_chat_daily" if "burst_tokens_chat_daily" in NAMES else NAMES[0]
        t = pd.read_parquet(f"outputs/phase3/forecasts/{name}.parquet")
        rows = pd.concat([t[t["sample_id"] == s].head(3) for s in (-1, 0, 1)])
        print(f"First 3 periods of the point forecast and of paths 0 and 1 for {name} ({len(t):,} rows in the file):")
        show_table(rows, n=9, digits=1)
    ''')


def part_how(nb: NB) -> None:
    nb.md("""
    ## 3. How a path is made
    **Point forecast + one resampled vector of backtest errors = one path.** A path picks one backtest fold at
    random and adds that fold's *whole* error vector (actual minus forecast, step by step), so a path that starts
    too high tends to stay too high, as real errors do. For positive series the errors are first expressed relative
    to the level at that time and then scaled to today's level. Beyond the backtest horizon the last error grows
    with the square root of the horizon. The diagram uses real numbers from one series.
    """)
    nb.code(r'''
    with step("path diagram"):
        import matplotlib.pyplot as plt
        name = "burst_tokens_chat_daily" if "burst_tokens_chat_daily" in NAMES else NAMES[0]
        t = pd.read_parquet(f"outputs/phase3/forecasts/{name}.parquet")
        point = t[t["sample_id"] == -1].sort_values("period_index")["value"].to_numpy()
        path = t[t["sample_id"] == 0].sort_values("period_index")["value"].to_numpy()
        x = range(1, len(point) + 1)
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.2), sharex=True)
        axes[0].plot(x, point, color="#0072B2", lw=2)
        axes[0].set_title("point forecast")
        axes[1].bar(x, path - point, color="#E69F00")
        axes[1].axhline(0, color="#8C8C8C", lw=1)
        axes[1].set_title("+ one resampled error vector")
        axes[2].plot(x, point, color="#0072B2", lw=1, ls="--", label="point forecast")
        axes[2].plot(x, path, color="#222222", lw=2, label="path 0")
        axes[2].set_title("= one simulated path")
        axes[2].legend(fontsize=8)
        for ax in axes:
            ax.set_xlabel("steps ahead")
        axes[0].set_ylabel(t["unit"].iloc[0])
        fig.suptitle(name, fontsize=10)
        plt.tight_layout()
        plt.show()
    ''')
    nb.md("""
    **Look at the code.** The real simulation function: draw folds with a seeded random generator, extend the
    error vectors beyond the backtest horizon, scale them, add them to the point forecast and clip at 0.
    """)
    nb.code(r'''
    with step("code: simulate"):
        show_source("tsaf.simulate", "simulate")
        show_source("tsaf.simulate", "extend_errors")
    ''')


def part_fans(nb: NB) -> None:
    nb.md("""
    ## 4. Fan charts
    How to read them: the dark line is the point forecast; the shaded bands hold 50%, 80% and 95% of the 200
    paths; thin grey lines are individual paths. A wide fan means an uncertain series. The title gives the
    result of the holdout check (section 5).
    """)
    nb.code(r'''
    with step("fan charts"):
        for name in NAMES:
            show_img(f"outputs/phase3/figures/fan_{name}.png", width=850)
    ''')


def part_check(nb: NB) -> None:
    nb.md("""
    ## 5. Honest check: do the bands hold on data the model has not seen?
    We repeat the whole procedure as if we stood at the start of the Phase 2 holdout (refit only on earlier data,
    errors only from earlier folds) and count how many actual holdout values fall inside the 80% and 95% bands.
    A well calibrated 80% band holds about 80% of them. Rows are flagged when the 80% band holds under 60% or the
    95% band under 85%. The hourly series is also split into hours 1 to 24 and 25 to 168.

    **Before and after.** Two optional fixes were tried: *recency weights* (newer backtest folds are drawn more
    often) and *level matching* (only folds from times with a similar level). For each series they were chosen on
    the last backtest folds only (a "pseudo-holdout"), never on this final holdout, then the final check was run
    once. The reading below, including the causes of the remaining misses, is taken from the summary file.
    """)
    nb.code(r'''
    with step("interval check"):
        ic = read_table("phase3", "interval_check")
        show_table(ic, n=20, cols=["driver", "segment", "n_holdout_points", "coverage_80_before", "coverage_80_after",
                                   "coverage_95_before", "coverage_95_after", "mean_width_80_before",
                                   "mean_width_80_after", "options", "flag"])
        show_img("outputs/phase3/figures/interval_check.png", width=750)
        text = md_section("outputs/phase3/PHASE3_SUMMARY.md", "Honest check")
        if text:
            display(Markdown("\n".join(l for l in text.splitlines() if not l.startswith("|"))))
    ''')
    nb.md("""
    **How the options were chosen.** Each row is one option combination scored on the held-out backtest folds;
    the chosen one has 80% coverage closest to 0.8 (tie: the narrower band). Identical rows mean the option made
    no difference for that series, so it stays off.
    """)
    nb.code(r'''
    with step("interval tuning"):
        tun = read_table("phase3", "interval_tuning")
        show_table(tun, n=40, cols=["driver", "option", "n_heldout_folds", "coverage_80", "coverage_95",
                                    "mean_width_80_relative_to_level", "chosen"])
    ''')


def part_run_rate(nb: NB) -> None:
    nb.md("""
    ## 6. BurstGPT 30-day run-rate
    Phase 4 works in months, but BurstGPT is forecast for 14 days. The run-rate of each path is the sum of its
    14 simulated days plus 16 times the mean of its last 7 days. **The last 16 days are extrapolated, not forecast.**
    """)
    nb.code(r'''
    with step("run-rate"):
        s = pd.read_csv("outputs/phase3/forecasts/burstgpt_monthly_run_rate_summary.csv")
        for c in ("p10", "p50", "p90", "point_forecast"):
            s[c + " (M tokens)"] = s[c] / 1e6
        show_table(s, cols=["driver", "p10 (M tokens)", "p50 (M tokens)", "p90 (M tokens)",
                            "point_forecast (M tokens)", "extrapolated_days"], digits=1)
        display(Markdown("**Warning: the last 16 of the 30 days are extrapolated from the last 7 simulated days.**"))
        show_img("outputs/phase3/figures/run_rate_burstgpt.png", width=850)
    ''')


def part_scenarios(nb: NB) -> None:
    nb.md("""
    ## 7. Scenario inputs: assumptions, not forecasts
    The time-saved scenarios are not forecast; they are taken directly from the data and kept in a separate file
    (`kind = assumption`). Each row says where its number comes from (`source`) and exactly how it was taken
    (`derivation`). Rows whose meaning was unclear would be marked `needs_review`.
    """)
    nb.code(r'''
    with step("scenarios"):
        sc = pd.read_csv("outputs/phase3/forecasts/scenario_tables.csv")
        show_table(sc, n=20, cols=["scenario", "parameter", "value", "unit", "status", "source", "derivation"])
        nr = sc[sc["status"] == "needs_review"]
        print(f"Rows marked needs_review: {len(nr)}" + (": " + ", ".join(nr["parameter"]) if len(nr) else ""))
        show_img("outputs/phase3/figures/scenarios.png", width=750)
    ''')


def part_validation(nb: NB) -> None:
    nb.md("""
    ## 8. Validation
    Every forecast file is checked: the ten columns in the right order, no missing or negative values,
    exactly 200 paths plus the point forecast, the full horizon, no duplicate rows. PASS means Phase 4 can read it.
    """)
    nb.code(r'''
    with step("validation"):
        show_table(read_table("phase3", "validation"), n=20)
    ''')


def part_explorer(nb: NB) -> None:
    nb.md("""
    ## 9. Explore a series (optional, interactive)
    Pick a series to see its fan chart and the first rows of its table. Nothing else depends on this cell.
    """)
    nb.code(r'''
    with step("explorer"):
        try:
            import ipywidgets as widgets
        except ImportError:
            widgets = None
            print("ipywidgets is not available; the fan charts above show the same content.")
        if widgets is not None and NAMES:
            box = widgets.Output()
            dd = widgets.Dropdown(options=NAMES, value=NAMES[0], description="series")
            def _show(change=None):
                box.clear_output()
                with box:
                    show_img(f"outputs/phase3/figures/fan_{dd.value}.png", width=800)
                    show_table(pd.read_parquet(f"outputs/phase3/forecasts/{dd.value}.parquet"), n=5, digits=1)
            dd.observe(_show, names="value")
            display(dd, box)
            _show()
    ''')


def phase3_sections(nb: NB) -> None:
    for part in (part_why, part_table, part_how, part_fans, part_check, part_run_rate, part_scenarios,
                 part_validation, part_explorer):
        part(nb)
