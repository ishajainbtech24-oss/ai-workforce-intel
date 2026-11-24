# AI Workforce Investment Intelligence (CS3216 TSAF)

Download and preprocessing live in `ai-workforce-intel/` (scripts `src/prep_*.py`, notebook
`TSAF_Data_Preprocessing.ipynb`, see its README). This outer folder holds the processed data
(`data/processed/`) and the modelling phases.

Use Python 3.10 to 3.13 (developed on 3.11). On this machine `python` resolves to the empty
3.15 pre-release in `.venv`, so run commands with `py -3.11` instead of `python`.

```bash
pip install -r requirements.txt
```

## Phase 1: exploration and baselines

```bash
python src/run_phase1.py            # full run (about 15 seconds)
python src/run_phase1.py --fast     # 3 folds max, no cross-correlation, smaller plots
python src/run_phase1.py --drivers burst_tokens_total_daily burst_requests_hourly
python -m pytest -q tests           # unit + smoke tests (about 10 seconds)
```

The drivers, seasonal periods, minimum lengths and backtest settings are in `src/config.py`.
Phase 1 code is in `src/tsaf/`: `loaders` (series + flags), `metrics` (MAE, RMSE, sMAPE, MAPE,
MASE), `eda` (summary, decomposition, trend methods, anomaly screen), `stationarity`
(ADF + KPSS, d/D decision), `dependence` (ACF, PACF, CCF), `baselines` (naive, seasonal naive,
mean, drift, seasonal MA(3)), `backtest` (expanding-window rolling origin + hold-out),
`plots`, `handoff`, `report`, `pipeline`.

Outputs (`outputs/phase1/`):

| File | Content |
|---|---|
| `data_contract.md` | columns, dtypes, rows, ranges, nulls of every processed file |
| `run.log` | the run's log, one line per driver |
| `tables/summary_stats.csv` | n, mean, std, zeros, coefficient of variation, skewness |
| `tables/decomposition.csv` | additive/multiplicative choice and reason, seasonal and trend strength |
| `tables/trend_methods.csv` | semi-averages, centred MA, linear and quadratic slopes |
| `tables/stationarity.csv` | ADF and KPSS for each (d, D) |
| `tables/anomalies.csv` | robust z-score screen and the day-77 check |
| `tables/cross_correlation.csv` | requests vs tokens, lags -10 to 10 |
| `tables/baseline_cv.csv`, `baseline_folds.csv`, `baseline_holdout.csv` | baseline scores |
| `tables/leaderboard_baselines.csv` | best baseline per driver by CV MASE |
| `figures/` | series, decomposition, ACF/PACF, baselines per driver; trend methods; CCF |
| `handoff.json` | per-driver decisions and benchmark scores read by Phase 2 |
| `PHASE1_SUMMARY.md` | generated findings, decisions, review talking points, limitations |

## Phase 2: forecasting models and rolling backtests

```bash
python src/run_phase2.py               # full run (about 10 minutes)
python src/run_phase2.py --fast        # 3 folds, 8 ARIMA candidates, 100 trees, no hourly SARIMAX/Prophet/LSTM
python src/run_phase2.py --with-lstm   # also the optional LSTM challenger (needs torch)
python src/run_phase2.py --drivers burst_tokens_total_daily
```

Reads `outputs/phase1/handoff.json` (drivers, season, d, D, decomposition, CV settings) and runs
every model through Phase 1's rolling-origin folds and hold-out. Models (`src/tsaf/models/`,
one interface `fit(train, h, ctx)`; registry in `registry.py`): the five baselines; moving
average, SES, Holt, damped Holt, Holt-Winters additive/multiplicative; ARIMA, SARIMA, SARIMAX
(orders by AICc on the first training window); Ridge, Random Forest, XGBoost (recursive
multi-step, daily and hourly only, plus `*_with_requests` for total tokens); optional Prophet
and LSTM; and an average of the two best models. Settings are in `src/config_phase2.py`;
optional packages are detected in `src/optional.py`. A model wins a driver only if its mean CV
MASE is below seasonal naive.

Outputs (`outputs/phase2/`):

