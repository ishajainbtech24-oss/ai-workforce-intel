# Phase 5D, step B: read-only loaders and forecast helpers

No page changed in this step: it adds the plumbing that steps C to E draw on. Nothing writes to any file.

## Added

- `src/dashboard/data.py`: `phase_table(phase, name)` (outputs/phase1 to 3 tables), `forecast_series()` (series with a
  saved forecast, in page order), `history(name)` (the real series, loaded with the project's own
  `tsaf.loaders.load_driver`, so it is exactly what Phases 1 to 3 used: same window, nothing filled). All raise `Missing`.
- `src/dashboard/logic_forecasts.py` (pure, no Streamlit): likely range (10th to 90th percentile of the 200 saved
  futures), `saved_horizon`, `horizon_options` ("show the next ..." = shorter cuts plus the saved length, never more),
  `cut`, `future_x` (future dates/steps), `step_label` ("Day 88", "Q4 2026", "3 Jul 2024"), `series_facts`, `amount`
  (Indian style: lakh / crore), `chosen_approach`, `past_check`, `average_miss`, `range_hits`, `ranking`, `approach_label`.
- `src/dashboard/copy.py`: plain names and one-line descriptions of the 7 series, two groups ("Pay and prices",
  "AI use"), plain names of all 23 approaches (the engine names stay only as dictionary keys), the "no calendar dates" note.
- `tests/test_phase5d_loaders.py`: 35 tests (all 7 series where it applies).

## Facts the helpers return (from the saved files)

| Series | Real data | Saved forecast | Choices | Chosen approach (plain) | Smaller miss than simple repeat |
|---|---|---|---|---|---|
| Pay levels | Q1 2001 to Q3 2026, 103 | Q4 2026 to Q3 2028 | 4, 8 quarters | Statistical pattern finder | 81% |
| Technology hosting prices | Dec 2000 to Oct 2026, 311 | Nov 2026 to Oct 2027 | 3, 6, 12 months | Blend of several approaches | 67% |
| AI usage per day | Day 1 to 87 | Day 88 to 101 | 7, 14 days | Blend of several approaches | 23% |
| AI usage through apps | Day 1 to 87 | Day 88 to 101 | 7, 14 days | Blend of several approaches | 23% |
| AI usage in chat | Day 1 to 87 | Day 88 to 101 | 7, 14 days | Blend of several approaches | 3% |
| AI requests per hour | Hour 1 to 2,088 | Hour 2,089 to 2,256 | 24, 72, 168 hours | Blend of several approaches | 8% |
| Chat conversations per day | 4 Mar to 2 Jul 2024, 121 | 3 to 16 Jul 2024 | 7, 14 days | Average of the same weekday in the last three weeks | 7% |

## Found while building (needs a decision in step D)

- Two saved "inside the likely range" counts exist and can differ: Phase 2's own range on its held-back stretch
  (`holdout.csv`) and Phase 3's check after the range was set (`interval_check.csv`). For pay levels they are 3 of 4 and
  1 of 4; for hosting prices 0 of 6 and 2 of 6. Step D must say on screen which one is shown (the plan's mock-up shows both).
- The daily chat series saves only the month in `calendar_month`, so future days are counted on from the last real day
  (3 to 16 Jul 2024, as the Phase 3 summary states).
