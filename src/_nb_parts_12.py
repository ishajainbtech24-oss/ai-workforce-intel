"""Phase 1 (parts A and B) and Phase 2 (part C) notebook sections, unchanged from the combined notebook.

Each function adds its cells to an `_nb_common.NB`; shared setup cells live in `_nb_common`.
"""
from __future__ import annotations

from _nb_common import NB


# --------------------------------------------------------------------------- part A
def part_a(nb: NB) -> None:
    nb.md("""
    # Part A: the data

    The project models **seven drivers** (time series). The table comes from `outputs/phase1/handoff.json`,
    the file Phase 1 writes for Phase 2: grain (daily, hourly, monthly, quarterly), number of observations,
    the index or date range, and the seasonal period (7 = weekly cycle in daily data, 24 = daily cycle in
    hourly data, 12 = yearly cycle in monthly data, 4 = yearly cycle in quarterly data).
    """)
    nb.code(r'''
    NAMES = []
    with step("drivers"):
        HANDOFF = json.loads(Path("outputs/phase1/handoff.json").read_text(encoding="utf-8"))
        NAMES = [d["name"] for d in HANDOFF["drivers"] if not DRIVERS or d["name"] in DRIVERS]
        stats = read_table("phase1", "summary_stats").set_index("driver")
        rows = [{"driver": d["name"], "grain": d["grain"], "n": d["n_obs"],
                 "from": stats.loc[d["name"], "start"] if d["name"] in stats.index else "",
                 "to": stats.loc[d["name"], "end"] if d["name"] in stats.index else "",
                 "season": d["season"], "extra seasons": ", ".join(map(str, d["extra_seasons"])) or "-"}
                for d in HANDOFF["drivers"] if d["name"] in NAMES]
        show_table(pd.DataFrame(rows), n=20)
        print("Not analysed:", "; ".join(f"{s['name']} ({s['reason'][:70]})" for s in HANDOFF.get("skipped", [])))
    ''')
    nb.md("""
    **The BurstGPT modelling window.** BurstGPT is a trace of real LLM API and chat requests. It has no
    calendar dates, only "day since the trace started". We model **days 0 to 86** only:
    days 87 to 91 are *copied days* (the trace repeats earlier data, so they are not real),
    and days 93 to 110 are a *low-activity* tail where logging was clearly reduced. **Day 77** is a real
    one-day outage (almost no traffic). We keep it in the data, mark it on every chart, and later test
    whether an anomaly screen finds it. The figures below come from the preprocessing step.
    """)
    nb.code(r'''
    with step("preprocessing figures"):
        figs = sorted(Path("reports/figures").glob("*.png"))
        if not figs:
            print("No preprocessing figures in this bundle; skipped.")
        for f in figs:
            print(f.stem)
            show_img(f, width=800)
    ''')


