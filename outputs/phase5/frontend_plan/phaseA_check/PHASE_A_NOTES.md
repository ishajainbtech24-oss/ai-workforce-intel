# Phase 5D, step A: Welcome page, menu groups, "Next" cards

Implements step A of `../FRONTEND_DESIGN_PLAN.md` (section 16). No engine, model, forecast, Phase 1 to 4 output or
package changed; the new code only reads saved files.

## What changed

| File | Change |
|---|---|
| `src/dashboard/pages/welcome.py` (new) | Welcome page: promise, "Explore the results" (goes to The big picture), "How it works" (jumps down the page), real chart of hosting prices, three steps, three headline numbers, How to read this |
| `src/dashboard/charts_forecast.py` (new) | What happened (solid) / Today line / what we expect (dashed) / likely range (band) chart |
| `src/dashboard/logic_forecasts.py` (new) | Pure helpers: likely range = 10th to 90th percentile of the 200 saved simulated futures; Welcome chart data |
| `src/dashboard/data.py` | Two read-only loaders: `processed(name)` (data/processed) and `saved_forecast(series)` (outputs/phase3/forecasts); both raise `Missing` |
| `src/dashboard/app.py` | Welcome is the first page; the three money pages are grouped under "The money" menu; a "Next" card under each page |
| `src/dashboard/components.py` | `PAGE_FILES`, `next_card`, `section_marker`; the motion script marks "The money" as active when one of its pages is open |
| `src/dashboard/copy.py` | All new text (Welcome, legend, Today, Next lines, menu name) |
| `src/dashboard/styles.css` | Menu group, Welcome hero, buttons, chart title, Next card, three-card row |
| `tests/test_phase5d_navigation.py` (new) | 6 tests: likely range equals the saved percentiles; chart draws the saved values; Welcome shows the Phase 4 numbers and the chart note; Next cards walk all pages in order; menu groups declared; missing files raise `Missing` |
| `tests/test_phase5_dashboard.py`, `tests/test_currency.py` | `PAGES` now starts with Welcome; the two overview-card tests open The big picture explicitly (it is no longer the first page) |

## Numbers on the Welcome page (all from saved files)

- Hosting prices: last 36 months of `data/processed/ppi_hosting_monthly.csv`; expected 128.8 by Oct 2027, likely between
  127.0 and 131.3 (`outputs/phase3/forecasts/ppi_hosting_monthly.csv`, central line and 10th/90th percentile of 200 futures).
- Total cost ₹2.61 Cr, estimated benefit ₹1.7 Cr, pays for itself: Not within 12 months (optimistic outlook: month 11)
  (`outputs/phase4/tables/totals_summary.csv`, `break_even_summary.csv`, expected outlook, standard caution).

## Browser check (`browser_check_A.json`, screenshots in this folder)

Chromium via Playwright, 1440, 768 and 390 px, light on every page, dark on Welcome and Where the money goes
(24 page views): banner on every page; no sideways scroll; no "$" in the page text; a Next card on every page except
Try your own numbers (the last one); no page or console errors. Picking "When it pays for itself" from "The money" menu opens
`/timing` with the menu marked active; "Explore the results" opens `/overview`; "How it works" scrolls to the steps.
On phones the "Pages" button opens a drawer with Welcome, The big picture, Try your own numbers and a "The money" group.

## Known limits / deviations

- Streamlit always puts ungrouped pages before menu groups, so the top bar reads Welcome, The big picture,
  Try your own numbers, The money ▾ (the plan had Try your own numbers last).
- At 768 px Streamlit folds part of the top bar into its own "3 more" item.
- The big picture still opens with the original hero headline, which now repeats the Welcome headline; calming that
  page is step F of the plan.
- Full-page screenshots show only the first screen because Streamlit scrolls inside its own container; the lower
  parts were captured as element screenshots (`welcome_chart_*`, `welcome_numbers_*`, `welcome_next_*`).
