# Phase 5 summary: the dashboard

## What was built

A five-page Streamlit dashboard for a non-technical reader, in `src/dashboard/`: `app.py` (entry point, top bar,
banner, page registry), `copy.py` (all on-screen text and the one mapping from engine names to plain labels),
`theme.py` (colours, fonts, Plotly template, formatters), `styles.css`, `data.py` (cached loaders of the Phase 3
and 4 outputs and the live engine call), `logic.py` (card values, findings, input checks), `components.py`
(cards, banner, hero), `charts.py` (all Plotly figures) and `pages/` (one file per page). The theme is in
`.streamlit/config.toml`; extra packages in `requirements-dashboard.txt`.

## How to run

```bash
pip install -r requirements.txt -r requirements-dashboard.txt
streamlit run src/dashboard/app.py          # then open http://localhost:8501
```

## Pages and where each block's numbers come from

| Page | What it shows | Source |
|---|---|---|
| The big picture | hero, four cards (expected outlook: total cost, estimated benefit, running balance, pays for itself), running balance of the three outlooks, three key findings | `totals_summary.csv`, `break_even_summary.csv`, `monthly_summary.csv`, `cost_breakdown.csv`, `sensitivity.csv` |
| Where the money goes | monthly cost by type with "Based on trends" / "Our estimate" tags, cost share, benefit versus cost; outlook and caution selectors | `monthly_summary.csv`, `cost_breakdown.csv` |
| When it pays for itself | verdict sentence, month-by-month chart with a "Not within 12 months" bar, the three outlooks side by side, narrow-range note | `break_even_summary.csv`, `totals_summary.csv`; the month counts are recomputed with the Phase 4 settings (5,000 runs, same starting number), and a test checks they match the saved share exactly |
| What matters most | which choices change the year-end balance most (+-20%), takeaway, "What could change that" box (the expected outlook does not pay for itself within 12 months) | `sensitivity.csv`, `break_even_summary.csv`, `totals_summary.csv` |
| Try your own numbers | control panel; Update results reruns the real engine with 2,000 runs; cards, running balance, cost share, verdict, Download my results | `engine.simulate.run_engine` live, defaults from `config/example_company.json` |

## Numbers checked against the Phase 4 files

Values read from the rendered pages (browser text; the comparison table is drawn on a canvas, so its cells were
read from the rendered table instead) and recomputed independently from the Phase 4 files:

| page | value | from Phase 4 file | shown as | on screen |
|---|---|---|---|---|
| overview | Total cost over the year (expected) | 2.769e+05 | $276.9K | yes |
| overview | Estimated benefit (expected) | 1.803e+05 | $180.3K | yes |
| overview | Running balance at year end (expected) | -9.664e+04 | -$96.6K | yes |
| overview | Pays for itself (expected, P = 0%) | 0 | Not within 12 months | yes |
| overview | Training and support share | 0.6534 | 65% | yes |
| overview | Technology + AI usage share | 0.08823 | 8.8% | yes |
| overview | Top lever swing / 2 | 3.601e+04 | $36.0K | yes |
| timing | Optimistic pays for itself (P50 month) | 11 | Month 11 | yes (table) |
| timing | Optimistic chance | 1 | 100% | yes |
| timing | Cautious likely year-end balance | -6.879e+05 | -$687.9K to -$679.5K | yes (table) |
| timing | Expected most money tied up | 1.657e+05 | $165.7K | yes (table) |
| timing | Optimistic most money tied up | 1.28e+05 | $128.0K | yes (table) |
| timing | Optimistic likely year-end balance | 5.919e+04 | $59.2K to $63.4K | yes (table) |
| levers | Expected year-end balance in the box | -9.664e+04 | -$96.6K | yes |

All 14 sampled values match.

## Motion, 3D and fallbacks

- Hero: a slow, low-poly glass shape (Three.js r160 from jsDelivr, pinned) over an animated CSS gradient; paused
  when the tab is hidden, skipped for reduced motion, and if the download is blocked only the gradient shows (tested
  by blocking the CDN: no page errors).
