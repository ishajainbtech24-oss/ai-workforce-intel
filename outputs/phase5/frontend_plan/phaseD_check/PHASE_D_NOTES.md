# Phase 5D, step D: "How reliable it is"

Second page in the **Forecasts** menu (after What we expect next). No engine, model, forecast, Phase 1 to 4 output or
package changed; the page only reads saved Phase 2 and 3 tables.

## What the page shows (for the trend picked at the top; default: technology hosting prices)

- **Verdict in one sentence** from the final held-back stretch (Phase 2 `holdout.csv`, the approach Phase 2 chose),
  e.g. "Over the last 6 months we held back, the prediction missed by about 2.5 points on average, about 2.0% of the
  typical level."
- **Three tiles**
  1. Average miss (2.5 points; typical level 125.8 points).
  2. Real value inside the likely range: the **Phase 3** count, i.e. the range used on What we expect next (2 of 6),
     with the **Phase 2** count of the first prediction's own range under it (0 of 6). This settles the step B question:
     both are shown, each named for what it is. The page does not claim Phase 3 "widened" the range, because for pay
     levels it did not (Phase 2: 3 of 4; Phase 3: 1 of 4).
  3. Compared with simply repeating: how much smaller the chosen approach's average miss was than the simple yardstick
     over the earlier checks (67% for hosting prices; 81% pay; 23% usage per day and through apps; 8.4% hourly requests;
     6.8% chat conversations; 3.3% usage in chat).
- **Chart**: recent real values, a "Prediction made here" divider, what was predicted (dotted), the range given with
  the prediction (band), and a dot per held-back real value (green inside, amber outside). The amber note from
  What we expect next repeats under it when Phase 3 flagged the range.
- **Which approach came closest**: horizontal bars of the average miss over earlier checks (`leaderboard.csv`, approaches
  that ran, sorted by `cv_mae`), closest at the top; the approach used in indigo and the simple yardstick in amber. The
  first 8 plus the yardstick by default; "Show every approach" lists all. Notes underneath when several approaches were
  almost equally close (within 5%), and how many approaches could not run on the data.
- Plain names only (for example "Blend of several approaches", "Statistical pattern finder", "Repeat the same weekday
  last week"); the engine names live only as dictionary keys in `copy.py`.

## What the saved results say (worth knowing before a review)

- In all 7 trends the approach Phase 2 chose also had the smallest average miss in the earlier checks.
- The usage and chat trends are hard to predict: on the held-back stretch the miss is 43% to 73% of the typical level
  (pay 0.7%, hosting prices 2.0%). The page states this plainly.

## Fixed along the way

- Plotly adds markers to traces with under 20 points unless told otherwise, so short shaded ranges showed stray dots and
  a dot in the legend. All bands are now lines only (also on What we expect next and Welcome; a test checks it).
- Ranking labels on the points scale use two decimals, so 0.57 and 0.61 no longer both read "0.6".

## Checks

- `tests/test_phase5d_reliability.py` (30 tests): ranking order and values equal `leaderboard.csv`; chart bars, labels,
  colours and the short/long list; every number equal to the Phase 2 / 3 tables; past-check chart equal to `holdout.csv`
  with the right inside/outside counts; rendered page text for all 7 trends free of approach names, metric abbreviations
  and other technical words (a stricter word list than the banned-word scan); bands without markers.
- Full suite: 252 passed.
- Browser (`browser_check_D.json`, screenshots here): fresh server with the page opened directly as the first request;
  1440, 768 and 390 px, light and dark; switching to "Chat conversations per day" and "Show every approach" (9 -> 18
  bars); banner and styles on every view, no sideways scroll, no "$", no technical words in the page text, Forecasts
  menu marked active, Next card leads to Where the money goes, no page or console errors.

## Not done (as planned)

- The earlier rolling checks (`cv_folds.csv`) are not drawn; the plan lists them as a later "Show earlier checks"
  option.
