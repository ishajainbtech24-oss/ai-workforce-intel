"""Full-page screenshots of every dashboard page (Playwright, Chromium).

Usage: python outputs/phase5/ui_polish/shoot.py <out_dir> [--theme light|dark] [--widths 1440,390] [--pages a,b]
Needs the app running on http://localhost:8501. Streamlit scrolls inside its own container, so the viewport is
grown to the page height before each capture.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8501"
PAGES = {"overview": "", "costs": "costs", "timing": "timing", "levers": "levers", "your_company": "your_company"}


def settle(page, ms: int = 2500) -> None:
    page.wait_for_selector('[data-testid="stMain"]', timeout=60000)
    page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"] [data-testid=\"stSpinner\"]')",
                           timeout=60000)
    page.wait_for_timeout(ms)


def full_height(page) -> int:
    return page.evaluate("""() => { const m = document.querySelector('[data-testid="stMain"]');
      const kids = [document.documentElement, document.body, m, m && m.firstElementChild].filter(Boolean);
      return Math.max(...kids.map(e => e.scrollHeight)); }""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--theme", default="")
    ap.add_argument("--widths", default="1440,390")
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
        for w in (int(x) for x in a.widths.split(",")):
            ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1,
                                color_scheme="dark" if a.theme == "dark" else "light")
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
            for name in a.pages.split(","):
                q = f"?theme={a.theme}" if a.theme else ""
                page.goto(f"{BASE}/{PAGES[name]}{q}")
                settle(page)
                h = min(full_height(page), 9000)
                page.set_viewport_size({"width": w, "height": h})
                page.wait_for_timeout(1500)
                try:
                    page.wait_for_function("() => !document.querySelector('[data-testid=\"stSkeleton\"], .stSkeleton')",
                                           timeout=45000)
                except Exception:  # noqa: BLE001 - capture anyway and say so
                    print(f"note: {name} at {w}px still showed a loading placeholder")
                page.wait_for_timeout(2500)
                f = out / f"{name}_{w}{a.suffix}.png"
                page.screenshot(path=str(f))
                page.set_viewport_size({"width": w, "height": 900})
                print(f, h)
            ctx.close()
        b.close()
    for e in errors:
        print(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