# --------------------------------------------------------------------------- part B
def part_b(nb: NB) -> None:
    nb.md("""
    # Part B: Phase 1, exploration and baselines

    ## B1. The series
    First we simply look at each series. Shaded areas are flagged days (copied, low activity, outage);
    the dashed line marks the start of the **hold-out**, the final stretch we keep aside for a last, fair test.
    The table below gives the size and variability: the **coefficient of variation** (CV = standard
    deviation / mean) says how bursty a series is (above 1 is very bursty).
    """)
    nb.code(r'''
    with step("series"):
        show_table(read_table("phase1", "summary_stats"), n=20,
                   cols=["driver", "unit", "n", "mean", "std", "cv", "zero_share", "skewness"])
        for name in NAMES:
            show_img(f"outputs/phase1/figures/{name}_series.png", width=850)
    ''')
    nb.md("""
    ## B2. Components: trend, seasonality and remainder
    A series = trend + seasonal pattern + remainder (**additive**), or trend x seasonal x remainder
    (**multiplicative**, when the swings grow with the level). Our rule: if the rolling standard deviation
    rises with the rolling mean (correlation above 0.5), choose multiplicative. **Strength** (0 to 1) says
    how much of the variation the trend or the seasonal part explains.
    """)
    nb.code(r'''
    with step("decomposition"):
        show_table(read_table("phase1", "decomposition"), n=20,
                   cols=["driver", "type", "reason", "method", "seasonal_strength", "trend_strength"])
        for name in ["burst_tokens_total_daily", "burst_requests_hourly"]:
            show_img(f"outputs/phase1/figures/{name}_decomposition.png", width=850)
    ''')
    nb.md("""
    ## B3. Measuring the trend: four classic methods
    On BurstGPT total tokens per day we measure the trend four ways: **semi-averages** (mean of the second
    half minus mean of the first half, divided by the distance between their centres), a **centred moving
    average**, and **least squares** with a straight line and with a quadratic curve. The slope is in tokens
    per day and as a percentage of the mean.
    """)
    nb.code(r'''
    with step("trend methods"):
        show_table(read_table("phase1", "trend_methods"), cols=["method", "slope_per_step", "slope_pct_of_mean", "how"])
        show_img("outputs/phase1/figures/trend_methods_burstgpt.png", width=850)
    ''')
    nb.md("""
    ## B4. Dependence: ACF and PACF
    The **ACF** shows how a value correlates with the value k steps earlier; the **PACF** shows the same after
    removing the effect of the steps in between. Bars outside the shaded band are significant. A spike at
    lag 7 in daily data means a weekly pattern; a slowly decaying ACF means a trend (not stationary).
    """)
    nb.code(r'''
    with step("acf pacf"):
        for name in ["burst_tokens_total_daily", "burst_requests_hourly", "eci_wages_quarterly"]:
            show_img(f"outputs/phase1/figures/{name}_acf_pacf.png", width=850)
    ''')
    nb.md("""
    ## B5. Stationarity: ADF and KPSS together
    ARIMA needs a **stationary** series (constant mean and variance). The two tests ask opposite questions:
    **ADF**: "is there a unit root?" (small p-value = stationary); **KPSS**: "is it stationary?"
    (small p-value = not stationary). We difference (d = ordinary, D = seasonal) until both agree the
    series is stationary. The decision per driver is carried into Phase 2.
    """)
    nb.code(r'''
    with step("stationarity"):
        show_table(read_table("phase1", "stationarity"), n=25,
                   cols=["driver", "d", "D", "adf_stat", "adf_p", "kpss_stat", "kpss_p", "verdict"])
        dec = pd.DataFrame([{k: d[k] for k in ("name", "d", "D", "decomposition", "tests_agree")} for d in HANDOFF["drivers"]])
        print("Decision carried into Phase 2:")
        show_table(dec, n=20)
    ''')
    nb.md("""
    ## B6. Anomaly screen and the day-77 check
    We flag a day when its **robust z-score** (distance from the median, measured in MADs, the median
    absolute deviation) is above 3.5. The known outage on day 77 is the test case. The result is shown
    honestly below, straight from `PHASE1_SUMMARY.md`, including a FAIL if that is what happened.
    """)
    nb.code(r'''
    with step("day 77"):
        an = read_table("phase1", "anomalies")
        show_table(an[an["note"].fillna("").str.contains("day-77")], cols=["driver", "time", "robust_z", "note"])
        text = md_section("outputs/phase1/PHASE1_SUMMARY.md", "day-77")
        display(Markdown(text) if text else Markdown("_No day-77 section in the summary._"))
    ''')
    nb.md("""
    ## B7. Baselines: the bar every later model must beat
    Five simple forecasts: **naive** (repeat the last value), **seasonal naive** (repeat the last season),
    **mean**, **drift** (straight line from first to last value) and a **seasonal moving average**.
    We score them with **MASE**: the forecast error divided by the error of the seasonal naive forecast
    on the training data, so **MASE below 1 means better than seasonal naive**.
    **Every later model must beat the seasonal naive baseline.**
    """)
    nb.code(r'''
    with step("baselines"):
        show_table(read_table("phase1", "leaderboard_baselines"), n=20)
        show_img("outputs/phase1/figures/baselines_burst_tokens_total_daily.png", width=850)
    ''')
    nb.md("""
    ## B8. A look at the code
    These cells print real functions from the project with `inspect.getsource`, so you can point to the exact
    lines in the review. First **MASE**: the mean absolute error scaled by the in-sample error of seasonal naive.
    """)
    nb.code(r'''
    with step("code: mase"):
        show_source("tsaf.metrics", "mase_scale")
        show_source("tsaf.metrics", "mase")
    ''')
    nb.md("""
    **Semi-averages trend**: split the series in two halves, take each half's mean, and divide the
    difference by the distance between the two half centres.
    """)
    nb.code(r'''
    with step("code: semi-averages"):
        show_source("tsaf.eda", "semi_averages")
    ''')
    nb.md("""
    **Rolling-origin backtest**: every fold trains only on the data before its origin and tests on the next
    h points; the origin then moves forward by `step`. No shuffling, so the future never leaks into training.
    """)
    nb.code(r'''
    with step("code: rolling origin"):
        show_source("tsaf.backtest", "rolling_origin")
    ''')