| File | Content |
|---|---|
| `run.log` | one line per driver and model, with seconds |
| `tables/leaderboard.csv` | every driver x model: status, CV MAE/RMSE/sMAPE/MAPE/MASE, share of folds beating seasonal naive, 80%/95% coverage, flags, hold-out scores, fit seconds |
| `tables/chosen_models.csv` | chosen model per driver, the rule applied, CV and hold-out MASE |
| `tables/params.csv` | selected orders, windows, smoothing parameters, ML settings, Fourier K, fallbacks |
| `tables/cv_folds.csv`, `tables/cv_residuals.parquet` | fold forecasts with intervals; out-of-sample errors for Phase 3 |
| `tables/holdout.csv` | hold-out forecasts, intervals and scores |
| `tables/residual_diagnostics.csv`, `tables/arima_params.csv` | Ljung-Box, normality, residual statistics; ARIMA parameter tables with p-values |
| `tables/interval_coverage.csv`, `tables/feature_importance.csv`, `tables/anomalies.csv` | coverage, RF/XGBoost importances, flagged points and the day-77 check |
| `figures/` | `leaderboard_`, `forecast_`, `residuals_`, `cv_folds_<driver>.png` |
| `chosen_models.json` | hand-off to Phase 3 (schema-checked) |
| `PHASE2_SUMMARY.md` | generated results, review talking points, limitations, deviations |

## Phase 3: standard forecast tables (200 simulated paths)

```bash
python src/run_phase3.py           # about 5 seconds; refits the chosen models and simulates
python src/run_phase3.py --fast    # same numbers, fan charts without the thin sample paths
```

Reads `outputs/phase2/chosen_models.json` (model + fixed parameters) and
`outputs/phase2/tables/cv_residuals.parquet` (backtest errors). Each chosen model is refitted on the
full window (`src/tsaf/forecast.py`, seasonal-naive fallback if a refit fails or explodes), then
200 paths are drawn by residual bootstrap (`src/tsaf/simulate.py`: whole error vectors of a random
fold, relative errors for positive series, `GROWTH = "sqrt"` beyond the backtest horizon in
`src/config.py`, seed 42 + driver position). The same procedure is checked on the Phase 2 holdout.
Two optional interval fixes, `RECENCY_HALF_LIFE` and `LEVEL_MATCH` in `src/config.py`, are chosen per driver by a pseudo-holdout on the last backtest folds (never the final holdout; `tables/interval_tuning.csv`), and the holdout check reports coverage before and after. `inputs_for_phase4.json` recommends uncertainty multipliers 1.0 / 1.5 / 2.0 for Phase 4 (the saved files are unscaled). Settings: `src/config_phase3.py`.

Outputs (`outputs/phase3/`):

| File | Content |
|---|---|
| `forecasts/<driver>.parquet` / `.csv` | the standard table: `driver, period_index, calendar_month, sample_id, value, unit, model, source, grain, kind` (sample_id -1 = point forecast) |
| `forecasts/burstgpt_monthly_run_rate*.csv` | 30-day token run-rate per path and its P10/P50/P90 (last 16 days extrapolated, see the NOTE file) |
| `forecasts/scenario_tables.csv` | downside / expected / optimistic time-saved assumptions (`kind = assumption`), with source and derivation |
| `tables/interval_check.csv` | holdout coverage of the simulated 80% / 95% bands (hourly split 1-24 / 25-168) |
| `tables/validation.csv` | schema PASS/FAIL per file |
| `manifest.json`, `inputs_for_phase4.json` | per-driver run details; input-token share, API/chat shares, file list |
| `figures/` | `fan_<driver>.png`, `interval_check.png`, `run_rate_burstgpt.png`, `scenarios.png` |
| `PHASE3_SUMMARY.md` | generated results, review talking points, limitations, deviations |

## Phase 4: Monte Carlo cost and value engine

```bash
python src/run_phase4.py                                   # example company, 5,000 draws x 9 runs (about 10 s)
python src/run_phase4.py --fast                            # 1,000 draws, no tornado chart
python src/run_phase4.py --inputs my_company.json --horizon 18
```

