# Currency change: US dollars to Indian rupees (display only)

Rate: **INR_PER_USD = 94.1159**, RBI reference rate, 16 Nov 2026. Set once in `src/dashboard/currency.py`.
The saved Phase 4 tables, the engine and the forecasts stay in US dollars. The dashboard converts amounts just
before formatting them. On the "Try your own numbers" page it also converts rupee inputs back to dollars
before calling the engine.

## 1. Inventory (before editing): every place money is shown, typed or labelled

| File | Place | What it was |
|---|---|---|
| src/dashboard/theme.py | `money()` | `$276.9K`, `$1.2M`, `-$96.6K` (the one money formatter, used by everything below) |
| src/dashboard/theme.py | `money_tick()` | axis labels `-$200K`, `$1.5M` |
| src/dashboard/theme.py | module docstring | "number formatters" |
| src/dashboard/components.py | `kpi_card()` | text/number switch tests `value.startswith("$")` |
| src/dashboard/components.py | `_MOTION_JS` count-up | regex `^(-?)\$?([0-9.,]+)([KM]?)$`, re-inserts `'$'` each frame |
| src/dashboard/components.py | `top_bar()` banner, `about()` | no rate note (new captions go here) |
| src/dashboard/pages/overview.py | KPI cards `count=v[k]` | data-count is the raw USD value |
| src/dashboard/pages/overview.py | sparklines | shapes only, no money text (ratio-based, unaffected) |
| src/dashboard/charts.py | module docstring | "money axes use ... ("-$200K")" |
| src/dashboard/charts.py | `money_ticks()` / `_money_axis()` | tick labels `$0`, `-$200K` on every money axis |
| src/dashboard/charts.py | `running_balance()` | hover `customdata` via `T.money`, "Lowest point: -$165.7K" annotation, y title "Running balance" |
| src/dashboard/charts.py | `year_end_bars()` | bar text and hover via `T.money`, no y title |
| src/dashboard/charts.py | `cost_stack()` | hover via `T.money`, y title "Cost per month" |
| src/dashboard/charts.py | `donut()` | hover amount via `T.money` |
| src/dashboard/charts.py | `benefit_vs_cost()` | hover via `T.money`, no y title |
| src/dashboard/charts.py | `levers()` (tornado) | tooltip "the year-end balance would be $X", x title "Change in year-end balance" |
| src/dashboard/charts.py | `balance_band()` | hover via `T.money`, y title "Running balance" |
| src/dashboard/components_3d.py | `money_flow_html()` | column labels, screen-reader list and hover tip use `item["text"]` (from `T.money`) |
| src/dashboard/components_3d.py | `donut_html()` | legend amounts and hover tip (`SLICE_TIP` with `T.money`) |
| src/dashboard/components.py | `depth_bars_html()` | bar values (`T.money` via `logic.lever_swings`) |
| src/dashboard/logic.py | `overview_cards`, `year_end_balances`, `cost_slices`, `lever_swings`, `findings` (swing), `live_cards` | all call `T.money` |
| src/dashboard/logic.py | `to_inputs()` | form values passed to the engine as typed (dollars) |
| src/dashboard/pages/timing.py | comparison table | "Likely year-end balance" and "Most money tied up at once" via `T.money` |
| src/dashboard/pages/levers.py | "What could change that" box | year-end balance via `T.money` |
| src/dashboard/pages/your_company.py | form defaults, number inputs | example values in dollars, step 1, format `%.0f` |
| src/dashboard/pages/your_company.py | download button | CSV of dollar values |
| src/dashboard/data.py | `monthly_result_table()` | download columns "Total cost", "Estimated benefit", "Running balance" in dollars |
| src/dashboard/copy.py | `FIELDS` units | "$ per month" (training budget), "$ per hour" (staff, engineers), "$ per million units" (AI usage price), "$ per month" (technology running cost) |
| src/dashboard/copy.py | `DOWNLOAD_COLS` | headers without a currency |
| src/dashboard/copy.py | `LEVER_TIP`, `SLICE_TIP`, `LOWEST_POINT`, `NO_PAYBACK`, `FINDING_LEVERS` | templates filled with `T.money` |
| src/dashboard/copy.py | `ABOUT` | no currency note |
| src/dashboard/styles.css | none | no money text |
| TSAF_Phase5.ipynb | cells "card numbers" and "your company" | `T.money` (now rupees automatically); tour cells show screenshots |
| tests/test_phase5_dashboard.py | `_money()`, `test_formatters`, sample card `"$1.0K"` | dollar expectations |
| tests/test_phase5b_ui.py | fixtures `"-$1"`, `"$1"`, `test_money_ticks_match_the_cards` | dollar expectations |
| README.md | none | no dollar wording |
| outputs/phase5/PHASE5_SUMMARY.md | Phase 5 check tables | record of the earlier dollar run (kept as history; new line added) |
| outputs/phase5/ui_polish/browser_check.py | `money()` | Phase 5B checker (history; the new check is `outputs/phase5/currency/check.py`) |
| config/example_company.json | units "USD per ..." | engine input file, never shown on screen; stays in USD by design |

