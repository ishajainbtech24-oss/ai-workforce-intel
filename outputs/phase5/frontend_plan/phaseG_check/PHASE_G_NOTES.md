# Phase 5D, step G: palette, contrast and colour-blind checks

No engine, model, forecast, Phase 1 to 4 output or package changed. Only colours and a few CSS colour rules moved.

## New: `src/dashboard/colour_check.py`

One place that measures the palette, used by the tests and runnable on its own (`python -m dashboard.colour_check` from
`src`):
- WCAG contrast for text (4.5:1) and chart marks (3:1);
- see-through colours measured **as drawn over the page** (the glass cards, raised cards, banner, pill, selected pill);
- a colour-blindness simulation (Machado et al. 2009, red-weak, green-weak and blue-weak at full severity) with CIELAB
  distances. Colours drawn together on one chart must stay at least 20 apart for every type of vision.

## What changed, and why (all measured)

| Change | Why |
|---|---|
| New chart colour roles `CHART_COLORS` (history, forecast, predicted) in `theme.py`; the forecast charts use them | On "How reliable it is" the real-values line (grey) and the predicted line (pink) were almost the same for red-weak viewers (distance 4.0 light / 2.9 dark). Now: light history `#1E293B`, forecast `#4338CA`, predicted `#A21CAF`; dark `#E2E8F0`, `#818CF8`, `#D946EF`. |
| Accent: light `#4F46E5` -> `#4338CA`, dark `#8B8CF8` -> `#818CF8` (also the Expected outlook colour; `.streamlit/config.toml` follows) | Stronger links and buttons (light 6.3 -> 7.9:1 for white text); keeps history and forecast apart for blue-weak viewers in dark mode. |
| Light outlooks: cautious `#D97706` -> `#B45309`, optimistic `#0D9488` -> `#0F766E` | The cautious line was only just above the 3:1 minimum (3.11); now 4.9 and 5.3. |
| Light faint grey `#6B7088` -> `#5F6580` | It was only just above 4.5:1 on the page (4.53). |
| Light second accent `#0D9488` -> `#0F766E` | Buttons and numbered circles fade from accent to this teal; white text reached only 3.7:1 at that end. |
| Primary buttons and numbered circles: hard-coded white text -> the theme's on-accent colour | In dark mode the gradient ends in a light teal, so white text was about 1.9:1 (this existed before Phase 5D). Now dark text in dark mode. |
| "Example company" pill text: amber -> darker amber (the banner's text colour) | It was 4.2:1 on its pale background. |
| Cost types: light sky `#7DD3FC` -> `#0284C7`, lavender `#C4B5FD` -> `#7C3AED`, plus a **fill pattern per type** in the stacked bars and the flat donut | Two light-theme cost colours were 1.6 to 1.8:1 against the card, and "AI usage cost" and "Setup and connection work" looked alike for green-weak viewers in both themes. No set of four colours passes every vision type at 3:1 contrast, so each type now also has its own pattern (the biggest one stays solid). The 3D donut keeps its legend and hover labels. |

Differences from the plan's section 6: the dark accent is `#818CF8` (the plan said `#A5B4FC`, which sat too close to the
light history line for blue-weak viewers), and the history and predicted colours differ from the plan for the
red-weak problem above. The page backgrounds and main text colours were already fine and are unchanged.

## Checks

- `tests/test_phase5d_colours.py` (11 tests): every row of the colour report passes in both themes; text on page, card,
  solid card and raised card; the contrast and simulation maths; each chart's colours stay apart for every vision type;
  the charts use the named roles; cost types carry distinct patterns; the Streamlit theme matches the accent; no
  hard-coded white text in the stylesheet. The earlier contrast test still passes. Full suite: 300 passed.
- Browser (`browser_check_G.json`, screenshots here): all nine pages, light and dark, 1440 and 390 px, on a fresh server
  (first request straight to a page): banner on all 36 views, no sideways scroll, no page or console errors. An in-page
  scan of the colour actually painted behind each piece of text found the pill (fixed) and the button gradient (fixed);
  its other low readings were measuring errors, each checked: the blurred top bar's colour mix, gradients the scan
  cannot read, and slider numbers that sit above the handle, not on it.
