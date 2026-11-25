# AI Workforce Investment Intelligence (CS3216 TSAF)

**Live website: https://ai-workforce-intel.onrender.com** (updates itself on every push to `main`; the free
service sleeps when idle, so the first visit after a quiet spell takes about a minute)

## Quick start

```bash
pip install -r src/dashboard/requirements.txt
streamlit run src/dashboard/app.py
```

The website needs only what is in this repository (processed data, saved results and `artifacts/`). To rebuild the
results from the data: `python src/run_phase1.py`, `run_phase2.py`, `run_phase3.py`, `run_phase4.py`, then
`python src/build_artifacts.py` (details per phase below). Method, limits and data sources are explained on the
site's *How we forecast* page.

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
pip install -r src/dashboard/requirements.txt    # the website's packages, pinned (Streamlit 1.67, Plotly, openpyxl ...)
streamlit run src/dashboard/app.py               # opens http://localhost:8501
python -m pytest -q                              # all tests, about 4 minutes (browser checks need Playwright)
```

Ten pages for readers with no technical background, in plain words throughout, each chart followed by
*What you see / What it means / Why it matters*:

| Group | Page | What it answers |
|---|---|---|
| | Welcome, The big picture | cost, estimated benefit, running balance and payback for the company shown |
| Forecasts | The data we used, What we expect next, How reliable it is, How we forecast | the seven public trends, their forecasts with calibrated ranges, how well those held on the past, and the method, limits and sources |
| The money | Where the money goes, When it pays for itself, What matters most | cost by type, payback chance and month, NPV / return on cost / cost per person, which inputs matter, what it would take |
| Your own figures | Try your own numbers | reruns the engine on your figures; PDF memo, Excel summary, CSV and a scenario file |

**Code layout** (`src/dashboard/`): `app.py` (navigation, theme, first-visit tour, error boundary), `app_pages/` (one
file per page), `ui/` (shared components, charts, all on-screen wording in `copy.py` and `copy_technical.py`, theme,
styles, PDF and Excel builders, Analyst mode), `core/` (data loading, page logic, view state, presets, decision
figures, Analyst-mode files). Every page is built from the shared components (`page_header`, `insight_row`,
`chart`, `kpi_card`, `scenario_bar`, `empty_state` ...); every chart has *View as table* and *Download these numbers*,
and the camera icon saves it as PNG.

**One view, one link.** Company (example, small team, enterprise), outlook and caution level are chosen in the bar
above the charts on every Money page; the trend in a grouped picker on the Forecast pages. All live in
`core/state.py` and are mirrored to the address, so a copied link reproduces the view, e.g.
`/timing?preset=small&outlook=optimistic&caution=more` or `/forecast?trend=pay`. `?analyst=on`, `?theme=dark` and
`?tour=off` work the same way.

**Analyst mode** (switch in the side panel, off by default) adds the statistics behind each trend: STL
decomposition, ADF/KPSS verdict, ACF/PACF, subseries, CUSUM break test, outliers; and behind each forecast: model
cards, rolling-origin cross-validation (MAE, RMSE, MASE, bias, coverage), Diebold–Mariano tests, error by step,
residual checks (Ljung–Box, Q–Q) and a coverage plot. All of it is precomputed by `python src/build_artifacts.py`
into `artifacts/` (committed, about 0.5 MB); nothing is fitted on a page load.

**Calibrated ranges.** The likely range on every forecast is a split-conformal range calibrated on earlier
cross-validation folds; its 80% coverage in rolling-origin CV is 71–86% for all seven trends (shown on *How reliable
it is*). **Input uncertainty.** The cost engine varies time saved, conversion to value, adoption level and training
hours in every draw (PERT ranges in `src/config_phase4.py`), on top of the forecast paths, so payback is a real
probability. Every change to a forecast or money figure is logged with before and after values in
`docs/CHANGELOG.md`; design choices are in `docs/DECISIONS.md`.

**Your own figures.** *Update results* runs the engine for every outlook and caution level; every results page then
shows your figures until *Back to the example*. Nothing is stored on the server: results live in the browser
session, and the scenario file you save stays on your computer (load it again on the same page). Downloads: PDF
report with a decision-memo first page, Excel decision summary, month-by-month CSV, scenario file (JSON).

**Settings.** None are needed; see `.env.example` (`TSAF_DASH_ROOT`, `AIWI_TOUR`, `AIWI_STRICT`). Money is shown in
Indian rupees converted at one fixed rate set in `src/dashboard/core/currency.py`. The theme follows the visitor's
system setting on the first visit; *Dark mode* and *Reduce motion* are in the side panel.

**Tests and CI.** `.github/workflows/ci.yml` runs the whole suite on every push and pull request: engine and
forecasting units, a render of every page with Streamlit's AppTest (a page error fails the run), copy rules (no
jargon outside the technical panels), currency, PDF/Excel/scenario file, and browser checks with Playwright:
contrast in both themes, side navigation, and accessibility at 375 / 768 / 1280 px (no sideways scrolling, one main
heading, named controls, visible keyboard focus).

**Load times** (measured 25 Nov 2026, page shown with its first chart): on a laptop, the first page after the
server starts about 3 s, other pages 0.3–1.4 s. On the live free Render service (0.1 CPU): the first page after a
deploy took 29 s while the saved results load once, every later page about 3 s, and Welcome in a new session about
9 s. After 15 idle minutes the service sleeps; waking it adds up to about a minute to the first visit.

## Live website and automatic updates

The dashboard is deployed on [Render](https://render.com) as a free web service described in `render.yaml`:
Render installs `src/dashboard/requirements.txt` (the website's packages, pinned to the versions it was tested with),
starts Streamlit on its port with a health check at `/_stcore/health`, and rebuilds and redeploys on every push to
`main` (about a minute), so a change merged on GitHub is live without any other step. The theme comes from
`.streamlit/config.toml`. (`app.py` can also pick up changed code without a restart, on hosts that pull each push into the running app.) The site needs only what is in the repository: the cleaned data in
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
