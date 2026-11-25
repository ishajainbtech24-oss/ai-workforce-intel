# Audit of the dashboard (Step 0, 2026-11-25)

**One-line summary.** A working nine-page Streamlit 1.67 app that reads saved results from five offline phases, with a
live Monte Carlo engine behind *Try your own numbers*. Most gaps raised in the brief are real, and two observations in
it need correcting (see the last section).

## What is there

| Area | Where | Notes |
|---|---|---|
| Entry point | `src/dashboard/app.py` | `st.navigation` (sidebar, 4 sections), theme + motion switches, banner, footer, eager engine imports |
| Pages (9) | `src/dashboard/views/*.py` | Welcome, overview, data_used, forecast, reliability, costs, timing, levers, your_company; URLs come from file names |
| Shared UI | `components.py` (400 lines), `components_3d.py`, `charts.py`, `charts_forecast.py`, `theme.py`, `styles.css` (432 lines), `assets/mark.svg` | Page title, KPI cards, chart guide ("What you see / means / matters"), glossary, tables, 3D scenes with still fallbacks |
| Words | `copy.py` (588 lines), `copy_technical.py`, `explain.py` | All on-screen text; technical names only in "Explore technical details" |
| Logic | `data.py`, `logic.py`, `logic_forecasts.py`, `currency.py`, `report_pdf.py` | Loaders with `st.cache_data`; session "your figures" layer; INR at 94.1159 per USD; PDF report (matplotlib) |
| Data files read at run time | `data/processed/*.csv` (30 small files), `outputs/phase1-3/tables`, `outputs/phase3/forecasts/*.csv`, `outputs/phase4/tables/*.csv`, `config/example_company.json` | About 90 MB in git; raw downloads and request-level tables excluded |
| Forecast pipeline (offline) | `src/run_phase1..3.py`, `src/tsaf/` | Phase 1 baselines and rolling-origin CV; Phase 2 about 20 models, chosen by CV MASE below seasonal naive; Phase 3 refit plus 200 residual-bootstrap paths per series |
| Finance model | `src/engine/` (`model.py`, `simulate.py`, `sensitivity.py`) | 4 cost lines plus benefit, 5,000 draws × 3 outlooks × 3 caution levels; only the trend paths are random |
| Dependencies | `src/dashboard/requirements.txt` (pinned: streamlit 1.67, plotly 7.1, pandas 3.0.5, numpy 2.4.6, pyarrow 24, matplotlib 3.11.1, scipy, statsmodels 0.15, scikit-learn) | Root `requirements.txt` is for the offline phases |
| Deploy | `render.yaml` (free web service, auto-deploy on push), `.streamlit/config.toml` (light theme, file watcher off) | Free tier: about 0.1 CPU, sleeps after 15 min, ephemeral disk |
| Tests | `tests/` (25 files, 342 tests incl. Playwright contrast/nav) | No CI yet |

## The brief's observations, checked in the code

1. **Technical details are only a glossary.** Confirmed: the panels list terms and approach names. ADF/KPSS, ACF/PACF,
   decomposition and residual tables exist in `outputs/phase1-2/tables` but are not shown.
2. **Under-covering intervals.** Confirmed. Hosting prices: the 80% band caught 2 of 6 hold-out values (`interval_check.csv`).
   Bands come from residual bootstrap without calibration.
3. **Payback is 0% or 100%.** Confirmed: time saved, conversion, adoption and training hours are fixed per run. Only
   wage, hosting and AI-usage paths vary, and their spread is small next to the cost of training.
4. **Model comparison.** Confirmed: errors are in raw units; models that were skipped are summarised as "could not
   run"; the top approaches are within about 5% MASE.
5. **No provenance; pills wrap.** Confirmed.
6. **Try your own numbers.** Confirmed: 13 inputs; no presets, save, compare, link or decision summary.
7. **Render storage.** Respected already: nothing is written to disk; visitor figures live in `st.session_state`.
8. **Icon names in page text.** Partly. Streamlit already marks its icons `aria-hidden="true"`, so screen readers skip
   them. Their names still show when the page text is copied, or when the icon font is late (now hidden until it
   loads). Mobile layout was checked at 390 px earlier; it is now checked again at 375 px.

## Corrections to the brief

- The seven series are **not all monthly**: pay levels (ECI) are quarterly, hosting prices (PPI) monthly, the four
  BurstGPT series daily or hourly with day and hour numbers (no calendar dates), and WildChat daily (Mar to Jul 2024).
  The 6M / 1Y / 5Y / All buttons and shock markers therefore apply to the dated series; the BurstGPT series get an
  equivalent count-based range (last 7 / 30 / all days).
- The hosting-price hold-out has 6 points, so "2 of 6" is a small-sample figure. The calibration target (70-90%
  coverage of the 80% band) is measured on all rolling-origin folds instead.

## Proposed structure (implemented in workstream A, behaviour unchanged)

```
src/dashboard/
  app.py            entry: navigation, theme, shared chrome
  app_pages/        one file per page (was views/; URLs unchanged)
  ui/               components.py (page_header, kpi_card, insight_row, ...), charts.py, theme.py, styles.css, copy.py
  core/             data.py, finance.py (uncertain Monte Carlo, NPV, goal-seek), diagnostics.py, conformal.py,
                    scenarios.py, provenance.py
src/build_artifacts.py   precomputes diagnostics, CV and calibrated intervals into artifacts/
artifacts/          precomputed JSON/CSV loaded at start (no work on the slow host)
docs/               AUDIT, DECISIONS, CHANGELOG, METHODS; screenshots/
tests/              unit tests for core/, one AppTest smoke test per page, browser checks
```
