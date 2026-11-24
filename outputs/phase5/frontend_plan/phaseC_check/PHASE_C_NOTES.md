# Phase 5D, step C: "What we expect next"

New page under a new **Forecasts** menu (between The big picture and The money). No engine, model, forecast, Phase 1
to 4 output or package changed; the page only reads saved files.

## What the page shows

- **Which trend**: round pills for the 7 real series (plain names). Default: technology hosting prices, the same trend
  as the Welcome chart.
- **Show the next**: only shorter cuts of the one saved forecast plus its full length (3 / 6 / 12 months; 4 / 8
  quarters; 7 / 14 days; 24 / 72 / 168 hours).
- A one-line plain description of the trend; for the three usage series and the hourly series, the note that the
  source has no calendar dates, so days and hours are numbered.
- Chart: recent real values (solid), a dotted divider labelled **Latest real value** (not "Today": the chat and usage
  data end in 2023 and 2024), what we expect (dashed) and the likely range (band). Counts use lakh and crore, levels one
  decimal; the axis never shows negative counts.
- Side card in words, e.g. "By Oct 2027 we expect about 128.8 points. Likely between 127.0 and 131.3. That is +1.5%
  compared with the latest real value (126.9, Oct 2026)."
- Honest check from Phase 3 (`interval_check.csv`): amber when Phase 3 flagged the range (6 of 7 series), e.g. "...the
  real value landed inside the likely range only 2 of 6 times. Treat the range as narrower than reality."; calm when not
  flagged (AI usage per day and through apps: 14 of 14).
- **Download what we expect**: exactly the rows the chart shows (When, We expect, Likely low, Likely high).

## Fixed along the way (affected pages built before step C too)

1. **First visit to a page address showed a bare page.** A folder called `pages/` next to `app.py` makes Streamlit
   use its old page-folder mode until someone opens `/`: the first visitor who opened e.g. `/costs` directly got that
   page alone, without styles, banner, top bar or Next card. This existed before Phase 5D (earlier checks always opened
   `/` first, which hid it). Reproduced with a two-page test app; fixed by renaming `src/dashboard/pages/` to
   `src/dashboard/views/` (paths updated in `components.PAGE_FILES` and the tests; a guard test stops a `pages/` folder
   coming back). Checked: 7 fresh server starts, each opened one page address directly as the very first request; all
   show styles, banner and top bar (`cold_direct_visits.json`). `outputs/phase5/PHASE5_SUMMARY.md` and `DESIGN_NOTES.md`
   still say `pages/`; they are earlier records and were left unchanged.
2. **Long lines were cut short.** The line draw-on effect used a fixed 3,000 px dash, so lines longer than that (the
   two weeks of hourly requests) stopped part-way. Solid lines are now measured in relative units (`pathLength="1"`,
   set by the motion script) so the whole line always shows; Plotly's dashed lines are left alone; reduced motion still
   turns the effect off.

## Checks

- `tests/test_phase5d_forecast_page.py` (30 tests): headline, range and change text equal the saved forecast at every
  offered length for all 7 series (expected value and 10th / 90th percentile recomputed from the saved futures); chart
  lines equal the saved values and the recent real values; the divider sits on the latest real value; the range note
  uses the Phase 3 counts; the rendered page holds the words, the note and the download; default trend matches the
  Welcome chart; no banned words in text, chart labels or hover text.
- Full suite: 217 passed.
- Browser (`browser_check_C.json`, screenshots here): 1440, 768 and 390 px, light and dark; clicking "AI usage in chat"
  then "7 days" updates the words to "By Day 94 ... 9.3 lakh usage units"; banner on every view, no sideways scroll, no
  "$", Forecasts menu marked active, Next card leads to Where the money goes, no page or console errors. Next-card chain
  checked on every page: Welcome -> The big picture -> What we expect next -> Where the money goes -> When it pays for
  itself -> What matters most -> Try your own numbers.

## Known limits

- The likely range for daily AI usage widens sharply after a few days (up to about 28 crore units by day 101). That is
  what the saved futures say; the page shows it as is.
- At 390 px the top bar is replaced by the "Pages" drawer, so no menu is marked active there (as before).