- KPI cards: values are in the page as plain text; a small script counts them up once (about 800 ms) and tilts
  the cards slightly toward the cursor (max 6 degrees); both are off for reduced motion.
- Charts: short Plotly transitions; pages fade and rise in; a friendly "Working out the numbers..." while the
  engine runs.

## Checks

- Browser test (Playwright, Chromium): all five pages at 1440 px and 390 px, outlook and caution selectors switched,
  inputs changed and Update results pressed (1,000 employees: total cost $422.0K, estimated benefit $360.0K), a
  negative employee count shows the friendly message; no Python exceptions in the server log, no page errors, no
  horizontal scroll at 390 px. The only browser console messages are 404s from Streamlit's own start-up check of
  `<page>/_stcore/health` when a page address is opened directly; they come from Streamlit, not from the dashboard.
- Banned-words scan: `copy.py`, every page rendered with AppTest, the component HTML, the chart text, and the
  final browser text of every page: no hits.
- Screenshots (11 files) in `outputs/phase5/screenshots/`: costs_1440.png, costs_390.png, levers_1440.png, levers_390.png, overview_1440.png, overview_390.png, overview_no3d_check.png, timing_1440.png, timing_390.png, your_company_1440.png, your_company_390.png.
- Fingerprints of `src/engine/`, `src/tsaf/`, `data/processed`, `outputs/phase1` to `phase4` and the earlier
  notebooks: unchanged (237 files).

## What to say in the review

The dashboard puts the project's real results in front of a manager in plain words: what an AI programme costs,
what it could return and when it could pay for itself. Every number on the first four pages is read from the saved
Phase 4 results, and the last page reruns the same engine on the viewer's own figures. For the example company
the expected outlook costs $276.9K over the year against an estimated benefit of $180.3K, so it does not pay for
itself within 12 months; only the optimistic outlook does, in month 11. Training and support is about two thirds
of the cost, while technology running costs and AI usage are under a tenth. The choices that matter most are how
much time people save and how much of it turns into value. The company is an example with made-up figures, and
the dashboard says so on every page.

## Limitations

- The company is an example with made-up figures; the dashboard is only as good as the numbers entered.
- The benefit is an estimate built on surveys and one study, not a forecast.
- The likely ranges are narrow because the tracked cost trends move steadily; Phase 3 found those ranges too
  narrow, so the "More cautious" settings are offered.
- The 3D hero needs a network connection to load its library; without it a plain gradient is shown.
- Streamlit itself cannot run inside Colab; the Phase 5 notebook shows screenshots instead.

## Deviations from the Phase 5 prompt

See `DESIGN_NOTES.md`. In short: no `src/models/` folder exists (the models live in `src/tsaf/models/`); the
month-by-month payback chart is recomputed with the Phase 4 settings because Phase 4 saved only the summary;
`app.py` removes its own folder from the import path so `copy.py` cannot shadow Python's `copy` module; a
project `.streamlit/config.toml` sets the indigo theme; Plotly's toolbar is hidden because its labels are technical.

## UI polish (Phase 5B)

A visual and interaction upgrade only: the data, the engine, the Phase 1 to 4 outputs and every number on screen
are unchanged (fingerprints of `src/engine/`, `src/tsaf/`, `data/processed`, `outputs/phase1` to `phase4` and the
first notebooks: 238 files, identical before and after). Critique of the old look (17 points) in
`ui_polish/CRITIQUE.md`; screenshots in `ui_polish/before/` and `ui_polish/after/` (1440 px and 390 px, plus dark).

