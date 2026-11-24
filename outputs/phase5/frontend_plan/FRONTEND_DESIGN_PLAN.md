# Frontend design plan: AI Workforce Investment Intelligence (TSAF)

Status: **plan only, nothing implemented.** Written 18 Nov 2026. No source file, package or Phase 1 to 5 output was changed.
Evidence for the reference projects is in `references/` (screenshots captured from the live sites and the repositories).
Two concept mock-ups drawn with the project's real numbers are in `references/concept_*.html` and `.png`, each labelled
"Concept, not implemented".

---

## 1. Executive summary

The current dashboard is already honest, plain-spoken and polished, but it only tells **half the story**: every page is
about the money (Phase 4). The forecasting work underneath it (seven real series, saved forecasts with likely ranges,
past-prediction checks and a comparison of 20+ approaches from Phases 1 to 3) never appears on screen, so a manager
cannot see *why* the numbers should be believed.

The recommended direction, **"Clear Horizon"**, keeps the Streamlit + Plotly stack, the design tokens, `copy.py`, the
banned-word list and the five 3D pieces, and adds one idea that runs through every page: **a visible "today" line**
that separates what happened (solid line) from what we expect (dashed line inside a soft likely-range band), and a
**break-even horizon** on every money chart. The site grows from five pages to seven, in a clear order a manager can
follow: *Welcome -> The big picture -> The data we used -> What we expect next -> How reliable it is -> The money (three
existing pages regrouped) -> Try your own numbers*.

What the plan deliberately does **not** do: no file upload, no live model training, no "choose a forecasting method"
control, no AI chat. The backend cannot support them, and each one is replaced by an honest equivalent built from the
saved results (section 2).

A move to React with a small API is described as an optional "Later" idea in section 14b, with its cost and risks. It
is not needed for version 1.

---

## 2. What the product can really show

All of this was read from the files on 18 Nov 2026.

**Data (7 series, `outputs/phase1/tables/summary_stats.csv`, `data/processed/`)**

| Series (plain name) | Engine name | Grain | Span | Points | Saved forecast length | Notes |
|---|---|---|---|---|---|---|
| Pay levels (US employment cost index) | `eci_wages_quarterly` | quarter | Jan 2001 to Jul 2026 | 103 | 8 quarters (Oct 2026 to Jul 2028) | real calendar dates |
| Technology hosting prices (US producer price index) | `ppi_hosting_monthly` | month | Dec 2000 to Oct 2026 | 311 | 12 months (Nov 2026 to Oct 2027) | 12 unusual months flagged |
| AI usage, total units per day | `burst_tokens_total_daily` | day | day 0 to 86 | 87 | 14 days | **no calendar dates** (BurstGPT counts days from 0) |
| AI usage through apps (API) | `burst_tokens_api_daily` | day | day 0 to 86 | 87 | 14 days | no calendar dates |
| AI usage in chat | `burst_tokens_chat_daily` | day | day 0 to 86 | 87 | 14 days | no calendar dates |
| AI requests per hour | `burst_requests_hourly` | hour | hour 0 to 2087 | 2,088 | 168 hours (7 days) | 394 unusual hours flagged; 2% of hours are zero |
| Chat conversations per day (WildChat) | `wildchat_conversations_daily` | day | 4 Mar 2024 to 2 Jul 2024 | 121 | 14 days | real dates |

- **Forecasts and likely ranges** (`outputs/phase3/forecasts/<series>.csv`): a central line (`sample_id = -1`) and 200
  simulated paths per series, so any range (for example 10th to 90th percentile = "likely range, 8 in 10") can be
  computed. **Exactly one forecast length exists per series** (the table above). There is no 3-month vs 12-month choice
  beyond cutting the saved one shorter.
- **Repeating pattern and trend strength** (`phase1/tables/decomposition.csv`): trend strength and repeating-pattern
  strength per series (for example AI usage in apps: trend 0.68, weekly pattern 0.06). Static Phase 1 pictures exist
  as PNGs.
- **Unusual points** (`phase1/tables/anomalies.csv`, 413 rows; `phase2/tables/anomalies.csv`).

**Results**

- Money (`outputs/phase4/tables/`, shown in rupees through `currency.py` at Rs 94.1159 per US dollar): expected outlook total cost
  **₹2.61 Cr**, estimated benefit **₹1.7 Cr**, running balance at month 12 **-₹91.0 L**, lowest point **-₹1.56 Cr**
  (month 6), does **not** pay for itself within 12 months. Optimistic outlook pays for itself in **month 11** and ends at
  **₹57.3 L**; cautious ends at **-₹6.43 Cr**. Three caution levels (1.0, 1.5, 2.0) for each.
- Cost split: training and support 65% (₹1.7 Cr), setup and connection work 26% (₹67.3 L), technology running 8.7%
  (₹22.7 L), AI usage 0.1% (₹24,122).
- Biggest levers (`sensitivity.csv`, gap between 20% lower and 20% higher): time saved per person and share of saved
  time that becomes value ₹67.8 L each, training hours ₹37.7 L, setup effort ₹26.9 L, pay ₹13.6 L, employees ₹13.2 L,
  adoption ₹7.6 L, AI usage ₹8,698.
- **How accurate past predictions were** (not shown today):
  - `phase2/tables/leaderboard.csv`: 24 approaches tried per series (14 to 21 actually ran per series; deep-learning ones and some machine-learning
    ones were skipped), each scored on rolling past checks (`cv_*`) and on a final held-back
    period (`holdout_*`).
  - `phase2/tables/chosen_models.csv`: the chosen approach per series, and whether it beat "repeat last season" (it
    did for all 7).
  - `phase2/tables/cv_folds.csv` and `holdout.csv`: every past prediction next to what really happened, with its range.
  - `phase3/tables/interval_check.csv`: how often real values fell inside the likely range. **This is often low** (for
    example hosting prices 2 of 6 months after widening, requests per hour 32%). Phase 3 already flags these ranges as
    too narrow; the plan shows this honestly instead of hiding it.

