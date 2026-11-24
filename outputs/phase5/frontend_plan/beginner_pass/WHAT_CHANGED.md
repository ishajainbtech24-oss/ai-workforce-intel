# Beginner pass: what changed

Goal: a visitor with no background in forecasting, statistics or data can open the dashboard, find their way, read
every chart and understand what the results mean, without help. The look stays premium; no engine, forecast,
number, Phase 1 to 4 output or package changed. The list of problems found is in `IMPROVEMENTS.md`.

## 1. Every chart explains itself (all 9 pages, every chart)

A three-line guide sits under each chart: **What you see**, **What it means**, **Why it matters**. "What it means"
is filled in from the same saved numbers the chart draws (`src/dashboard/explain.py`), for example:

- Welcome: "Prices are expected to rise by 1.5% over the next 12 months, to about 29% above their December 2000 level."
- The big picture: "In the expected outlook money is tied up all year: the balance is lowest at -₹1.56 Cr in month 6
  and ends at -₹91.0 L. Only the optimistic outlook pays for itself, in month 11."
- What we expect next (pay levels): "Pay levels: expected to rise by 6.8% over the next 8 quarters. The likely range is
  narrow (about 1.6% either side by the end)." Why it matters: "Pay levels set what staff and engineers cost, so they
  drive training and support, setup work and the value of the time people save."
- How reliable it is (hosting prices): "The real value landed inside the range given at the time 0 of 6 times. The
  prediction was too low most of the time."

The bottom-of-page "How to read this" boxes are gone; the guides replace them.

## 2. Numbers carry their meaning

- Price and pay levels are explained as changes ("about 29% above December 2000", "+6.8% from the latest real value").
- "67% smaller miss" now also reads "our misses were about a third the size of the simple guess's".
- How wide a range is, in words: narrow, moderate, wide or very wide ("wider than the expected value itself").
- Strengths read as strong / moderate / weak in sentences.

## 3. Forecasts in everyday language

Direction (expected to rise / fall / stay about the same), size of the change, width of the likely range, and what the
trend feeds in the money results, checked against the engine code:
pay levels -> training and support, setup work and the benefit; hosting prices -> technology running costs; AI usage per
day -> AI usage cost; the other four trends are background only, and the page says so.

## 4. Guidance where it is needed

- **"What do these words mean?"** button in the top bar on every page: 13 everyday words with special meanings
  (running balance, likely range, outlook, estimate, held back, approach, trend, repeating pattern, unusual point,
  points, lakh and crore, ...).
- Hints (ⓘ) on every choice: outlook, likely range / typical case, which trend, show the next, 3D / flat view, show every approach.

## 5. Facts kept apart from suggestions (The big picture)

**What the data shows** (three findings from the results) and **Ideas to consider**, marked "Suggestions based on the
results above. They are not results themselves.", each tied to a number: start with time saved per person (₹67.8 L
swing); keep training and support under watch (65% of spending); plan for up to ₹1.56 Cr tied up; try a longer project
length (shown only while the expected outlook does not pay back within the year).

## 6. Deeper detail on request

A closed **"Explore technical details"** panel on What we expect next, How reliable it is, The data we used, When it
pays for itself and What matters most. It names the technical terms (for example ARIMA, MAE, MASE, cross-validation, STL,
80% prediction interval, Monte Carlo) and explains each in the same line; How reliable it is also lists every approach
with its technical name and scores. These panels are the only place technical words appear; the word scans still cover
everything else.

## 7. 3D motion (each with a still version)

| Piece | Where | Made with | Still version |
|---|---|---|---|
| Glass 3D banner with the headline (back) | Welcome | Three.js | gradient banner with a still ring |
| **Forecast cone** (new): the past as a line, the future as a cone whose width at each step is the saved likely range; turns slowly, drag to turn | What we expect next | Three.js | the same shapes drawn flat |
| **3D pattern bars** (new): raised bars, highest one in teal, lift on hover | The data we used, Repeating pattern | CSS 3D | flat chart (one click), still bars with Reduce motion |
| Year-end balance columns | The big picture (panel) | Three.js | plain bars |
| Cost donut | Where the money goes | Three.js | flat donut |
| Depth bars | What matters most | CSS 3D | same bars without motion |
| Background orbs | every page | CSS | hidden on phones |

Rules kept: one moving WebGL scene at a time (the one most on screen), paused when off screen or the tab is hidden,
everything cleaned up when the page changes; Reduce motion, no WebGL or a blocked 3D library all show the still versions.

## Files

New: `src/dashboard/explain.py`, `src/dashboard/copy_technical.py`, `tests/test_beginner_pass.py`.
Changed: `copy.py` (all new words), `components.py` (guide, glossary, technical panel, cone and pattern-bar wrappers),
`components_3d.py` (cone, pattern bars), `logic.py` (ideas), `logic_forecasts.py` (size words, grain), `theme.py`
(3D palette colours), `styles.css`, every page in `views/`, and three test files (the word scan skips only the technical
panels; two page checks follow the new layout).
