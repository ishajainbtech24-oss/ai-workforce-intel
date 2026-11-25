"""Accessibility checks in a real browser at phone, tablet and desktop widths (375, 768, 1280 px), on every page:
no sideways scrolling, one main heading, every button and link has a name, and keyboard focus is visible.
Uses the same server and Chromium as tests/test_ui_contrast.py (skipped when Playwright is not installed)."""
import pytest

from test_ui_contrast import browser_app  # noqa: F401 - the shared browser + server fixture

PAGES = ["", "overview", "data_used", "forecast", "reliability", "methodology", "costs", "timing", "levers",
         "your_company"]
WIDTHS = (375, 768, 1280)

AUDIT = r"""() => {
  const vis = el => el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  const name = el => (el.getAttribute('aria-label') || el.innerText || el.title || '').trim();
  const main = document.querySelector('[data-testid=stMain]');
  return {
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    h1: [...main.querySelectorAll('h1')].filter(vis).length,
    unnamed: [...document.querySelectorAll('button, a[href], [role=button]')].filter(vis)
               .filter(el => !name(el) && !el.querySelector('img[alt]:not([alt=""]), svg[aria-label]'))
               .map(el => el.outerHTML.slice(0, 120)),
  }; }"""

FOCUS = r"""() => { const el = document.activeElement; if (!el || el === document.body) return null;
  const cs = getComputedStyle(el);
  return {tag: el.tagName, outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0,
          ring: cs.boxShadow !== 'none'}; }"""


@pytest.mark.parametrize("width", WIDTHS)
def test_pages_fit_have_one_heading_and_named_controls(browser_app, width):  # noqa: F811
    browser, base = browser_app
    problems = []
    for slug in PAGES:
        pg = browser.new_page(viewport={"width": width, "height": 900})
        pg.goto(f"{base}/{slug}?tour=off")
        pg.wait_for_selector(".aiwi-banner", timeout=120000)
        pg.wait_for_selector('[data-testid="stPlotlyChart"], [data-testid="stForm"], .steps-title', timeout=120000)
        pg.wait_for_timeout(1500)
        a = pg.evaluate(AUDIT)
        pg.close()
        if a["overflow"] > 1:
            problems.append((slug, width, "scrolls sideways", a["overflow"]))
        if a["h1"] != 1:
            problems.append((slug, width, "main headings", a["h1"]))
        if a["unnamed"]:
            problems.append((slug, width, "controls without a name", a["unnamed"][:3]))
    assert not problems, problems


def test_keyboard_focus_is_visible(browser_app):  # noqa: F811
    browser, base = browser_app
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(f"{base}/costs?tour=off")
    pg.wait_for_selector('[data-testid="stPlotlyChart"]', timeout=120000)
    pg.wait_for_timeout(1500)
    seen = []
    for _ in range(12):
        pg.keyboard.press("Tab")
        f = pg.evaluate(FOCUS)
        if f:
            seen.append(f)
    pg.close()
    assert len(seen) >= 8, seen  # the keyboard reaches the controls
    hidden = [f for f in seen if not (f["outline"] or f["ring"])]
    assert not hidden, hidden