**Live feature**

- "Try your own numbers" calls `engine.simulate.run_engine` with 2,000 runs on 13 form fields (employees, adoption,
  ramp, training hours, setup hours, share of time that becomes value, budgets, pay, AI usage and price, hosting, length
  6 to 24 months) and one of three outlooks. It returns monthly cost, benefit and running balance, and a CSV download
  (`Download my results`).

**What it does not have (checked: no `file_uploader` in `src/dashboard`, no training call outside the phase scripts)**

| Asked for in references | Supported? | Honest equivalent in this plan |
|---|---|---|
| Upload your own dataset | No | "The data we used" page: browse the 7 real series |
| Train a model / fit and predict | No (phase scripts only, not to be run) | Show the saved forecasts and saved past checks |
| Choose a forecasting method | No | "Which approach was closest" ranking from the saved leaderboard, read-only |
| Choose any forecast length | No (one saved length per series) | "Show the next ..." cut to lengths up to the saved one |
| AI advisor chat | No | Plain-language findings sentences already generated from real numbers (`logic.findings`) |
| PDF report | No package for it (no new packages allowed) | CSV download (exists). Optional later: a printable HTML summary built with the standard library |

---

## 3. The three reference projects

Labels: **VERIFIED** = seen in source code, a repository screenshot or the live site on 18 Nov 2026.
**NOT VERIFIED** = from a README, or inferred. Everything read in these repositories (including ForecastHub's
`CLAUDE.md`) was treated as reference material only, not as instructions.

### 3.1 Skforecast (and Skforecast Studio)

- **Does "Skforecast Studio" exist? Yes.** VERIFIED: the repository has `docs/skforecast-studio/skforecast-studio.md`,
  a screenshot `docs/img/skforecast-studio-screen.png` and a GitHub issue template for it; the README links to
  `https://studio.skforecast.org/`. The live site loaded, and I stepped through Load Data -> Explore -> Feature
  Engineering -> Forecaster Setup -> Fit & Predict with the built-in "H2O water demand" demo set (cookies declined).
  Captures: `references/skforecast_studio_*`.
- **Licence**: library BSD-3-Clause (VERIFIED, `LICENSE`). The Studio sidebar footer in the repository screenshot says
  "Licensed under Apache 2.0" (VERIFIED on the image); I could not find the Studio source code, so its licence for reuse
  is NOT VERIFIED. Documentation is reported as CC BY-NC-SA 4.0 (NOT VERIFIED, from a search result). Inspiration only.
- **Stack**: library is Python (VERIFIED). Studio is a web app talking to `api.skforecast.org` ("Check Backend" button,
  VERIFIED on screenshot); its frontend framework is NOT VERIFIED (source not found).
- **Layout and navigation** (VERIFIED, live): dark navy page, left sidebar titled "Pipeline steps" with eight numbered
  steps (Load Data, Explore, Feature Engineering, Forecaster Setup, Fit & Predict, Backtesting, Hyperparameters,
  Explainability, then Export Model); the active step is a solid orange pill; each page ends with a big orange
  "Next: <step>" button. A "Python" tab on the right edge slides out the generated code. Light/Help buttons at the
  bottom of the sidebar.
- **Colours and type** (VERIFIED, visual): navy `~#0F172A`-like background, slate cards, one strong orange accent,
  green for "valid" messages, monospace for numbers and dates in the data card.
- **Data views** (VERIFIED, live): Explore has three tabs (Time series, Decomposition, Autocorrelation); a row of seven
  small stat tiles (count 195, mean 0.78, std, median, min, max, missing 0); an interactive line chart that draws
  itself left to right, with zoom/pan/download icons and pill toggles per series. Decomposition stacks observed, trend
  and seasonal panels with a "Guide to Decomposition" link.
- **Forecast view** (VERIFIED, live, Fit & Predict): a train/test split chosen by date or slider (156 / 39 points), a
  forecast-length box limited to the test size, an "Include prediction intervals" switch, then a green "Forecast
  results (39 steps)" banner, three colour-tinted metric cards (MAE, MSE, MASE), a history (orange) vs forecast (blue)
  chart, a feature-importance table and a predictions table with Download.
- **Pleasant**: the step-by-step order removes guesswork; "Next" buttons; data summary before any modelling; each
  chart has one job. **Hard**: everything is technical (lags, MASE, exog, regressors); a manager would be lost by step 3.