# --------------------------------------------------------------------------- part C
def part_c(nb: NB) -> None:
    nb.md("""
    # Part C: Phase 2, forecasting models

    ## C1. The model families
    - **baseline**: the five Phase 1 benchmarks.
    - **smoothing**: moving average and exponential smoothing (SES, Holt, damped Holt, Holt-Winters), which weight recent values more.
    - **arima**: ARIMA, seasonal SARIMA, and SARIMAX with extra inputs (weekend dummy, or Fourier sine/cosine terms for hourly data).
    - **ml**: Ridge regression, random forest and XGBoost on lag features, forecasting one step at a time.
    - **deep**: optional Prophet and LSTM challengers.
    - **ensemble**: the average of the two best models.

    The table lists every registered model and the series it actually ran on (from the leaderboard).
    """)
    nb.code(r'''
    with step("families"):
        from tsaf.models.registry import build_registry
        lb = read_table("phase2", "leaderboard")
        rows = []
        for model, family in [(s.name, s.family) for s in build_registry()] + [("ensemble", "ensemble")]:
            ok = lb[(lb["model"] == model) & (lb["status"] == "ok")]["driver"].tolist()
            rows.append({"family": family, "model": model,
                         "ran on": f"{len(ok)} series" + (f": {', '.join(ok)}" if 0 < len(ok) < 4 else "")
                         if ok else "not run (reason in leaderboard.csv)"})
        show_table(pd.DataFrame(rows), n=40)
    ''')
    nb.md("""
    ## C2. How the models are compared
    Every model gets **exactly the same test**: an *expanding-window rolling-origin backtest*. The training
    window (blue) grows, the test window (orange) moves forward, and the **hold-out** at the end (grey) is
    used once, at the very end, never for choosing. The diagram uses the real settings of BurstGPT daily
    tokens. A model "wins" a series only if its mean cross-validation (CV) **MASE** is below seasonal naive's.
    """)
    nb.code(r'''
    with step("backtest diagram"):
        import matplotlib.pyplot as plt
        from tsaf import backtest
        d = next(x for x in HANDOFF["drivers"] if x["grain"] == "daily")
        cv, n = d["cv_settings"], d["n_obs"]
        origins = backtest.fold_origins(n - cv["holdout"], cv["initial"], cv["h"], cv["step"])
        fig, ax = plt.subplots(figsize=(9, 0.55 * (len(origins) + 2)))
        for i, o in enumerate(origins):
            ax.barh(i, o, color="#0072B2", height=0.6)
            ax.barh(i, cv["h"], left=o, color="#E69F00", height=0.6)
        k = len(origins)
        ax.barh(k, n - cv["holdout"], color="#0072B2", height=0.6)
        ax.barh(k, cv["holdout"], left=n - cv["holdout"], color="#8C8C8C", height=0.6)
        ax.set_yticks(range(k + 1), [f"fold {i}" for i in range(k)] + ["hold-out"])
        ax.invert_yaxis()
        ax.set_xlabel("day since trace start")
        ax.set_title(f"{d['name']}: {k} folds of {cv['h']} days, then a {cv['holdout']}-day hold-out")
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in ("#0072B2", "#E69F00", "#8C8C8C")],
                  labels=["training data", "test window", "hold-out"], loc="lower right", fontsize=8)
        plt.tight_layout()
        plt.show()
    ''')
    nb.md("""
    ## C3. Leaderboards
    For each series: bars of mean CV MASE per model (shorter is better), the dashed line is seasonal naive,
    the blue bar is the chosen model. The table shows the top 5 with the **share of folds** in which the
    model beat seasonal naive and its **hold-out MASE** (the final, untouched test).
    """)
    nb.code(r'''
    with step("leaderboards"):
        lb = read_table("phase2", "leaderboard")
        ok = lb[lb["status"] == "ok"]
        for name in NAMES:
            display(Markdown(f"**{name}**"))
            show_img(f"outputs/phase2/figures/leaderboard_{name}.png", width=650)
            top = ok[ok["driver"] == name].sort_values("cv_mase").head(5)
            show_table(top, cols=["model", "family", "cv_mase", "share_beats_snaive", "holdout_mase"])
    ''')
    nb.md("""
    ## C4. The chosen model per series
    The rule: rank by mean CV MASE; a model is chosen only if it beats seasonal naive; ties within 1% go to
    the simpler family. The `why` column shows the rule that was applied.
    """)
    nb.code(r'''
    with step("chosen models"):
        ch = read_table("phase2", "chosen_models")
        show_table(ch, n=20, cols=["driver", "chosen_model", "family", "cv_mase", "holdout_mase",
                                   "seasonal_naive_cv_mase", "beats_seasonal_naive", "why"])
        n_ens = int((ch["family"] == "ensemble").sum())
        n_base = int((ch["family"] == "baseline").sum())
        print(f"Won by the ensemble: {n_ens} | by a single model: {len(ch) - n_ens - n_base} | "
              f"by a baseline: {n_base} (of {len(ch)} series)")
    ''')
    nb.md("""
    ## C5. Ensemble check: is the ensemble really better?
    The ensemble averages the two models with the best CV MASE, so it was **chosen on the same CV folds**
    it is scored on, and its CV score is optimistic. The **hold-out** was never used for choosing, so it is the
    fair check: compare the ensemble's hold-out MASE with seasonal naive's on the same hold-out.
    """)
    nb.code(r'''
    with step("ensemble check"):
        lb = read_table("phase2", "leaderboard").set_index(["driver", "model"])
        ch = read_table("phase2", "chosen_models").set_index("driver")
        rows = []
        for name in NAMES:
            if (name, "ensemble") not in lb.index:
                continue
            e, s = lb.loc[(name, "ensemble")], lb.loc[(name, "seasonal_naive")]
            rows.append({"driver": name, "chosen": ch.loc[name, "chosen_model"] if name in ch.index else "",
                         "ensemble of": e["reason"].replace("average of ", ""),
                         "ensemble CV MASE": e["cv_mase"], "ensemble hold-out MASE": e["holdout_mase"],
                         "seasonal naive hold-out MASE": s["holdout_mase"],
                         "ensemble better on hold-out": bool(e["holdout_mase"] < s["holdout_mase"])})
        show_table(pd.DataFrame(rows), n=20)
    ''')
    nb.md("""
    ## C6. Forecasts on the hold-out
    History in black, the hold-out actual with dots, the chosen model in blue with its **80% and 95%
    prediction intervals** (built from the model's own backtest errors), and seasonal naive dashed for comparison.
    """)
    nb.code(r'''
    with step("forecasts"):
        for name in NAMES:
            show_img(f"outputs/phase2/figures/forecast_{name}.png", width=900)
    ''')
    nb.md("""
    ## C7. Diagnostics: are the residuals just noise?
    A good model leaves residuals (actual minus fitted) that look like **white noise**: no pattern left.
    The **Ljung-Box test** checks this (p-value above 0.05 = looks like white noise). **Shapiro-Wilk** checks
    normality. The **coverage** table checks the intervals: an 80% interval should contain about 80% of the
    actual values; rows highlighted in orange fall short (below 60% for the 80% interval or below 85% for the 95% interval).
    """)
    nb.code(r'''
    with step("residual diagnostics"):
        rd = read_table("phase2", "residual_diagnostics")
        lag_cols = [c for c in rd.columns if c.startswith("ljung_box_p_lag")]
        show_table(rd, n=20, cols=["driver", "model", "white_noise", *lag_cols, "shapiro_p", "normal_residuals"])
        for name in NAMES:
            show_img(f"outputs/phase2/figures/residuals_{name}.png", width=850)
    ''')
    nb.code(r'''
    with step("interval coverage"):
        cov = read_table("phase2", "interval_coverage")
        ch = read_table("phase2", "chosen_models")
        keep = set(zip(ch["driver"], ch["chosen_model"])) | {(d, "seasonal_naive") for d in ch["driver"]}
        sub = cov[[(d, m) in keep for d, m in zip(cov["driver"], cov["model"])]].copy()
        sub["flags"] = sub["flags"].fillna("")
        sub = sub[["driver", "model", "n_folds", "coverage_80", "coverage_95", "flags"]].round(3).reset_index(drop=True)
        print(f"{int(cov['flags'].fillna('').str.contains('coverage').sum())} of {len(cov)} model-series pairs have a coverage warning; "
              "chosen models and seasonal naive shown below.")
        try:
            display(sub.style.apply(lambda r: ["background-color: #FBD9C4" if "coverage" in r["flags"] else "" for _ in r], axis=1)
                    .format(precision=3))
        except Exception:
            display(sub)
    ''')
    nb.md("""
    ## C8. Machine-learning insight
    Tree models report **feature importance**: how much each input reduced the error. `lag_k` is the value
    k steps earlier, `roll_mean` and `roll_std` summarise the last week (or day), `cycle_sin/cos` encode the
    weekday or hour. For total tokens we also tried adding **requests** (lagged 14 days) as an extra input.
    """)
    nb.code(r'''
    with step("feature importance"):
        import matplotlib.pyplot as plt
        fi = read_table("phase2", "feature_importance")
        pairs = [(d, "random_forest") for d in ("burst_tokens_total_daily", "burst_requests_hourly")
                 if ((fi["driver"] == d) & (fi["model"] == "random_forest")).any()]
        if pairs:
            fig, axes = plt.subplots(1, len(pairs), figsize=(5.5 * len(pairs), 3.6), squeeze=False)
            for ax, (d, m) in zip(axes[0], pairs):
                g = fi[(fi["driver"] == d) & (fi["model"] == m)].nlargest(8, "importance").iloc[::-1]
                ax.barh(g["feature"], g["importance"], color="#0072B2")
                ax.set_title(f"{d}\n{m}", fontsize=10)
                ax.set_xlabel("importance (share of error reduction)")
            plt.tight_layout()
            plt.show()
        lb = read_table("phase2", "leaderboard")
        t = lb[(lb["driver"] == "burst_tokens_total_daily") & (lb["family"] == "ml") & (lb["status"] == "ok")]
        if len(t):
            t = t.assign(base=t["model"].str.replace("_with_requests", "", regex=False),
                         variant=["with requests" if m.endswith("_with_requests") else "without" for m in t["model"]])
            comp = t.pivot(index="base", columns="variant", values="cv_mase").round(3)
            if {"with requests", "without"} <= set(comp.columns):
                comp["requests helped"] = comp["with requests"] < comp["without"]
            print("Mean CV MASE of the ML models on burst_tokens_total_daily, with and without requests:")
            display(comp)
    ''')
    nb.md("""
    **The recursive forecast** used by the machine-learning models: predict one step, append the prediction
    to the history, rebuild the lag features, and repeat. This is how a one-step model produces a multi-step forecast.
    """)
    nb.code(r'''
    with step("code: recursive forecast"):
        show_source("tsaf.models.ml", "recursive_forecast")
    ''')
    nb.md("""
    ## C9. Prophet and LSTM (optional challengers)
    Both are optional. Prophet needs the `prophet` package; the LSTM needs `torch` and the `--with-lstm` switch.
    """)
    nb.code(r'''
    with step("prophet lstm"):
        lb = read_table("phase2", "leaderboard")
        for m in ("prophet", "lstm"):
            g = lb[lb["model"] == m]
            ran = g[g["status"] == "ok"]
            if len(ran):
                show_table(ran, cols=["driver", "model", "cv_mase", "holdout_mase"])
            else:
                reasons = sorted(set(g["reason"].fillna("")) - {""})
                why = next((r for r in reasons if "only for" not in r), reasons[0] if reasons else "not run")
                print(f"{m}: skipped (not installed or switched off): {why}")
    ''')
    nb.md("""
    ## C10. Explore a series (optional, interactive)
    Pick a series in the dropdown to see its leaderboard, forecast and residual figures together.
    Nothing else in the notebook depends on this cell.
    """)
    nb.code(r'''
    with step("explorer"):
        try:
            import ipywidgets as widgets
        except ImportError:
            widgets = None
            print("ipywidgets is not available; the figures above show the same content.")
        if widgets is not None and NAMES:
            box = widgets.Output()
            dd = widgets.Dropdown(options=NAMES, value=NAMES[0], description="series")
            def _show(change=None):
                box.clear_output()
                with box:
                    for kind, w in (("leaderboard", 600), ("forecast", 850), ("residuals", 800)):
                        show_img(f"outputs/phase2/figures/{kind}_{dd.value}.png", width=w)
            dd.observe(_show, names="value")
            display(dd, box)
            _show()
    ''')
