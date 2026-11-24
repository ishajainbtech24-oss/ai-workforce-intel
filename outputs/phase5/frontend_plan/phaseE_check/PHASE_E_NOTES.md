# Phase 5D, step E: "The data we used"

First page of the **Forecasts** menu (The data we used -> What we expect next -> How reliable it is). Replaces the
"upload" idea from the references: nothing can be uploaded; the page shows the seven real series the forecasts use.
No engine, model, forecast, Phase 1 to 4 output or package changed; the page only reads saved files.

## What the page shows (for the trend picked at the top; default: technology hosting prices)

- A plain description, which part of the source was used and why, the "days are numbered" note for the four sources
  without calendar dates, and, for the AI usage sources, the known one-day outage (Day 78), which is kept and marked.
- **Four tiles**: time span, number of points, unusual points, missing values (all equal to Phase 1's
  `summary_stats.csv` and `anomalies.csv`).
- **Plain summary**: the averages of the first and the last full cycle and the direction, plus Phase 1's trend and
  repeating-pattern strengths as words (strong / some / little), e.g. "The first 12 months averaged about 101.5 points
  and the last 12 about 124.6 points, so the values rose. Long-term trend: strong. Repeating yearly pattern: little."
- **Three tabs**
  1. What happened: every real value used, Phase 1's unusual points (amber dots) and the known outage (x); download of
     the values.
  2. Repeating pattern: the plain average for each month, quarter, weekday or hour. Sources without dates number their
     days and hours (1 = first in the source) and say so.
  3. Unusual points: a short table (when, value, how unusual, higher or lower than usual), the 10 most unusual first
     when there are more (the hourly requests have 394).

## Which part of each source is used (shown on the page)

| Series | Used | In the source | Why |
|---|---|---|---|
| Pay levels, hosting prices | all 103 / 311 | same | official monthly / quarterly records |
| AI usage per day, through apps, in chat | first 87 days | 116 days with values | later days include copies of earlier days and a long run of unusually low activity |
| AI requests per hour | first 2,088 hours | 2,784 hours with values | same reason |
| Chat conversations per day | 121 days | 451 days with values | longest stretch with both chat services present; last day in the file was incomplete |

## Fixed along the way

- **Unusual-point count** (from step B): Phase 1's `anomalies.csv` holds one row for AI usage per day that is a note
  about its day-77 check, not a flagged value. It was counted as 1 unusual point; it now counts 0 (rows without a value
  are left out; a test checks it).
- A count of zero shows as "0", not the word "None" (the earlier screen check treats "None" as a sign of a program value
  leaking onto the page).
- Phone layout: pattern bars are labelled 1 to 7 / 1 to 24 with the meaning in the axis title (the long labels
  overlapped at 390 px); tiles without an icon no longer leave an empty band at the top.

## Checks

- `tests/test_phase5d_data_page.py` (25 tests): tiles equal `summary_stats.csv` for all 7; the check note is not counted;
  the day-number note shows exactly for the four sources without dates; window notes use the real counts (checked
  against the processed file); chart values, unusual points and the outage mark; pattern averages and the summary
  recomputed independently; the most unusual hourly point listed first; no banned or technical words in page text,
  chart labels or hover text.
- Full suite: 282 passed.
- Browser (`browser_check_E.json`, screenshots here): fresh server with this page opened directly as the first request;
  1440, 768 and 390 px, light and dark; switching to "AI usage in chat" and opening every tab; banner and styles on every
  view, no sideways scroll, no "$", no technical words, Forecasts menu active. The Forecasts menu lists the three pages
  in order, and the Next chain runs Welcome -> The big picture -> The data we used -> What we expect next -> How
  reliable it is -> Where the money goes -> When it pays for itself -> What matters most -> Try your own numbers. No page
  or console errors.

## Not done

- The Phase 1 decomposition pictures are not shown: their labels use technical words. The page uses the saved strengths
  (as words) and plain averages instead.
