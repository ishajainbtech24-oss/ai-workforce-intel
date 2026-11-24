# UI v3 critique (before) and widget checklist

"Before" screenshots: `before/<page>_<1440|390>_<light|dark>.png` (all 9 pages, both themes, desktop and phone, taken
with Playwright on a fresh server). Widget measurements: `widget_audit_before.json`.

## The bug: "What do these words mean?" in dark mode

Measured, not guessed (computed styles in Chromium, dark theme): the control's **background is `rgb(255,255,255)`**
while its **text is `rgb(236,238,248)`**, the dark theme's text colour: contrast **1.16 : 1**. The open panel is the
same: near-white `#F5F6FB` behind `#ECEEF8` text, **1.07 : 1**.

Cause: Streamlit cannot switch its own theme per visitor, so `.streamlit/config.toml` fixes Streamlit's built-in theme to
light, and the dashboard's dark mode is drawn by our stylesheet. That stylesheet recolours text everywhere (so the label
turned pale) but never recoloured the pop-up control and its panel, which kept Streamlit's built-in white button and
white panel. Every widget Streamlit draws from its built-in theme is at risk in the same way.

## Widget checklist (before the fix)

Contrast of each widget's text against the colour actually painted behind it (minimum 4.5 : 1).

| Widget | Light | Dark | Note |
|---|---|---|---|
| Word guide control (closed) | OK 18.6 | **Fails 1.16** | white button, pale text |
| Word guide panel (open) | OK 7.5 | **Fails 1.07** | white panel, pale text |
| Toggles (labels) | OK 7.5 | OK 9.8 | |
| Expanders | OK 18.2 | OK 15.4 | |
| Primary link button | OK 7.9 | OK 6.5 | |
| Secondary button | OK 17.2 | OK 16.7 | |
| Form submit (gradient) | OK (checked by hand: 5.5 / 10.4 at the ends) | OK | the scan cannot read gradients |
| Number input | OK | OK 13.6 | |
| Selectbox (closed) | OK 18.2 | OK 13.6 | |
| Selectbox list (open) | not measured | not measured | the click did not open it in the scan; covered by the new test |
| Slider (label and value) | not measured | not measured | covered by the new test |
| Segmented control | OK 14.7 | OK 14.0 | |
| Pills | OK 18.6 | OK 14.8 | |
| Download button | OK 18.6 | OK 14.8 | |
| Tabs | OK 17.2 | OK 16.7 | |
| Tooltip (help) | OK 18.5 | OK 14.9 | |
| Page links / Next card | OK 7.7 | OK 6.0 | |
| Alert (warning) | OK 18.5 | OK 13.7 | |
| Tables | OK 7.9 | OK 9.1 | |

## Ten critique points (what looks plain, crowded or "AI-made")

1. **The purple-indigo-to-teal glow is everywhere**: hero gradient, gradient headline text, gradient buttons, gradient
   numbered circles, gradient card edges. It is the most common "generated" look there is.
2. **Glass on every card.** Every block is a translucent, blurred, rounded card with a glowing edge, so nothing stands
   out; the eye has no anchor.
3. **Decoration with no meaning**: aurora backdrop, dot-grid overlay, floating blurred orbs, cursor tilt with a moving
   light on the cards, shimmer. None of it says anything about the data.
4. **Identical cards in identical grids**: four equal KPI cards, three equal findings, three equal ideas, three equal
   steps. No lead, no rhythm; the most important number is the same size as the least.
5. **One typeface voice**: a geometric sans for everything (headlines included). Nothing feels edited; there is no
   contrast between a headline and a label.
6. **Headings that are labels, not statements**: "Where the money goes", "Key findings", "What it means". The point
   (most of the cost is training, not technology) is buried in body text.
7. **Navigation sits in a crowded top bar** with drop-down menus, the product name, a pill, the word guide and two
   switches all competing on one line; on phones it hides behind a small "Pages" button.
8. **Too much 3D**: seven pieces (knot, columns, donut, cone, pattern bars, depth bars, orbs). The cone and the
   pattern bars repeat flat charts that are right next to them.
9. **The word guide is broken in dark mode** (white box, unreadable text), and Streamlit-drawn widgets depend on the
   stylesheet catching each one.
10. **Cold colour**: cool grey-lilac background, indigo accent, teal second accent. Nothing warm, nothing confident;
    the only warm colour is the warning amber, so warmth reads as "danger".

## Reference page

`https://colorlib.com/wp/best-websites/` was fetched (19 March 2026 article). Its text describes very little colour: a
yellow accent that "adds warmth and energy" on a bakery site, a deep purple-and-pink gradient on one SaaS site, dark
designs for a premium feel, contrasting colours for call-to-action buttons, and plenty of white space; nothing on
typography. The images were not seen. So the palette below follows the default direction of the brief, using only
those two points (a warm yellow-orange accent; strong contrast on the main buttons).

---

# After (UI v3)

"After" screenshots: `after/<page>_<1440|768|390>_<light|dark>.png` (54 full-page shots). Browser run:
`browser_check.py` → `browser_check.json`. Contrast test: `tests/test_ui_contrast.py`.

## The fix