**What changed, page by page**
- Everywhere: one type family (Inter, with Plus Jakarta Sans for headlines), tabular figures, a 4/8/12/16/24/32/48
  spacing scale, colours only from tokens in `theme.py` (light and dark sets, pushed to CSS as custom properties),
  a slow aurora backdrop with a faint dot grid, glass cards with a gradient edge that brightens on hover and three
  shadow levels, a sticky blurred top bar with a pill that glides to the active page, a polished "Example
  company" pill, **Dark mode** and **Reduce motion** switches (kept for the session), pages that fade and rise in
  with cards staggered 60 ms apart (all done within 600 ms), restyled selectors, sliders, number boxes, buttons,
  expanders, tooltips, loading shimmer, scrollbar and footer. On phones the page menu is a labelled "Pages" button.
- Charts: one Plotly template per theme (Streamlit's own chart theme switched off so it cannot override it), money
  axes in the card style ("-$200K"), rounded bars, translucent likely-range bands, smooth lines that draw
  themselves, glass hover cards with plain words.
- The big picture: richer hero, cards with an icon, a count-up, a sparkline that draws itself, a status chip
  chosen from the real results ("Needs attention", "On track", "Estimate", "Mostly people costs") and a cursor tilt
  with a moving light; the expected outlook is highlighted on the chart (the others dimmed) with notes for its
  lowest point (-$165.7K) and for the month the optimistic outlook pays for itself (month 11); new 3D columns of
  the year-end balance with the same figures as plain bars beside them.
- Where the money goes: colour swatches on the tags, 3D donut with a "3D view / Flat view" switch.
- When it pays for itself: percentage labels on the bars; the comparison table is now an HTML table (follows the
  theme, readable by screen readers) with an outlook colour dot per row.
- What matters most: raised depth bars of how far each choice can move the year-end balance; the chart title no
  longer repeats the page heading.
- Try your own numbers: gradient "Update results" and a dashed ghost "Reset to example" under the form, whole
  numbers shown without decimals, sparklines on the result cards.

**The five 3D / depth pieces and their fallbacks**

| piece | where | made with | still version |
|---|---|---|---|
| glass torus knot, depth particles with cursor parallax, faint grid floor, text parallax | The big picture, banner | Three.js r160 | CSS gradient with a still glass ring |
| 3D columns of the year-end running balance per outlook (grow in, sway, drag to turn, hover note) | The big picture | Three.js | CSS bars around a break-even line; plain Plotly bars are always beside it |
| tilted 3D cost donut, slices lift on hover, linked legend | Where the money goes | Three.js | flat Plotly donut (the switch hides itself) |
| depth bars with extrusion and hover lift | What matters most | CSS 3D | same bars without motion |
| floating blurred accent orbs behind the cards | every page | CSS | hidden on phones; still with Reduce motion |

Every WebGL scene: transparent background, pixel ratio capped at 2, one animation loop that runs only while the
scene is on screen, the tab is visible and it is the most visible scene on the page (so at most one animates),
renderer, geometry, materials and listeners disposed when the frame goes away. Three.js comes from a pinned jsDelivr
address; if it cannot be fetched, WebGL is missing, the visitor prefers reduced motion or Reduce motion is on, the
still version stays and no error text is shown. Off switch for all of it: `ENABLE_3D = False` in `theme.py`.

**Performance and checks** (`ui_polish/browser_check.py`, results in `ui_polish/browser_check.json`)
- Average frame time of The big picture over 5 s: 16.8 ms (297 frames, 95th percentile 16.8 ms, about 60 fps) on
  the laptop's Intel UHD Graphics (Direct3D 11) in Chromium; no reduction of effects was needed.
- Browser run: every page through the top menu, dark mode on every page and off again, outlooks and caution levels
  switched, Costs flat view and back to 3D, a drag on the 3D columns (the picture changes), Try your own numbers with
  1,000 employees ($422.0K cost, $360.0K estimated benefit) and Reset to example (back to $276.9K). No Python
  exceptions in the Streamlit log, no page errors and no console errors. Runs with the 3D download blocked, with
  WebGL switched off and with reduced motion: every 3D piece shows its still version; the only console line in the
  blocked run is Chrome's own network notice for the blocked file (one line; no page script can silence it).
- No sideways scrolling at 375 px on any page; the example-company banner is on every page.
- Banned-word scan on the final rendered text of every page, the 3D frames, labels and tooltips: no hits.
- 13 on-screen numbers compared with the Phase 4 tables, all equal (cards, 3D columns, lowest point, donut slice,
  comparison table, depth bars, verdict box).
- Text contrast of every text colour on the page and card backgrounds is at least 4.5:1 in both themes (tested).
- pytest: 103 passed (all earlier tests, the Phase 5 tests and 22 new Phase 5B tests: both themes on every page,
  the ENABLE_3D and reduced-motion still versions, 3D values equal to the Phase 4 tables, chart notes, contrast).

**Deviations and simplifications**
- Streamlit 1.67 has no per-viewer theme switch, so the light and dark themes are CSS tokens applied by the app;
  `.streamlit/config.toml` still sets the light base for Streamlit's own widgets, which the CSS then restyles.
- The comparison table on When it pays for itself is an HTML table instead of `st.dataframe` (the canvas table
  cannot follow the dark theme).
- "Reset to example" moved under the form next to "Update results" and now resets through a button callback (the
  form's values cannot be changed after the form has been drawn).
- The cursor tilt, count-up and gliding page pill come from one small script installed once in the page; the 3D
  columns' empty space below the floor on phones was kept rather than cropping the cautious column.
- Streamlit's start-up check of `<page>/_stcore/health` still prints a 404 when a page address is opened directly
  (from Streamlit, as before); the browser check opens pages through the menu.

**Currency (Phase 5C)**: the currency on screen is Indian rupees, converted at `INR_PER_USD` = 94.1159 (RBI reference rate, 16 Nov 2026) from one place, `src/dashboard/currency.py`; the saved Phase 4 tables stay in US dollars (see `outputs/phase5/currency/CHANGES.md`; the dollar figures above are the earlier record).

## UI v3: readable controls, side navigation, a warmer hand-made look

A visual and navigation change only. The engine, the data, the Phase 1 to 4 outputs and every number are unchanged:
245 fingerprinted files identical (`ui_v3/fingerprint_check.json`). The only other files in the protected folders are
raw downloads last changed between 1 and 14 Nov 2026, before this work. Critique, widget checklist, palette and
contrast ratios: `ui_v3/CRITIQUE.md`. Screenshots: `ui_v3/before/` (1440 / 390 px) and `ui_v3/after/`
(1440 / 768 / 390 px), light and dark.

**The dark-mode bug.** The "What do these words mean?" control was a white box with pale text (1.16 : 1; the open
panel 1.07 : 1). Streamlit's own theme is fixed to light, and the dark mode in our stylesheet recoloured the text but
not the surfaces Streamlit draws itself. The fix is one token layer in `styles.css` that repaints every Streamlit-drawn
surface: buttons, the pop-up and its panel, drop-down lists, inputs, tabs and the spinner, at rest, on hover, on
focus, open and disabled. The same layer fixed the open drop-down list, which had the same problem. The control is
now called **Word guide**. `tests/test_ui_contrast.py` measures eight widget groups in a real browser in both themes
(at least 4.5 : 1) and skips itself when Playwright is missing.

**Navigation.** `st.navigation` builds a side panel:
- **Desktop.** A 240 px panel with the logo and name, the pages in three sections, a solid marker on the current
  page, and the Word guide, switches and rate note at its foot.
- **Tablet (641 to 1024 px).** A 76 px icon rail.
- **Phone.** A **Menu** button.

The example banner stays at the top of every page. There is no sideways scrolling at 390 px.

**Look.**
- **Palette.** Warm off-white `#FBF7F0` with ink `#1C2230` in light; ink navy `#141A24` with cream `#F3EEE5` in
  dark. Blue `#1F4E8C` is the primary, marigold `#E8A33D` the warm accent and `#FBEBD0` the soft tint. Each page
  group has its own tint (sand, sky, blush, sage).
- **Type and shape.** Fraunces headlines over an Inter body, radii of 8 to 12 px, underlined links and tabular
  figures.
- **Headlines.** Every page opens with a statement filled in from the saved results.
- **Removed.** Glow, glass blur, gradient text, aurora, dot grid, orbs, cursor tilt and shimmer.
- **Motion.** One entrance per page, hover responses of 160 to 180 ms, and nothing looping except the Welcome shape.
- **3D.** Three pieces remain: the Welcome shape, recoloured and slower; the year-end columns; and the cost donut.
  The forecast cone and the pattern bars were removed because they repeated flat charts.

**Checks** (`ui_v3/browser_check.py` → `browser_check.json`):
- **Pages.** 9 pages × light/dark × 1440/768/390 px, 54 views, all clean: banner present, current page marked, no
  sideways scroll, no `$`, `nan`, banned words or filler words, and no page or console errors.
- **Word guide.** Opens at every width; 13 terms.
- **Choices.** The outlook, caution level and trend pills change the view.
- **Try your own numbers.** 1,000 employees gives ₹3.97 Cr; Reset brings back ₹2.61 Cr and 500 employees.
- **3D.** The Welcome shape draws with WebGL. It shows its still version with Reduce motion and when the 3D library
  is blocked.
- **Speed and numbers.** The Overview frame time is 16.6 ms. Ten on-screen numbers equal Phase 4 × 94.1159.
- **Notes on the logs.** Streamlit's own start-up 404s for `<page>/_stcore/health` and `host-config` appear only when
  a page address is opened directly; they are counted apart. The server log shows only Windows connection resets
  when test tabs close.
- **Tests.** `python -m dashboard.colour_check` finds 0 failures. pytest: 333 passed (`ui_v3/pytest.txt`), including the browser contrast and side-navigation tests and the filler-word and "AI look" checks in `tests/test_ui_v3_copy.py`.

## Your own figures across the site, and a PDF report

- **Site-wide results.** Update results on Try your own numbers now runs all 3 outlooks × 3 caution levels plus the
  16 "what matters most" runs (`data.run_all`, 5,000 futures each, under 0.2 s of engine time). It reuses
  `engine.report` and `engine.sensitivity` unchanged, so the example company's inputs reproduce the saved Phase 4
  tables exactly (tested). With different figures, `data.table()` answers from the visitor's tables for the rest of
  the browser session:
    - the Welcome cards;
    - The big picture;
    - Where the money goes;
    - When it pays for itself;
    - What matters most.

  The banner, pill, headline, footer and About text say "your figures". A side-panel note offers **Back to the
  example**. Reset to example, that button, or a page refresh (a new session) restores the example. Update with
  the example's own figures keeps the example. The three forecast pages show public trends and stay as they are.
- **PDF report.** **Download report (PDF)** sits next to the unchanged CSV download. It builds a five-page A4 report
  only when clicked:
    1. a summary with the four cards, the verdict and the running balance;
    2. the cost split, monthly cost by type, and benefit against cost;
    3. the three outlooks, with their table and the payback-month chart;
    4. what matters most, and the figures used;
    5. the month-by-month table and notes.

  It uses matplotlib, which was already a dependency, in the light palette with rupee axes.
- **Checks.**
    - `tests/test_yours_and_pdf.py` covers:
        - the saved tables reproduced exactly;
        - every results page switching and switching back;
        - reset and a new session;
        - unchanged figures keeping the example;
        - both download buttons;
        - a valid 5-page PDF for the example and for an 18-month company.
    - In a real Chromium run at 1440 px with 1,200 employees:
        - every results page showed the new figures;
        - both downloads arrived (a 5-page PDF and the CSV);
        - Back to the example and a page refresh restored the example;
        - there was no sideways scroll at 390 px;
        - there were no console or server errors.
