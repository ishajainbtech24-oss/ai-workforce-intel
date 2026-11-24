"""Text on the controls must be readable in both themes: a real browser renders the app (light and dark) and the text
colour of the top-bar controls, the word guide (closed and open), a drop-down list, the slider labels and the buttons is
measured against the colour actually painted behind it. At least 4.5 : 1 everywhere.

Skips with a message when Playwright or its Chromium is not installed (`pip install playwright` and
`python -m playwright install chromium`)."""
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from dashboard import colour_check as K

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "dashboard" / "app.py"

# returns, for every visible element with its own text inside the selector: [text, its colour, colour painted behind it]
LAYERS = r"""(sel) => {
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    const own = el.tagName === 'INPUT' ? !!el.value : [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || !el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) continue;
    const cs = getComputedStyle(el); if ((cs.fontFamily || '').includes('Material')) continue;
    const layers = [];
    for (let e = el; e; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor;
      if (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) { layers.push(bg); if (!/rgba|\//.test(bg)) break; } }
    layers.push(getComputedStyle(document.body).backgroundColor);
    out.push([(el.tagName === 'INPUT' ? el.value : el.textContent).trim().slice(0, 40), cs.color, layers]);
  }
  return out; }"""
CHECKS = [  # (name, page, selector, action)
    ("word guide control", "", '[data-testid="stPopoverButton"] p', None),
    ("word guide panel (open)", "", '[data-testid="stPopoverBody"] dt, [data-testid="stPopoverBody"] dd', "popover"),
    ("theme and motion switches", "", '[data-testid="stCheckbox"] p, [data-testid="stWidgetLabel"] p', None),
    ("buttons", "your_company", '.stButton button p, [data-testid="stPopoverButton"] p', None),
    ("slider labels and value", "your_company", '[data-testid="stSlider"] [data-testid="stWidgetLabel"] p, [data-testid="stSliderThumbValue"]', None),
    ("drop-down list (open)", "your_company", '[role="option"], [role="option"] div, [role="option"] span', "select"),
    ("trend pills, chosen and not", "forecast", '.st-key-fc_series button[data-variant] p', None),
    ("outlook and caution choices", "costs", 'button[data-variant="segmented_control"] p', None),
]


def _painted(layers: list[str]) -> str:
    """Compose the background layers (innermost first) into the colour actually painted."""
    base, _ = K.css_to_hex(layers[-1])
    for c in reversed(layers[:-1]):
        hexc, a = K.css_to_hex(c)
        base = hexc if a >= 0.999 else K.over(f"rgba({int(hexc[1:3], 16)},{int(hexc[3:5], 16)},{int(hexc[5:7], 16)},{a})", base)
    return base


def test_colour_parser_and_contrast_helper():
    assert K.css_to_hex("rgb(255, 255, 255)") == ("#FFFFFF", 1.0)
    assert K.css_to_hex("rgba(0, 0, 0, 0.5)") == ("#000000", 0.5)
    assert K.css_to_hex("color(srgb 0.5 0.25 1 / 0.4)") == ("#8040FF", 0.4)
    assert K.contrast("#ECEEF8", "#FFFFFF") < 1.2  # the old dark-mode word guide: pale text on white
    assert K.contrast("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert _painted(["rgba(255, 255, 255, 0.5)", "rgb(0, 0, 0)"]) == "#808080"


@pytest.fixture(scope="module")
def browser_app():
    sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed: pip install playwright")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(APP), "--server.headless", "true", "--server.port",
                            str(port), "--browser.gatherUsageStats", "false"], cwd=str(ROOT),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(f"http://localhost:{port}/_stcore/health")
                break
            except Exception:
                time.sleep(1)
        else:
            pytest.skip("the dashboard did not start")
        with sync_api.sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:  # noqa: BLE001
                pytest.skip(f"Chromium for Playwright is not installed (python -m playwright install chromium): {exc}")
            yield browser, f"http://localhost:{port}"
            browser.close()
    finally:
        srv.terminate()
        srv.wait(timeout=30)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_controls_are_readable(browser_app, theme):
    browser, base = browser_app
    failures, seen = [], set()
    for name, page, sel, action in CHECKS:
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f"{base}/{page}?theme={theme}")
        pg.wait_for_selector(".aiwi-banner", timeout=120000)
        pg.wait_for_selector('[data-testid="stPlotlyChart"], [data-testid="stForm"]', timeout=120000)
        pg.wait_for_timeout(2000)
        if action == "popover":
            pg.locator('[data-testid="stPopoverButton"]').first.click()
            pg.wait_for_selector('[data-testid="stPopoverBody"]', timeout=10000)
        elif action == "select":
            opener = pg.locator('[data-testid="stSelectbox"] .react-aria-ComboBox button').first
            opener.scroll_into_view_if_needed()
            opener.click()
            pg.wait_for_selector('[role="option"]', timeout=10000)
        pg.wait_for_function("s => document.querySelectorAll(s).length > 0", arg=sel, timeout=30000)
        pg.wait_for_timeout(600)
        found = pg.evaluate(LAYERS, sel)
        pg.close()
        assert found, f"{name}: nothing found to measure ({sel})"
        seen.add(name)
        for text, fg, layers in found:
            ratio = K.contrast(K.css_to_hex(fg)[0], _painted(layers))
            if ratio < K.TEXT_MIN:
                failures.append((name, text, fg, layers[:2], round(ratio, 2)))
    assert seen == {c[0] for c in CHECKS}
    assert not failures, failures


SIDEBAR = r"""() => ({
  links: [...document.querySelectorAll('[data-testid=stSidebarNav] a')].map(a => ({
    name: a.innerText.trim().split(String.fromCharCode(10)).pop(), current: a.getAttribute('aria-current')})),
  controls: !!document.querySelector('[data-testid=stSidebar] .st-key-aiwi_sidecontrols'),
  wordGuide: [...document.querySelectorAll('[data-testid=stSidebar] [data-testid=stPopoverButton]')].map(b => b.innerText.trim()),
  banner: !!document.querySelector('[data-testid=stMain] .aiwi-banner'),
  topNav: !!document.querySelector('[data-testid=stTopNav]')})"""


def test_side_navigation_lists_every_page_and_marks_the_current_one(browser_app):
    from dashboard import copy as C
    browser, base = browser_app
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(f"{base}/timing")
    pg.wait_for_selector('[data-testid="stSidebarNav"] a', timeout=120000)
    pg.wait_for_selector('[data-testid="stPlotlyChart"]', timeout=120000)
    pg.wait_for_timeout(1500)
    info = pg.evaluate(SIDEBAR)
    pg.close()
    names = [link["name"] for link in info["links"]]
    assert names == [C.PAGES[k][0] for k in ("welcome", "overview", "data", "forecast", "reliable", "costs", "timing",
                                             "levers", "company")]
    assert [link["name"] for link in info["links"] if link["current"] == "page"] == [C.PAGES["timing"][0]]
    assert info["controls"] and any(C.GLOSSARY_BUTTON in t for t in info["wordGuide"])
    assert info["banner"] and not info["topNav"]