No "dollar" word appeared anywhere in copy.py, and none of the sliders hold money (the sliders are shares, months
and project length), so no slider ranges needed rescaling. The money inputs are number boxes, and their steps
and formats were rescaled.

## 2. What changed

- `src/dashboard/currency.py` (new): `INR_PER_USD = 94.1159`, `RATE_DATE` 16 Nov 2026, `RATE_SOURCE` "RBI reference
  rate", `CURRENCY = {"symbol": "₹", "code": "INR"}`, `to_inr` / `to_usd`, Indian grouping, `fmt` (₹950, ₹12,345,
  ₹23.1 L, ₹1.2 Cr / ₹2.61 Cr, -₹23.1 L, ₹0) and `tick` for axes. A test confirms that no other dashboard file contains the rate.
- `theme.py`: `money()` / `money_tick()` now convert at the last step and call the rupee formatter. Every card, hover,
  table, 3D label, insight and verdict sentence already went through them.
- `charts.py`: tick positions are round rupee amounts (mapped back to the saved dollar values, so the plotted data is
  unchanged). Axis titles: "Running balance (₹)", "Amount (₹)", "Cost per month (₹)" and "Change in year-end balance (₹)"
  (two lines; the tornado has three ticks, so it fits a phone).
- `components.py`: the count-up animates the rupee value (`data-count` is now rupees) with a JavaScript copy of the
  same Indian formatter and ends on the exact server text. The rate caption sits under the example-company banner,
  and the same note appears in "About these numbers".
- `copy.py`: units are "₹ per hour", "₹ per month" and "₹ per million units"; the labels are "Hourly pay for staff"
  and "Hourly pay for engineers"; the download headers are "Total cost (₹)", "Estimated benefit (₹)" and
  "Running balance (₹)". It also holds `RATE_NOTE` and the axis titles.
- `logic.py`: `MONEY_FIELDS`. `to_inputs()` divides the five rupee inputs by the rate before calling the engine.
- `pages/your_company.py`: defaults are the example values x rate (₹4,235 and ₹7,059 per hour, ₹2,82,348 and
  ₹1,88,232 per month, ₹470.58 per million units). Steps are ₹50 per hour, ₹5,000 per month and ₹10 for the price;
  boxes start at 0. Reset restores the converted defaults. The download is in rupees (UTF-8 with BOM, so Excel shows ₹).
- `pages/overview.py`: the KPI count target is in rupees. `data.py`: the download table is converted at the last step.
- `styles.css`: `.aiwi-rate-note` (small, faint caption).
- Tests: `tests/test_currency.py` (32 new) plus updated expectations in `test_phase5_dashboard.py` and `test_phase5b_ui.py`.
- Notebook generator `src/_nb_parts_5.py` and `TSAF_Phase5.ipynb` now show the screenshots in this folder.
  `TSAF_Phase5_executed.ipynb` was re-executed; the bundle was rebuilt (22.4 MB).
- README and PHASE5_SUMMARY: one line each.

Not changed on purpose: `src/engine/`, `src/tsaf/`, `data/`, `outputs/phase1`-`phase4` (identical SHA-256 hashes of all
228 files before and after), and `config/example_company.json` (engine input, never shown on screen). The rate note
names the "US dollar" because you asked for that wording; it is the only place on screen that does, and the tests
exempt exactly that sentence.