One token layer in `src/dashboard/styles.css` ("Streamlit-drawn widgets") repaints every surface Streamlit draws from
its built-in light theme: secondary, tertiary, pop-up and download buttons, the pop-up panel (`stPopoverBody`), the
drop-down list (`stSelectboxVirtualDropdown`, `[role=listbox]`, `[role=option]`), inputs, spinner, tabs, and their
hover, focus, open and disabled states. Each one takes `--surface-solid` / `--elevated` / `--text` / `--accent`, so
it follows the theme. A second instance found on the way: the open drop-down list was also painted light in dark
mode (fixed by the same layer). A third, found in the "after" screenshots: the **selected trend pill** was blank
(a stronger CSS rule painted it white while its text turned white); fixed and added to the test.

## Widget checklist (after)

Measured in Chromium by `tests/test_ui_contrast.py` (text colour against the colour actually painted behind it,
composited through every translucent layer; minimum 4.5 : 1). All pass in both themes.

| Widget | Light | Dark |
|---|---|---|
| Word guide control (closed) | OK | OK (#F3EEE5 on #1D2431, 13.5) |
| Word guide panel (open) | OK | OK |
| Dark mode / Reduce motion switches | OK | OK |
| Buttons (Update, Reset, pop-up) | OK | OK |
| Slider labels and value | OK | OK |
| Drop-down list (open) | OK | OK |
| Trend pills, chosen and not | OK (white on #1F4E8C, 8.3) | OK |
| Outlook and caution choices | OK | OK |

## Palette (tokens in `src/dashboard/theme.py`)

| Token | Light | Contrast on page / card | Dark | Contrast on page / card |
|---|---|---|---|---|
| bg (page) | `#FBF7F0` warm off-white | | `#141A24` ink navy | |
| bg-2 | `#F3ECE0` | | `#1A2130` | |
| surface (card) | `#FFFFFF` | | `#1D2431` | |
| text | `#1C2230` | 14.9 / 15.9 | `#F3EEE5` | 15.1 / 13.5 |
| muted | `#4A5163` | 7.4 / 7.9 | `#CBC4B7` | 10.1 / 9.0 |
| faint | `#5A6070` | 5.9 / 6.3 | `#ADA699` | 7.2 / 6.4 |
| **primary** (accent) | `#1F4E8C` deep blue | 7.8 / 8.3 | `#8DB3EC` | 8.1 / 7.3 |
| **warm accent** (marigold) | `#E8A33D` | fills only (2.0, never text) | `#F2B45A` | 9.5 / 8.5 |
| warm text | `#6B3405` | 9.3 / 9.9 | `#F6CC8F` | 11.6 / 10.3 |
| **soft tint** (marigold-soft) | `#FBEBD0` | warm text on it 8.4 | marigold 16% | |
| second accent | `#0F766E` | 5.1 / 5.5 | `#5CC2B0` | 8.1 / 7.3 |
| good | `#1F6F5C` | 5.6 / 6.0 | `#86CF94` | 9.4 / 8.4 |
| text on primary | `#FFFFFF` | 8.3 | `#141A24` | 8.1 |

Page personalities (the tinted band behind each page headline): sand `#F6EBD9` (Welcome, big picture), sky `#E4EDF7`
(the three forecast pages), blush `#F8E7E0` (the money pages), sage `#E5EEE3` (Try your own numbers); dark versions
`#262420`, `#1C2737`, `#2B2226`, `#1E2A25`.

Outlook colours (lines on cards ≥ 3 : 1): light cautious `#B4580A`, expected `#1F4E8C`, optimistic `#0F8F8A`; dark
`#F2B45A`, `#8DB3EC`, `#5FD8B5`. Colour-blind check (`python -m dashboard.colour_check`, Machado simulation, CIELAB):
the closest pair in any vision type is expected/optimistic under tritan, ΔE 24.8 light and 23.4 dark (needed ≥ 20);
lines also differ by dash pattern. 0 failures in either theme.

Fonts: **Fraunces** (serif, headlines, big figures, Next links) and **Inter** (body, labels, numbers with tabular
figures), from Google Fonts with Georgia / system-sans fall-backs. Radii 8 / 12 / 16 px. Labels in small caps
(spaced capitals). Links in the text are underlined.

## Each critique point, answered

1. Purple-to-teal glow: gone. One blue primary, one marigold warm accent; no gradient text, buttons or circles.
2. Glass: gone. Solid cards with one soft warm shadow; no blur.
3. Meaningless decoration: aurora, dot grid, orbs, cursor tilt, shimmer and the pulsing active pill are removed; the
   only motion is one entrance per page (0.32 s), line draw-on and the count-up, plus 150 to 200 ms hover responses.
   Nothing loops except the Welcome shape, which turns slowly and stops with Reduce motion.
4. Identical grids: the running balance now leads the big picture as a wide marigold card with a 40 to 56 px figure;
   findings use a 1.3 / 1 / 1 grid; chart guides sit under a rule.
5. One voice: serif headlines over a sans body.
6. Labels as headings: every page opens with a statement filled in from the saved results ("Most of the cost is
   people, not technology", "Only the optimistic outlook pays for itself within 12 months").
7. Crowded top bar: replaced by a 240 px side panel (sections Forecasts / The money / Your own figures, a solid
   3 px marker on the current page) with the Word guide, switches and rate note at its foot. Tablets get a 76 px
   icon rail; phones a "Menu" button.
8. Too much 3D: down to three (Welcome shape, year-end columns, cost donut), recoloured to ink, cream and marigold,
   slower, fewer particles, no grid floor. The cone and the pattern bars are gone (they repeated flat charts).
9. Word guide in dark mode: fixed at the root and tested.
10. Cold colour: warm off-white and ink navy, a marigold accent that means "look here" rather than "danger".