- **Adopt**: the *guided order* (data -> what we expect -> how reliable -> what it means), a compact row of plain
  stat tiles above a series chart, "Next: ..." links at the foot of each page, a tabbed "View" switch (history /
  pattern / past checks).
  **Improve**: replace metric abbreviations with one plain sentence plus a bar ("misses about 67% less than repeating
  last year"). **Do not copy**: the orange-on-navy brand look, the logo, the code panel, the pipeline-builder controls,
  any text.

### 3.2 ForecastHub (chipidaza23/ForecastHub)

- **Licence**: MIT (VERIFIED, `LICENSE`).
- **Stack** (VERIFIED, `frontend/package.json`, `backend/`): Next.js 16.2, React 19.2, Tailwind v4, Recharts 3,
  lucide-react icons, Supabase; FastAPI + StatsForecast backend; Playwright smoke test. Live demo
  `frontend-eta-sand-86.vercel.app` loaded (it runs on mock data; README says the API falls back to it, VERIFIED in
  `CLAUDE.md` text and consistent with what loaded). Capture: `references/forecasthub_live_dashboard.jpg`.
- **Layout** (VERIFIED, live + `page.tsx`): white 224 px left sidebar (logo, five links with icons, version footer),
  slate-50 page, `max-w-7xl` content: page title + one-line subtitle + "Upload Data" button; four KPI cards (2 x 2 on
  medium screens, 4 across on extra-large); forecast chart (2/3 width) next to a reorder-alerts list (1/3); a sortable
  inventory table; an "Ask AI" box with three suggested questions.
- **Components** (VERIFIED, source): `KPICards` = label top-left, tinted icon chip top-right, big bold value, small grey
  caption; a pulsing grey skeleton while loading; a friendly empty state ("No data yet, upload a CSV") with a link; a
  red error box. `Sidebar` turns into a top bar + slide-in drawer under the `md` breakpoint with proper `aria-label`s.
  `ForecastChart` = Recharts area chart, history in green, forecast line in indigo, two gradient bands (80% and 95%),
  SKU and horizon (7/14/30 days) dropdowns, CSV export icon, request cancelling when the selection changes.
- **Colours / type** (VERIFIED): Tailwind indigo-600 accent, slate/grey neutrals, amber for alerts, emerald for OK;
  system UI font.
- **Pleasant**: very clear hierarchy, one screen answers "what needs my attention" (alert list with plain actions
  "Order 650 units", "~3d of stock left"); good empty/loading/error states. **Hard**: technical captions on screen
  ("100 - MAPE (last 30d)", "ROP", "EOQ"); on the live demo the forecast chart showed only a forecast band with almost no
  history; no dark mode (NOT VERIFIED beyond the CSS, which has a single light palette); generic look.
- **Adopt**: the "attention list" idea (our version: "What needs a decision" with the top levers), the
  KPI-card anatomy (label, chip, value, meaning), the loading skeleton / empty / error trio, the drawer navigation
  pattern on phones, one CSV download next to each chart.
  **Improve**: plain captions, rupees, history always visible before the forecast. **Do not copy**: the inventory
  domain, upload page, AI advisor, auth, the generic Tailwind look, any text.

### 3.3 Visual Data Forecaster (Garud218/Visual-Data-Forecaster)

- **Licence: none found** (VERIFIED: GitHub reports no licence and the repository has only `README.md`, `index.html`,
  `Dashboard.png`). Without a licence nothing may be reused; **ideas only**.
- **Stack** (VERIFIED, `index.html`): one HTML file; Tailwind from its CDN, Chart.js 4.4.2, simple-statistics 7.8.3,
  Inter + Roboto Mono from Google Fonts. Live demo on GitHub Pages loaded; I loaded "Sample: Web Traffic" and pressed
  Generate Forecast (capture: `references/visual_data_forecaster_live_after_generate.jpg`).
- **Layout** (VERIFIED): near-black page (`#030712`), title + subtitle, a 1/4 control column (Data Source panel with two
  sample buttons and a text box, Forecasting Model dropdown, big glowing blue "Generate Forecast" button) and a 3/4 chart
  column, then a "Model Insights" row of four words (Trend: Upward, Volatility: Moderate, Confidence: High, Summary).
  One column on small screens (`grid-cols-1 lg:grid-cols-4`, VERIFIED in source; phone rendering NOT VERIFIED).
- **Visual style** (VERIFIED): "glass panels" = `rgba(17,24,39,0.6)` with a faint border and blur; blue history line,
  yellow trend line, pink dashed forecast with dots, a faint pink band; Roboto Mono axis labels; grid lines in
  `rgba(55,65,81,0.5)`; the button has a coloured glow on hover.
- **Pleasant**: dramatic dark look, the forecast pops, the four-word insight row is instantly readable.
  **Hard / misleading** (VERIFIED in source): the "confidence interval" is `1.96 x std / sqrt(n)` of the *history*, the
  same width at every step, so it does not widen with time and is not a range for future values; in the repository
  screenshot the insight says "Upward" while the drawn trend slopes down; x labels are rotated "P1, P3..."; the band is
  barely visible.
- **Adopt**: the dark-theme mood (deep background, translucent panels, one bright line for "what we expect"), a short
  word-based insight row ("Direction: rising slowly", "How steady: very steady"), monospace-like tabular figures for
  numbers.
  **Improve**: ranges that come from the saved simulations and widen with time, insight words computed from real saved
  values, readable date labels. **Do not copy**: the code, the pink/yellow scheme, the interval method, the model
  dropdown, the paste-your-data box, any text.

---

## 4. Comparative analysis

Scores are my judgement on what I saw (1 = weak, 5 = strong). "Mine" = the current dashboard (screenshots in
`outputs/phase5/currency/` and `ui_polish/after/`).

| Aspect | Skforecast Studio | ForecastHub | Visual Data Forecaster | Mine (now) |
|---|---|---|---|---|
| Overall visual appeal | 4: confident dark UI, strong accent | 3: clean but generic | 4: dramatic dark glass | 4: polished glass, aurora, 3D |
| Dashboard layout | 4: one job per step | 4: KPI row, chart + side list, table | 3: controls + one chart | 3: long single column per page |
| Landing page | 5: marketing page with hero, demos, steps, FAQ | 1: none (straight into the app) | 1: none | 3: hero inside the overview |
| Navigation | 5: numbered step sidebar + "Next" | 4: sidebar, drawer on phone | 1: single page | 3: top tabs; "Pages" button on phone; no order cue |
| Chart presentation | 4: interactive, zoom/pan, tabs | 3: bands but thin history | 3: striking but misleading band | 4: annotated, plain hover text |
| Data visualisation breadth | 5: stats, decomposition, autocorrelation, backtests | 3: forecast + table | 2: one chart | 3: money only; no forecasts shown |
| Colour combinations | 4: navy + orange | 3: indigo + slate | 3: blue/yellow/pink on black | 4: indigo/teal/amber, light + dark |
| Typography | 4: bold sans + mono numbers | 3: system font | 3: Inter + Roboto Mono | 4: Inter + Plus Jakarta, tabular figures |
| Animation and interaction | 3: chart draw-in, slide-out code | 2: skeleton pulse | 2: button glow | 5: count-up, tilt, 3D, reduce-motion switch |
| Responsiveness | NOT VERIFIED on phone | 4: drawer, grid steps (source) | 3: stacks (source) | 4: tested at 390 px, no sideways scroll |
| Ease of use for a manager | 2: technical | 3: plain actions, technical captions | 3: simple, but technical model names | 4: plain words throughout |

**What mine already does better**: plain language everywhere with a banned-word scan; honesty banner on every page;
rupee formatting; light and dark themes with tested 4.5:1 contrast; reduced-motion switch and still versions of every
3D piece; real numbers checked against saved tables by tests; a live engine behind "Try your own numbers".

**Where mine falls short**:
1. The forecasts, likely ranges and past-accuracy checks (Phases 1 to 3) are invisible, so trust rests on the reader's
   faith.
2. No guided order: five equal tabs, no "start here", no "next" cue.
3. The landing moment and the overview are one page; a first-time reader meets a 3D knot before knowing what the
   product is for.
4. Long single-column pages; there is no side-by-side "number + chart + what it means" pattern like ForecastHub's.
5. The pays-for-itself chart is one 100% bar for the expected outlook (accurate, but a dull, empty-looking picture);
   the outlook comparison lives in a table instead of the chart.

---

## 5. Recommended design direction

**Concept name: "Clear Horizon".** The product answers one question: *what lies ahead for this AI programme, and how
sure can we be?* The visual metaphor is a horizon:

- a **"Today" line** on every time chart (solid past to the left, dashed future to the right, a soft likely-range band
  that widens with time);
- a **break-even horizon** (the zero line) on every money chart, labelled "Pays for itself above this line";
- a calm, deep page (dark) or soft paper page (light) with translucent cards, keeping the existing glass language.

**Visual style name: "Horizon Glass"**: the current tokens, slightly deepened for contrast, one indigo accent for
"what we expect", warm amber for "caution", teal for "upside", slate for "what happened".

**Rationale**: it borrows the *guided order* from Skforecast Studio, the *dashboard anatomy* (KPI row, chart with side
panel, attention list, states) from ForecastHub, and the *dark, glowing forecast mood* from Visual Data Forecaster, but
keeps this project's strongest asset, plain honest words with real numbers, at the centre. It is achievable in
Streamlit with what already exists (Plotly shapes for the Today line and bands, `components.html` for small effects).

---

## 6. Colour palette

The existing token system in `theme.py` stays; values below replace or extend it. All text pairs were computed
(WCAG relative luminance, script run in a scratch folder): every text colour is at least **5.0:1** on its background.

**Light**

| Token | HEX | Use | Contrast |
|---|---|---|---|
| bg | `#F6F7FB` | page | |
| surface | `#FFFFFF` (cards at 72 to 92% opacity over bg) | cards | |
| text | `#101326` | body, numbers | 17.2:1 on bg |
| muted | `#4B5068` | captions | 7.4:1 |
| faint | `#5F6580` | axis ticks, footnotes | 5.4:1 |
| accent | `#4338CA` | links, active nav, "what we expect" | 7.4:1; white on it 7.9:1 |
| warm / warm-text | `#B45309` / `#7C4A03` | caution, banner | 5.0:1 / >7:1 |
| good | `#047857` | "on track" chip | >5:1 |
| banner bg | `rgba(217,119,6,0.10)` | example-company banner | |

**Dark**

| Token | HEX | Use | Contrast |
|---|---|---|---|
| bg | `#0B0E1A` | page | |
| surface | `#151A2E` | cards | |
| text | `#ECEEF8` | body | 16.6:1 on bg |
| muted | `#B4B9D2` | captions | 9.9:1 |
| faint | `#9AA0BD` | ticks | 7.5:1 |
| accent | `#A5B4FC` | links, "what we expect" | 9.7:1; dark text on it 9.7:1 |
| warm | `#FBBF24` | caution | >10:1 |
| good | `#34D399` | on-track chip | >8:1 |

**Chart colours** (meaning is fixed across every page)

| Meaning | Light | Dark | Also shown by |
|---|---|---|---|
| What happened (history, real values) | `#334155` solid | `#CBD5E1` solid | solid line |
| What we expect (central forecast) | `#4338CA` dashed | `#A5B4FC` dashed | dash style + "Today" divider |
| Likely range (8 in 10) | accent at 14% fill | accent at 18% fill | band, no outline |
| Past prediction | `#BE185D` dotted | `#F9A8D4` dotted | dotted + marker |
| Cautious outlook | `#B45309` | `#FBBF24` | direct label at line end |
| Expected outlook | `#4338CA` | `#A5B4FC` | thicker line |
| Optimistic outlook | `#0F766E` | `#5EEAD4` | direct label |
| Cost types | keep `LINE_COLORS` (sky, cyan, indigo, lavender) | same | legend + tags |

**Colour-blind check** (Machado 2009 simulation, full severity; CIELAB distance between outlook colours, >20 is clearly
different): light deutan 62 to 130, protan 48 to 119, tritan 25 to 90; dark deutan 35 to 114, protan 44 to 116, tritan
36 to 82. All pairs stay apart, and every line is also labelled directly and differs in thickness or dash, so colour is
never the only cue.

---

## 7. Typography

- **Inter** for everything (already loaded), with `font-variant-numeric: tabular-nums` on numbers;
  **Plus Jakarta Sans** 700/800 for display headings only (existing).
- Scale (px, desktop / phone): display 44 / 30, H1 32 / 26, H2 22 / 19, H3 17 / 16, body 16 / 15, caption 13, KPI value
  34 / 28, KPI words ("Not within 12 months") 22 / 18. Line height 1.5 body, 1.15 headings. Max line length 70
  characters.
- Weights: 400 body, 500 labels, 600 card titles, 700 values. Sentence case everywhere; no all-caps except the small
  section labels (letter-spacing 0.06em).

---

## 8. Sitemap

Evaluation of the suggested structure:

| Suggested page | Decision | Why |
|---|---|---|
| Landing / welcome | **Keep, new** ("Welcome") | Separates "what is this" from the dashboard; hero visual uses a real saved forecast |
| Dashboard overview | **Keep, rename**: existing "The big picture" | Already strong; add a small "how reliable" summary card and a "What we expect next" strip |
| Data overview (upload) | **Keep without upload**, rename "The data we used" | Upload is not supported; browse the 7 real series |
| Forecast explorer | **Keep**, name "What we expect next" | Series picker + "show the next ..." limited to saved lengths |
| How reliable is it | **Keep, new** | The biggest missing trust piece; uses saved past checks and leaderboard |
| Results and insights | **Split into existing pages** | "Where the money goes", "When it pays for itself" and "What matters most" already exist and work; they become one group "The money" with three tabs, so the top bar stays short |
| Try your own numbers | **Keep** | The live feature |

Final map (7 entries in the top bar, grouped):

```
Welcome
The big picture
Forecasts ▾        The data we used | What we expect next | How reliable it is
The money ▾        Where the money goes | When it pays for itself | What matters most
Try your own numbers
```

Streamlit's `st.navigation` accepts a dict of sections (`{"Forecasts": [...], "The money": [...]}`); with
`position="top"` sections render as drop-down menus (behaviour of section menus in the installed 1.67 must be checked in
phase A of section 16; fallback: flat top bar with nine items and the existing "Pages" menu on phones).

---

## 9. Page-by-page layout (with the real data each block uses)

Every page: sticky top bar -> example-company banner -> rupee-rate note -> page heading and one-line purpose -> content
-> "How to read this" -> "Next: ..." link -> footer.

### 9.1 Welcome (new)

```
+--------------------------------------------------------------------------+
| [logo] AI Workforce Investment Intelligence  (Example company)  ☾  ⏸   |
| ! You are looking at an example company with made-up figures.           |
+--------------------------------------------------------------------------+
|  See what an AI programme could cost,           | [hero chart]           |
|  what it could return, and when it               |  hosting prices:       |
|  could pay for itself.                           |  history ── | Today |  |
|  Built on public trends, applied to an           |  - - expected  ░ range |
|  example company.                                |                        |
|  [ Explore the results → ]  [ How it works ]     |                        |
+--------------------------------------------------------------------------+
|  How it works (3 steps):  1 Real public trends -> 2 What we expect next  |
|  -> 3 What it means for cost, benefit and payback                        |
+--------------------------------------------------------------------------+
|  Three numbers: ₹2.61 Cr cost | ₹1.7 Cr est. benefit | Pays: not in 12 m |
+--------------------------------------------------------------------------+
```

- Hero chart: `data/processed/ppi_hosting_monthly.csv` (last 36 months) + `phase3/forecasts/ppi_hosting_monthly.csv`
  (central line and 10th-90th percentile of the 200 paths, Nov 2026 to Oct 2027). Drawn with Plotly (static, real), with
  the existing 3D glass shape optionally behind it (3D piece 1).
- Three numbers: `totals_summary.csv`, `break_even_summary.csv` (expected, standard caution) via `logic.overview_cards`.
- "Explore the results" -> The big picture. See `references/concept_welcome.png`.

### 9.2 The big picture (existing, refined)

```
| Section label: EXPECTED OUTLOOK                                          |
| [Total cost ₹2.61 Cr] [Est. benefit ₹1.7 Cr] [Balance -₹91.0 L] [Pays: Not within 12 months] |
| [Likely range | Typical case]                                            |
| Running balance by outlook (line chart, break-even horizon, notes)  |  What needs a decision      |
|                                                                     |  1 Time saved per person    |
|                                                                     |  2 Share of time -> value   |
|                                                                     |  3 Training hours           |
| [What we expect next strip]: pay +6.8% over 2 yrs | hosting prices +1.5% | "How reliable: close on pay, wider misses on AI usage" -> link |
| Key findings (3 cards, existing)                                         |
```

- Cards, chart, findings: unchanged sources. Side list: `sensitivity.csv` top 3 via `logic.lever_phrases`.
- Strip: `phase3/forecasts/eci_wages_quarterly.csv` and `ppi_hosting_monthly.csv` (change from the last real value to
  the end of the saved forecast), `phase3/tables/interval_check.csv` for the reliability sentence.
- The 3D columns + plain bars move under a "See it in 3D" expander so the first screen is calmer (3D piece 2).

### 9.3 The data we used (new, replaces "upload")

```
| [Series picker: pills, grouped "Pay and prices" | "AI use"]                |
| Plain description: "How much US employers pay per hour, as an index."     |
| [From Jan 2001] [To Jul 2026] [103 quarters] [Unusual points: 0] [Gaps: none] |
| Tabs: [What happened] [Trend and repeating pattern] [Unusual points]      |
| Line chart of the full history (zoomable range slider on desktop)         |
| "In plain words": "Rising steadily, about 3% in the last year." |
```

- Stat tiles: `phase1/tables/summary_stats.csv`. Unusual points: `phase1/tables/anomalies.csv` (markers on the chart).
- Trend and pattern tab: `phase1/tables/decomposition.csv` (strength words: "strong / some / little") and the history
  smoothed; if a component series is not saved as numbers, show the saved Phase 1 decomposition PNG with alt text
  (`phase1/figures/*_decomposition.png`). Requires reading `data/processed` files in `data.py` (read-only, new loader).
- For BurstGPT series: x-axis "Day 1 ... Day 87" with a note "The source does not give calendar dates."
- Download: "Download this series (CSV)" from the processed file (read-only).

### 9.4 What we expect next (new forecast explorer)

```
| Series [pills]   Show the next: [3] [6] [12 months]  (only up to the saved 12) |
| Big chart: history (solid) | Today | expected (dashed) + likely range band |
| Side card: "By Oct 2027 we expect about 128.8 (likely between 127.0 and 131.3)"   |
|            "That is +1.5% from today."                                   |
| Small note: "Likely range = where 8 in 10 simulated futures land."      |
| [Download what we expect (CSV)]                                          |
```

- Data: `phase3/forecasts/<series>.csv` (sample -1 = expected; samples 0-199 -> 10th and 90th percentile); history from
  `data/processed`. "Show the next" options are generated from the saved horizon (e.g. hourly: 1 day, 3 days, 7 days;
  quarterly: 4, 8 quarters).
- Honest flag: where `interval_check.csv` shows real values often fell outside the range (`flag = True`), a calm
  amber note: "Past real values often landed outside this range; treat it as narrower than reality." (Phase 3 found
  this; the "More cautious" setting on the money pages exists because of it.)

### 9.5 How reliable it is (new)

```
| Plain verdict per series: "Our hosting-price forecast missed by about 2.5 index points on average." |
| Chart: past predictions (dotted) vs what really happened (solid), with the range at the time |
| Tile row: [Real value inside the range: 2 of 6 months] [Average miss: 2.5 points] |
| "Which approach was closest" bar chart, plain names, best at top:        |
|   Blend of several approaches      ██████████ closest                    |
|   Smoothed trend (multiplying)     ██████████                            |
|   Statistical pattern model        ██████████                            |
|   Straight-line trend              ██████████                            |
|   ...                                                                    |
|   Repeat last year's value         ███                                   |
| "The top four were almost equally close; we used a blend."              |
```

- Past predictions: `phase2/tables/holdout.csv` for the chosen approach (`chosen_models.csv`), optionally the rolling
  checks from `cv_folds.csv` behind a "Show earlier checks" toggle.
- Inside-the-range share: `phase3/tables/interval_check.csv` (`coverage_80_after`, `n_holdout_points`).
- Ranking: `phase2/tables/leaderboard.csv`, rows with `status = ok`, sorted by `cv_mae`, shown as "average miss" in the
  series' own unit; bars relative to "Repeat last year's value" (seasonal naive). Skipped approaches are not listed
  (plain footnote: "Some approaches could not run on this data").
- **Plain names live in `copy.py` only** (new map `APPROACH`): `naive` -> "Repeat the last value", `seasonal_naive` ->
  "Repeat last season's value", `mean` -> "Long-run average", `drift` -> "Straight-line trend", `moving_average` ->
  "Recent average", `ses`/`holt`/`damped_holt`/`hw_*` -> "Smoothed trend" (with plain qualifiers), `arima`/`sarima` ->
  "Statistical pattern model", `ensemble` -> "Blend of several approaches", `seasonal_ma3` -> "Average of the same day
  in recent weeks". Metric abbreviations never reach the screen.
- See `references/concept_reliability.png`.

### 9.6 The money (three existing pages as one group)

- **Where the money goes**, **When it pays for itself**, **What matters most**: layouts unchanged; sources unchanged.
  Two refinements: (a) "When it pays for itself" gets a three-outlook chart (one row per outlook: dot at month 11 for
  optimistic, "Not within 12 months" marker for the other two) above the existing per-month bars, from
  `break_even_summary.csv`; (b) each page ends with "Next: ..." to the following one.

### 9.7 Try your own numbers (existing)

- Unchanged engine and fields. Layout: form in a left card (sticky on desktop), results on the right; on phones the
  results come first after pressing Update, with a "Change numbers" link back to the form. Download stays CSV.

---

## 10. Component specifications

| Component | Spec |
|---|---|
| Top bar | Sticky, 64 px, blurred translucent surface; left: logo + product name + "Example company" pill; centre: navigation (sections as menus); right: Dark mode and Reduce motion switches. Phone (<768 px): logo + "Pages" button opening a full-height drawer (ForecastHub pattern) with the same groups. |
| Side navigation | Not used on desktop (top bar is enough for 7 entries). Inside Forecasts pages: a vertical step list "1 The data we used, 2 What we expect next, 3 How reliable it is" as a slim left rail at >=1280 px only; hidden below. |
| Banner | Existing text from `copy.BANNER`, warm tint, on every page, never dismissible. |
| Cards | Radius 14, 1 px border token, surface at 72% + 16 px blur, padding 24 (16 on phones), shadow level 1; hover lifts 2 px (none with Reduce motion). |
| KPI cards | Icon chip + status chip row; label (13/500); value (34/700, tabular); meaning line (13, muted); optional sparkline. Words-as-values use 22 px. Count-up once (800 ms). |
| Stat tiles (new, small) | 4 to 6 per row on desktop, 2 per row on phone; label above value; no chips. |
| Buttons | Primary: accent fill, 44 px high, radius 12, text on-accent; Secondary: ghost with border; Link-button "Next: ..." with arrow. Focus ring 3 px accent at 40%. |
| Forms | Number inputs with unit suffix and help icon (existing `FIELDS`); errors shown under the field in plain words (`ERRORS`). |
| Tabs / segmented controls | `st.segmented_control` styled as pills (existing CSS) for outlook, caution, series, "show the next". |
| Tooltips | Plain sentences from `copy.py`; every chart hover lists date in words, value with unit, and range ("likely between ..."). Glossary terms get a dotted underline + `help=` text. |
| Loading | Shimmer skeleton in the card's shape; "Working out the numbers..." for the engine (existing). |
| Empty | Friendly line + next step, e.g. "No saved forecast for this series yet." |
| Error | `copy.MISSING` in a calm card (existing `data.Missing` path); never a stack trace (`showErrorDetails = "none"` stays). |
| Section "Next" footer | Card with the next page name and one line on what it answers. |

---

## 11. Chart recommendations

| Data | Chart | Annotations | Interaction | Phone |
|---|---|---|---|---|
| History + forecast + range | Line (solid history, dashed forecast) + filled band | "Today" vertical line with label; end-of-forecast value label | Unified hover (date, value, likely range); range slider on desktop only | Last 24 points of history; labels at line ends instead of legend |
| Past predictions vs real | Two lines (dotted predicted, solid real) + the range at the time | Count of points inside the range in the title line | Hover shows "We expected X; it was Y" | Same, 260 px tall |
| Approach ranking | Horizontal bars, best at top, chosen one highlighted in accent | "Repeat last season" marked as the reference | Hover: "average miss: 0.57 points" | Top 6 + "Show all" |
| Running balance by outlook | Lines with break-even horizon, likely-range band on the highlighted outlook (existing) | Lowest point, pays-for-itself month (existing) | Legend click off (existing) | Existing |
| Cost over time | Stacked bars (existing) | Tags "Based on trends" / "Our estimate" | | Existing |
| Cost share | Donut / 3D donut (existing) or a 100% bar on phones | | | 100% bar |
| Payback month | Dot strip per outlook + per-month bars (existing) | "Not within 12 months" marker | | Stacked vertically |
| Levers | Diverging bars (existing) | | | Existing |
| Repeating pattern | Small multiples: trend line + pattern strength word | | | One per row |

General: no Plotly toolbar (keep `displayModeBar: False`), axis titles in plain words, money ticks via `money_tick`,
series colours from section 6, at most 3 lines highlighted at once, `responsive: True`.

---

## 12. Animation and interaction spec

| What | Where | Duration | Easing | Reduced-motion fallback |
|---|---|---|---|---|
| Page fade + rise 8 px, cards staggered 60 ms | every page | 400 ms (all done by 600 ms) | cubic-bezier(.2,.7,.2,1) | appear instantly |
| KPI count-up | KPI cards | 800 ms once | ease-out | final value only |
| Line draw-in (history first, then forecast) | forecast charts | 600 ms + 400 ms | cubic-in-out (Plotly transition) | static chart |
| Band fade-in after the forecast line | forecast charts | 300 ms | ease-out | static |
| Card hover lift / tilt (max 6 deg) | cards | 150 ms | ease-out | none |
| Nav pill glide | top bar | 250 ms | ease-in-out | jump |
| Skeleton shimmer | loading | 1.2 s loop | linear | static grey |

**3D pieces (maximum five, all existing, each with a still version)**

| # | Piece | Page | Still version |
|---|---|---|---|
| 1 | Glass shape over gradient | Welcome hero (moved from The big picture) | CSS gradient + still ring |
| 2 | Year-end balance columns | The big picture, inside "See it in 3D" | Plain Plotly bars (always beside it) |
| 3 | Tilted cost donut | Where the money goes | Flat Plotly donut |
| 4 | Depth bars | What matters most | Same bars without motion |
| 5 | Blurred accent orbs | background, every page | hidden on phones / still |

No new 3D piece is added. **Performance budget**: one WebGL scene animating at a time (existing rule); first
meaningful paint under 2.5 s on the laptop; each page under 1.5 MB of transferred script beyond Streamlit itself;
average frame time at most 20 ms (existing check: 16.8 ms); Three.js pinned (`three@0.160.0`) and optional.

---

## 13. Responsive strategy

| Width | Layout |
|---|---|
| 1440 px | Content max 1200 px; KPI row of 4; chart 2/3 + side card 1/3; step rail visible on Forecasts pages |
| 768 px | KPI 2 x 2; chart full width with side card below; top bar shows "Pages" drawer; no step rail |
| 390 px | One column, 16 px gutters; KPI cards one per row (value 28 px); charts 260 to 300 px tall with direct labels instead of legends; segmented controls scroll sideways inside their own box (never the page); range sliders hidden; 3D pieces off (still versions) except the hero still image |

Streamlit `st.columns` collapse below 640 px automatically; extra rules live in `styles.css` media queries at 1024 and
768 / 640. Check: no sideways page scroll at 375 and 390 px (existing browser test extended to the new pages).

---

## 14. Technology recommendation

### 14a. Version 1: stay in Streamlit (recommended)

- Streamlit 1.67 (installed) with `st.navigation` sections, `st.segmented_control`, `st.tabs`, `st.columns`,
  `st.download_button`; Plotly for every chart (shapes for the Today line, `fill="tonexty"` bands); existing
  `styles.css` + tokens; `components_3d.py` unchanged in kind. **No new packages** (pandas, numpy, pyarrow, plotly and
  streamlit already cover reading the forecast parquet/CSV and drawing it).
- New read-only loaders in `data.py` for `phase1/tables`, `phase2/tables`, `phase3/forecasts`, `phase3/tables` and
  `data/processed`, all cached with `st.cache_data`; every loader raises `Missing` exactly like today.
- Pure helpers in a new `logic_forecasts.py` (no Streamlit calls) so tests can check them.

### 14b. Later (optional, not part of the plan): React + a small read-only API

- **What**: a FastAPI service that serves the saved tables and the engine call as JSON; a React (Vite or Next.js) front
  end with Recharts or Plotly.js, Tailwind tokens mirroring section 6.
- **Gains**: full control of layout and motion, true side navigation and URL-addressable states, faster interactions
  without full reruns, easier phone polish.
- **Cost**: roughly 3 to 5 times the work of version 1 (a second language and build chain, an API layer, rewriting
  every page and every test, hosting two services); new packages (Node toolchain, FastAPI).
- **Risks**: two codebases drift; the banned-word scan and `copy.py` must be ported; number-equality tests must be
  rewritten; Streamlit's free hosting no longer fits. Only worth it if the dashboard becomes a product rather than a
  project deliverable.

---

## 15. Proposed folder structure (fits what exists)

```
src/dashboard/
  app.py                 (existing; navigation sections added)
  copy.py                (existing; new keys: WELCOME_*, DATA_*, FORECAST_*, RELIABLE_*, APPROACH map, SERIES map)
  theme.py               (existing; tokens per section 6, chart colour roles)
  currency.py            (existing, unchanged)
  data.py                (existing; new read-only loaders)
  logic.py               (existing)
  logic_forecasts.py     (new: likely range, "show the next" options, plain insight words, ranking rows)
  charts.py              (existing money charts)
  charts_forecast.py     (new: history/forecast/range, past-vs-real, ranking bars)
  components.py          (existing; + stat tiles, next-page card, step rail, drawer)
  components_3d.py       (existing, unchanged)
  styles.css             (existing; + new component styles, breakpoints)
  pages/
    welcome.py           (new)
    overview.py          (existing)
    data_used.py         (new)
    forecast.py          (new)
    reliability.py       (new)
    costs.py, timing.py, levers.py, your_company.py   (existing)
tests/
  test_phase5d_forecast_pages.py   (new)
```

---

## 16. Development phases (each small and testable)

| Phase | Work | Done when |
|---|---|---|
| A | Navigation sections + Welcome page (static Plotly hero from saved files) + "Next" cards | AppTest renders all pages; banner present; banned-word scan clean; browser check at 1440/768/390 |
| B | Read-only loaders + `logic_forecasts.py` with tests | Tests: likely range equals 10th/90th percentile of saved paths; options never exceed saved horizon; missing files raise `Missing` |
| C | "What we expect next" page | Values on screen equal the saved CSV (test); Today line present; phone layout checked |
| D | "How reliable it is" page + `APPROACH` plain-name map | No model name or metric abbreviation in rendered text (scan); ranking order equals `leaderboard.csv` by `cv_mae` |
| E | "The data we used" page | Stat tiles equal `summary_stats.csv`; BurstGPT day-number note shown |
| F | Big-picture refinements (attention list, "what we expect next" strip, 3D under expander) and payback dot strip | Number-equality tests updated and passing |
| G | Palette tweak (section 6) + contrast test update + colour-blind check in tests | Contrast test >= 4.5:1 both themes |
| H | Full regression: pytest, browser check, performance check, fingerprints of phase 1 to 4 outputs unchanged | All green |

---

## 17. Version 1 vs later

**Version 1**: phases A to H above; CSV downloads only; five existing 3D pieces; English only.

**Later**: printable HTML summary (standard library only); rolling past-check explorer with every fold; an "explain this
chart" plain-language panel per chart; Hindi copy (`copy.py` makes this possible); React move (14b); any upload or live
retraining (would need backend work and review first).

---

## 18. Final quality checklist

- [ ] Plain language: every new string lives in `copy.py`; sentences under 25 words; read aloud test.
- [ ] No jargon: banned-word scan over `copy.py`, AppTest output and browser text of every page, extended with model
      names (`arima`, `sarima`, `holt`, `ensemble`, `naive`, `prophet`, `lstm`, `xgboost`, ...) and metric names (`MAE`,
      `RMSE`, `MAPE`, `MASE`, `sMAPE`, "confidence interval", "seasonality", "stationarity").
- [ ] Real numbers: each new on-screen value compared with its source file in a test (as Phase 5 did with 13 values).
- [ ] Rupees: every money value through `T.money` / `currency.fmt`; rate note visible; no "$" in rendered text.
- [ ] Banner on every page, including Welcome; benefit always called "estimated", never "forecast".
- [ ] Likely ranges only from saved simulations; honest note where real values fell outside them.
- [ ] Accessibility: 4.5:1 text contrast both themes; focus rings; charts have a text summary; HTML tables, not canvas.
- [ ] Reduced motion and `ENABLE_3D = False` both give a complete still site; at most five 3D pieces.
- [ ] Responsive at 1440, 768, 390 px; no sideways scroll.
- [ ] Speed: first paint < 2.5 s locally; frame time <= 20 ms; one animated scene at a time.
- [ ] Tests: full pytest suite green; fingerprints of `src/engine`, `src/tsaf`, `data/processed`, `outputs/phase1` to
      `phase4` unchanged.

---

### Sources consulted

- https://github.com/skforecast/skforecast (README, `LICENSE`, `docs/skforecast-studio/skforecast-studio.md`,
  `docs/img/skforecast-studio-screen.png`, `.github/ISSUE_TEMPLATE/skforecast_studio.yml`, releases API)
- https://studio.skforecast.org/ (live, 18 Nov 2026)
- https://github.com/chipidaza23/ForecastHub (README, `CLAUDE.md`, `LICENSE`, `frontend/package.json`,
  `src/app/*`, `src/components/{Sidebar,KPICards,ForecastChart}.tsx`, `docs/dashboard-screenshot.png`)
- https://frontend-eta-sand-86.vercel.app (live, 18 Nov 2026)
- https://github.com/Garud218/Visual-Data-Forecaster (README, `index.html`, `Dashboard.png`; no licence)
- https://garud218.github.io/Visual-Data-Forecaster/ (live, 18 Nov 2026)
