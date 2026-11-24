# Phase 5 design notes

## What I found (before building)

- `src/`: Phase 1-4 code (`tsaf/` with the forecasting models under `tsaf/models/`, `engine/` with
  `run_engine`, `summarise`, `load_drivers`, `load_inputs`, `validate`), notebook builders and the bundle script.
  There is no `src/models/` folder; the forecasting models live in `src/tsaf/models/`.
- No earlier dashboard or Streamlit code remains anywhere in the project.
- `outputs/phase4/tables/`: `totals_summary.csv`, `break_even_summary.csv`, `monthly_summary.csv`,
  `cost_breakdown.csv`, `sensitivity.csv`, `extrapolation.csv`, `draws_sample.parquet` (expected outlook only).
  `outputs/phase4/assumptions.json` lists every input with its note.
- `config/example_company.json`: the illustrative example company (every value flagged `illustrative`).
- Results at the example inputs (from `PHASE4_SUMMARY.md`): the expected outlook does NOT pay for itself within
  12 months; only the optimistic outlook does (month 11); training and support is about two thirds of the cost;
  technology running costs and AI usage are small and steady; the time-saved outlook and the share of saved time
  that becomes value move the result most.
- Packages: plotly 7.1 was installed; streamlit was missing and was installed (1.67, supports `st.navigation`
  with a top position, `st.segmented_control`, `st.popover`); Playwright was installed but its Chromium was not,
  so `playwright install chromium` was run for the browser test.

## Decisions

- **Data layer** (`data.py`): pages 1, 2 and 4 read the saved Phase 4 tables. The month-by-month distribution of
  when the programme pays for itself (page 3) is not stored in Phase 4, so it is recomputed with the same engine
  call Phase 4 used (5,000 runs, the same fixed starting number, the example inputs); a test checks that its share
  of "pays for itself" equals the saved table exactly. Page 5 calls the engine live (2,000 runs).
- **Wording**: every on-screen string lives in `copy.py`; engine names map to plain labels in one place.
- **KPI cards** are plain HTML in the page (responsive, readable without JavaScript); a tiny script in a hidden
  component adds the count-up and the hover tilt, and does nothing if the browser prefers reduced motion.
- **Hero**: Three.js r160 loaded as an ES module from jsDelivr (pinned `three@0.160.0`; r160 no longer ships the
  old `three.min.js` file), drawn over a CSS gradient that is always present, so a blocked download leaves the
  gradient and no error text. Paused when the tab is hidden; skipped for reduced motion.
- **Navigation**: `st.navigation(position="top")` with five file pages in `src/dashboard/pages/`.
- **`copy.py` and the standard library**: Streamlit puts the script folder on the import path, and a file named
  `copy.py` there could shadow Python's own `copy` module. `app.py` removes its own folder from the import path
  and imports the module as `dashboard.copy`.
- Plotly's toolbar is hidden (its tooltips are technical) and every hover label is written explicitly.

## Deviations from the Phase 5 prompt

- `src/models/` does not exist (the forecasting models are in `src/tsaf/models/`); nothing there is touched.
- Page 3's month-by-month chart is recomputed live with the Phase 4 settings (see above) because Phase 4 saved
  only its summary, not the per-month counts.
- The engine needs no change: `run_engine`, `summarise`, `load_drivers` and `validate` are called as they are.
- A project `.streamlit/config.toml` sets the indigo theme (so selected controls are not Streamlit's default red)
  and the viewer toolbar; it is only read when the app is started from the project folder.
- `components.html` and `use_container_width` are deprecated in Streamlit 1.67: the dashboard uses `st.iframe`
  (falling back to `components.html` on older versions) and `width="stretch"`; `requirements-dashboard.txt` asks
  for streamlit 1.50 or newer.

## Changes made after looking at the screenshots

- Streamlit's toolbar was hidden too broadly and took the page navigation with it; only the menu, deploy button
  and status are hidden now, and the content starts below the sticky header.
- Chart legends moved under the charts and the chart cards lost their inner padding: on a phone the legend had
  covered the title and the last month was cut off.
- The "Not within 12 months" bar label is split over three lines and kept horizontal.
- KPI values that are words ("Not within 12 months") use a smaller size so they fit on one line.
- The 3D shape moves to the lower right and shrinks on narrow screens so it never sits behind the headline.
- Donut slices under 3% have no label (the amount is in the hover text).
