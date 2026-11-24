# Phase 5D, step F: The big picture and When it pays for itself

No engine, model, forecast, Phase 1 to 4 output or package changed; every new number is read from saved files.

## The big picture (`src/dashboard/views/overview.py`)

- **Top**: the glass 3D banner with the product promise is gone from this page. It repeated the Welcome headline word
  for word. The page now opens with a compact title and one line on what it shows.
- **Four KPI cards**: unchanged (₹2.61 Cr, ₹1.7 Cr, -₹91.0 L, Not within 12 months).
- **Running balance chart** (unchanged) now sits next to **What needs a decision**: the three choices with the widest
  gap between 20% lower and 20% higher (`sensitivity.csv`): time saved per person (₹67.8 L), share of saved time that
  becomes value (₹67.8 L), training hours per new user (₹37.7 L), each with which direction helps; link to What matters most.
- **The trends behind the costs** (new): pay levels +6.8% by Q3 2028 and technology hosting prices +1.5% by Oct 2027
  (saved Phase 3 forecasts against the latest real value), and how close past predictions came (Phase 2 held-back
  stretch): pay about 0.7% off, hosting prices about 2.0%, AI usage 43% to 73%. Links to What we expect next and
  How reliable it is.
- **Key findings**: unchanged.
- **See the year-end balance in 3D**: the 3D columns and the plain bars now sit in a panel that opens on request.

## When it pays for itself (`src/dashboard/views/timing.py`)

- New **When each outlook pays for itself** strip above the month-by-month bars: one dot per outlook at its typical
  month, or in the "Not within 12 months" column (`break_even_summary.csv`, follows the caution setting). Hover text
  says it in words, e.g. "Optimistic outlook: typically pays for itself in month 11; 100% of the futures we looked at pay
  for themselves within 12 months" / "Expected outlook: does not pay for itself within 12 months in 100% of the futures
  we looked at".

## 3D pieces now

Four are shown: the year-end columns (in the panel), the cost donut, the depth bars, the background orbs. The glass
banner is no longer on any page; its code and its still version are kept (`components_3d.hero_html`) and still tested,
so it can be placed on Welcome later if wanted. The plan allows at most five.

## Checks

- `tests/test_phase5d_overview.py` (7 tests): decision list equals the top three rows of `sensitivity.csv` (amounts and
  direction recomputed); the strip's changes equal the saved forecasts and processed data (+6.8%, +1.5%) and the miss
  shares equal `holdout.csv`; the page shows all of it, no longer shows the Welcome headline, and has the 3D panel; dot
  positions equal `break_even_summary.csv` at all three caution levels; no banned or technical words.
- Existing number tests for the KPI cards, 3D values, chart notes and money ticks still pass. Full suite: 289 passed.
- Browser (`browser_check_F.json`, screenshots here): fresh server with The big picture opened directly as the first
  request; 1440, 768 and 390 px, light and dark; KPI values, strip values and decision list as above; the 3D panel opens
  (3D columns and plain bars); When it pays for itself with the dot strip, switched to "Most cautious"; banner and styles
  on every view, no sideways scroll on either page, no "$", no technical words, no page or console errors.