Turns the Phase 3 paths (ECI wages, PPI hosting, BurstGPT demand factor; no Epoch price forecast yet, so a flat
input price is used and flagged) and the company inputs in `config/example_company.json` (an **illustrative
example company**; every value is flagged and should be replaced) into monthly token, hosting, enablement and
integration cost, the value of saved time per scenario (downside / expected / optimistic from
`scenario_tables.csv`), and break-even. Each draw picks one path per driver (independent between drivers);
the uncertainty multiplier k = 1.0 / 1.5 / 2.0 widens the paths. Engine roles are mapped in `src/config.py`
(`ENGINE_DRIVERS`), settings in `src/config_phase4.py`, code in `src/engine/`
(`inputs`, `drivers`, `model`, `simulate` with `run_engine` / `summarise`, `sensitivity`, `plots`, `report`).

Outputs (`outputs/phase4/`): `data_contract.md`, `assumptions.json` (every input with value, unit, evidence type,
source, note), `tables/` (`monthly_summary`, `totals_summary`, `break_even_summary`, `cost_breakdown`,
`extrapolation`, `sensitivity` CSVs and `draws_sample.parquet`), `figures/` (cost stacks, cumulative-net fans,
break-even histograms, scenario comparison, multiplier effect, tornado, cost share by type) and `PHASE4_SUMMARY.md`.

## Phase 5: dashboard

```bash
pip install -r requirements.txt -r requirements-dashboard.txt   # adds streamlit and plotly
streamlit run src/dashboard/app.py                              # opens http://localhost:8501
```

A five-page dashboard for readers with no technical background, using plain words throughout:
**The big picture** (cost, estimated benefit, running balance and when it pays for itself, for the expected
outlook), **Where the money goes** (costs by type, tagged "Based on trends" or "Our estimate"), **When it pays for
itself** (how often and in which month, the three outlooks side by side), **What matters most** (which choices
move the result) and **Try your own numbers** (reruns the Phase 4 engine on your figures and lets you download
the result). Pages 1-4 read the saved Phase 4 results; page 5 calls `run_engine` live. All on-screen text is in
`src/dashboard/copy.py`; the theme is in `src/dashboard/theme.py`, `styles.css` and `.streamlit/config.toml`.
The currency on screen is Indian rupees, converted from the saved US-currency results at `INR_PER_USD` (RBI reference rate, 16 Nov 2026), set in one place: `src/dashboard/currency.py`.
The shipped company is an example with made-up figures, and every page says so. Notes, the page-by-page summary
and screenshots are in `outputs/phase5/`.

**Navigation (UI v3).** `app.py` builds the pages with `st.navigation(..., position="sidebar")`: a 240 px side panel
with the logo (`src/dashboard/assets/mark.svg`) and product name at the top, the pages under *Forecasts*, *The money*
and *Your own figures* (the current page has a solid 3 px marker and `aria-current="page"`), and the **Word guide**,
**Dark mode**, **Reduce motion** and the rupee rate note at its foot. From 641 to 1024 px it becomes a 76 px icon
rail; at 640 px and below it folds away behind a **Menu** button. The example-company banner stays at the top of
every page.

**Your own figures and the PDF report.** On *Try your own numbers*, **Update results** runs the engine on the
visitor's figures for every outlook and caution level, plus the "what matters most" runs (`dashboard.data.run_all`:
the same 5,000 futures, starting number and table functions as `run_phase4.py`, so the example company's inputs give
the saved tables back). When the figures differ from the example's, every results page (Welcome cards, The big
picture, Where the money goes, When it pays for itself, What matters most) shows them, with "Your figures" in the
banner and a note plus a **Back to the example** button in the side panel. They live in that browser session only:
**Reset to example**, Back to the example or a page refresh brings the example back. The forecast pages are about
the public trends and do not change. Next to the month-by-month table download (CSV, unchanged), **Download report
(PDF)** makes a five-page A4 report with the summary, every chart, the figures used and the monthly table
(`dashboard/report_pdf.py`, drawn with matplotlib when the button is clicked).