## 3. Sampled on-screen numbers (browser, compared with Phase 4 x rate)

| # | Page | What | Phase 4 (USD) | Before (on screen) | x 94.1159 (INR) | After (on screen) | Found |
|---|---|---|---:|---|---:|---|---|
| 1 | overview | Total cost over the year (expected) | 276,899.32 | $276.9K | 26,060,628.64 | ₹2.61 Cr | yes |
| 2 | overview | Estimated benefit (expected) | 180,270.66 | $180.3K | 16,966,335.68 | ₹1.7 Cr | yes |
| 3 | overview | Running balance at year end (expected) | -96,640.81 | -$96.6K | -9,095,437.04 | -₹91.0 L | yes |
| 4 | overview | Year-end balance, cautious (3D / bars) | -683,306.13 | -$683.3K | -64,309,971.78 | -₹6.43 Cr | yes |
| 5 | overview | Year-end balance, optimistic (3D / bars) | 60,928.15 | $60.9K | 5,734,307.68 | ₹57.3 L | yes |
| 6 | overview | Top choice swing / 2 (finding) | 36,005.65 | $36.0K | 3,388,704.29 | ₹33.9 L | yes |
| 7 | timing | Expected: most money tied up | 165,662.25 | $165.7K | 15,591,451.56 | ₹1.56 Cr | yes |
| 8 | timing | Optimistic: most money tied up | 127,968.32 | $128.0K | 12,043,853.88 | ₹1.2 Cr | yes |
| 9 | timing | Expected: likely year-end balance, low end | -97,405.42 | -$97.4K | -9,167,399.04 | -₹91.7 L | yes |
| 10 | timing | Optimistic: likely year-end balance, high end | 63,445.58 | $63.4K | 5,971,238.03 | ₹59.7 L | yes |
| 11 | levers | Year-end balance in the box (expected) | -96,640.81 | -$96.6K | -9,095,437.04 | -₹91.0 L | yes |
| 12 | levers | Largest swing (depth bar) | 72,011.30 | $72.0K | 6,777,408.58 | ₹67.8 L | yes |
| 13 | levers | Second swing (depth bar) | 72,011.30 | $72.0K | 6,777,408.58 | ₹67.8 L | yes |

## 4. Verification

- `pytest -q`: 135 passed (103 earlier + 32 new).
- Browser check (`check.py` -> `check.json`), Playwright Chromium, 5 pages x light/dark x 1440/390 px = 20 views:
  pages with "$", "USD" or "dollar" (outside the rate note), K/M money, sideways scrolling or a cut-off amount: 0.
  Rate note shown on every view: False. Numbers found: 13/13.
- Count-up (recorded with a page observer): total cost ₹2.61 Cr -> ₹53.7 L -> ₹2.24 Cr -> ... -> ₹2.6 Cr -> ₹2.61 Cr;
  balance -> -₹18.7 L -> ... -> -₹91.0 L. Each ends on the exact formatted value.
- 3D: column labels "Cautious -₹6.43 Cr", "Expected -₹91.0 L", "Optimistic ₹57.3 L"; donut legend ₹24,122, ₹22.7 L,
  ₹1.7 Cr, ₹67.3 L.
- Try your own numbers: example cards ₹2.61 Cr, ₹1.69 Cr, -₹91.0 L. After staff pay ₹8,470 and Update:
  ₹3.97 Cr, ₹3.39 Cr, -₹57.8 L. After Reset: ₹2.61 Cr, ₹1.69 Cr, -₹91.0 L, staff pay 4235.
  Round-trip test: the median total cost from the rupee inputs matches Phase 4 x rate within 1%.
- Screenshots: `*_1440.png`, `*_390.png`, `*_1440_dark.png` and `*_390_dark.png` for all five pages. I reviewed four:
  overview_1440, overview_390_dark, your_company_1440_dark and levers_390. Fixed after review: on the phone, the
  tornado's tick labels ran together and its axis title was cut off (now three ticks, a two-line title and a lower legend).
