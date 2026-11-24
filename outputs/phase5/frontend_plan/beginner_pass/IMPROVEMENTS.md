# Beginner pass ("idiot-proof" review): what could confuse a first-time visitor, and the fix

Reviewed: all nine pages, every chart, number, control and message (`src/dashboard/copy.py` holds every word on
screen; each page in `src/dashboard/views/`). Most technical words were already gone. What remains is less about
jargon and more about **meaning**: charts that do not say what they show or why it matters, numbers without a
comparison, controls without a hint, and no place for deeper detail.

## What a beginner would stumble on

| # | Where | What could confuse | Fix |
|---|---|---|---|
| 1 | Every chart (16 of them) | The explanation of each chart sits in one collapsed "How to read this" box at the bottom of the page, not next to the chart. Nothing says what the pattern means or why it matters. | A short three-line guide under every chart: **What you see**, **What it means** (a sentence filled in from the real numbers), **Why it matters**. The bottom boxes go, so nothing is said twice. |
| 2 | Welcome and What we expect next | "128.8 points" and "Price level (December 2000 = 100)": a level means nothing without a comparison. | Say it as a change: "about 29% higher than in December 2000" and "+1.5% from the latest real value". |
| 3 | Pay levels | A level of 190.2 says nothing by itself. | Only changes are shown and explained ("6.8% higher than the latest real value"). |
| 4 | What we expect next | The forecast says where it goes, not what it means. | Add the direction in words (rising, falling, about flat), how wide the likely range is in words (narrow, moderate, wide), and **what it feeds** in the money results (pay feeds training, setup and the benefit; hosting prices feed technology running costs; AI usage per day feeds AI usage cost; the four other trends are background only). |
| 5 | How reliable it is | "67% smaller miss" is hard to picture. | Add the same thing as a size: "our misses were about a third the size of the simple guess's". |
| 6 | Controls | Outlook, "Which trend", "Show the next", "Likely range / Typical case only", "3D view / Flat view", "Show every approach" have no hint. | A short hint on each (the ⓘ next to the label). |
| 7 | Words such as outlook, running balance, likely range, estimate, held back | Explained only in the About box at the bottom of each page. | A **"What do these words mean?"** button in the top bar, on every page, with the full glossary. |
| 8 | The big picture | Findings and advice are mixed, and the page does not say what a business could do next. | Two labelled blocks: **What the data shows** (facts from the results) and **Ideas to consider**, marked as suggestions, each tied to a number on the page. |
| 9 | Pages with deeper analysis | No way to see how the results were produced without reading code. | An **"Explore technical details"** panel, closed by default, on What we expect next, How reliable it is, The data we used, When it pays for itself and What matters most. Every technical term in it is explained in the same sentence. |
| 10 | Visual depth | Only four 3D pieces left after the big-picture clean-up. | Three more, each with a still version: the glass 3D banner back at the top of Welcome; a **3D forecast cone** on What we expect next (the past as a line, the future as a cone that widens with the likely range, drag to turn); **3D pattern bars** on The data we used. Still one moving scene at a time; Reduce motion and no-WebGL give the still versions. |

## Rules kept

- Every new sentence is filled in from the saved results; suggestions are labelled as suggestions.
- No number, forecast, engine or backend changes; the Phase 1 to 4 outputs stay untouched.
- The banned-word scan still covers every page. Only the closed "Explore technical details" panels may name
  technical terms, and each one is explained where it appears.
- No filler: one short guide per chart, no new pages.