**Palette and theme switching.** All colours are tokens in `src/dashboard/theme.py` (`TOKENS["light"]`,
`TOKENS["dark"]`, plus `OUTLOOK_COLORS`, `CHART_COLORS`, `LINE_COLORS`): light uses a warm off-white page
`#FBF7F0`, ink text `#1C2230`, a deep blue primary `#1F4E8C`, a marigold accent `#E8A33D` and a soft tint `#FBEBD0`;
dark uses ink navy `#141A24` with cream text `#F3EEE5`. Headlines are Fraunces (serif), body text Inter. Streamlit
cannot switch its own theme per visitor, so `.streamlit/config.toml` fixes its built-in theme to the light palette
and the **Dark mode** switch (or `?theme=dark` in the address) swaps the CSS custom properties that
`components.inject_css` writes from those tokens; `styles.css` repaints every widget Streamlit draws (pop-ups,
drop-down lists, buttons, inputs) from the same properties. `python -m dashboard.colour_check` (from `src/`) checks
every text and chart colour for contrast and colour-blind separation; `tests/test_ui_contrast.py` measures the
rendered widgets in a browser (skipped when Playwright is not installed).

## Live website and automatic updates

The dashboard is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud) straight from this repository:
entry point `src/dashboard/app.py`, branch `main`, Python 3.11. Every push to `main` redeploys the site on its own
within a few minutes, so a change merged on GitHub is live without any other step. The cloud installs
`src/dashboard/requirements.txt` (the website's packages, pinned to the versions it was tested with) and reads
`.streamlit/config.toml` for the theme. The site needs only what is in the repository: the cleaned data in
`data/processed/` and the saved results in `outputs/phase1` to `outputs/phase4`.

Not in the repository (see `.gitignore`): the raw downloads (`data/raw/`, `ai-workforce-intel/data/`, about 4 GB;
re-create them with `ai-workforce-intel/src/download.py` and the `prep_*.py` scripts), the two request-level
tables built from them (nothing in Phases 1 to 5 reads them), and the Colab zip (rebuild it with
`python src/make_colab_bundle.py`).

## Colab notebooks (one per phase)

| Notebook | Executed copy (open to present without running) | Covers |
|---|---|---|
| `TSAF_Phase1.ipynb` | `TSAF_Phase1_executed.ipynb` | data overview, exploration, baselines |
| `TSAF_Phase2.ipynb` | `TSAF_Phase2_executed.ipynb` | forecasting models and backtests |
| `TSAF_Phase3.ipynb` | `TSAF_Phase3_executed.ipynb` | simulated paths and the standard forecast table |
| `TSAF_Phase4.ipynb` | `TSAF_Phase4_executed.ipynb` | Monte Carlo cost and value engine, break-even, try-your-own-numbers panel |
| `TSAF_Phase5.ipynb` | `TSAF_Phase5_executed.ipynb` | the dashboard: screenshots of each page, the numbers behind the main cards (Streamlit itself runs locally) |

The phase notebooks supersede the earlier combined `TSAF_Phases_1_2.ipynb` (kept unchanged for reference).
All of them use one bundle, `ai-workforce-intel_colab.zip` (code, tests, the processed files the
phases need, `reports/`, and the finished `outputs/phase1-4`, the Phase 5 screenshots, `config/`, the dashboard code); each notebook needs only that zip.

```bash
python src/make_colab_bundle.py        # -> ai-workforce-intel_colab.zip (checks Phase 1 and 3 run from a fresh unzip)
python src/_build_colab_notebook.py    # -> TSAF_Phase1..5.ipynb (--phases 5 for one)
pip install -r requirements-dev.txt    # nbformat / nbclient, only for building and testing the notebooks
```

Shared cells live in `src/_nb_common.py`; the sections in `src/_nb_parts_12.py`, `src/_nb_parts_3.py`, `src/_nb_parts_4.py` and `src/_nb_parts_5.py`.
In Colab: *File > Upload notebook*, then *Runtime > Run all* and upload the zip when asked (or unzip
it from Google Drive, see the commented line in the setup cell). The settings cell at the top has
`MODE = "show"` (default: display the finished results, under a minute) or `MODE = "run"` (recompute
this phase only, using the earlier phases' results in the zip; `RUN_FAST`, `DRIVERS`, and
`WITH_LSTM` in Phase 2). Rebuild the zip whenever the outputs change.
