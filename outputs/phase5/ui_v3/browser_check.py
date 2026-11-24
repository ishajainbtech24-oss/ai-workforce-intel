"""UI v3 browser check (Playwright, Chromium). Starts its own app on port 8597 and writes browser_check.json here.

  1. every page x light/dark x 1440/768/390 px: example banner, current page marked in the side navigation, no sideways
     scroll, no '$', 'nan' or 'None', no banned or filler words on screen, no page errors or console errors;
  2. the Word guide opens at every width (on phones through the Menu button);
  3. choices: outlook and caution level on 'Where the money goes', a trend pill on 'What we expect next';
  4. Try your own numbers: 1,000 employees + Update changes the result, Reset brings the example back;
  5. 3D: the Welcome banner draws (WebGL), falls back to its still version when the 3D library is blocked, and
     after 'Reduce motion' is switched on;
  6. Overview frame time over 5 seconds;
  7. ten on-screen numbers against the Phase 4 tables x the single rupee rate.
Streamlit's own start-up 404 for <page>/_stcore/health (only when a page address is opened directly) is ignored.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))
from test_phase5_dashboard import BANNED_RE, _money  # noqa: E402

from dashboard import components_3d as K3  # noqa: E402
from dashboard import copy as C  # noqa: E402

PORT = 8597
BASE = f"http://localhost:{PORT}"
OUT = Path(__file__).with_name("browser_check.json")
LOG = Path(__file__).with_name("browser_check_server.log")  # the app's own log during the run
TABLES = ROOT / "outputs" / "phase4" / "tables"
PAGES = {"": "welcome", "overview": "overview", "data_used": "data", "forecast": "forecast", "reliability": "reliable",
         "costs": "costs", "timing": "timing", "levers": "levers", "your_company": "company"}
FILLER = ["seamlessly", "seamless", "powerful", "unlock", "leverage", "delve", "cutting-edge", "in today's world", "journey",
          "robust", "empower", "game-changer", "revolutionise", "revolutionize", "elevate"]
FILLER_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in FILLER) + r")\b", re.IGNORECASE)
GPU_ARGS = ["--enable-gpu", "--ignore-gpu-blocklist", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]

VIEW = r"""() => {
  const main = document.querySelector('[data-testid=stMain]');
  const clone = main.cloneNode(true);
  clone.querySelectorAll('[data-testid=stExpander] details:not([open]) > div, style, script, .js-plotly-plot').forEach(n => n.remove());
  const text = clone.innerText;
  const cur = [...document.querySelectorAll('[data-testid=stSidebarNav] a[aria-current=page]')]
    .map(a => a.innerText.trim().split(String.fromCharCode(10)).pop());
  return {banner: !!main.querySelector('.aiwi-banner'), current: cur,
          sideways: document.documentElement.scrollWidth > innerWidth + 1, text}; }"""


def settle(pg, ms=1500):
    pg.wait_for_selector(".aiwi-banner", timeout=120000)
    pg.wait_for_selector('[data-testid="stPlotlyChart"], [data-testid="stForm"]', timeout=120000)
    try:
        pg.wait_for_function("() => !document.querySelector('[data-testid=stSkeleton]') && "
                             "!document.querySelector('[data-testid=stStatusWidget]')", timeout=60000)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(ms)


STARTUP = re.compile(r"/_stcore/(health|host-config)$")  # Streamlit's own start-up checks on a directly opened page


def watch(pg, bag):
    """Page errors, console errors and failed requests, except Streamlit's start-up 404s (counted apart)."""
    pg.on("pageerror", lambda e: bag.append(f"pageerror: {e}"))
    pg.on("response", lambda r: (bag.append(f"startup-404: {r.url}") if STARTUP.search(r.url)
                                 else bag.append(f"http {r.status}: {r.url}")) if r.status >= 400 else None)
    # the browser's own 'Failed to load resource' line repeats a failed request, which is recorded above
    pg.on("console", lambda m: bag.append(f"console: {m.text}") if m.type == "error"
          and not m.text.startswith("Failed to load resource") else None)


def real(errs):
    return [e for e in errs if not e.startswith("startup-404")]


def all_text(pg) -> str:
    parts = [pg.evaluate("() => document.querySelector('[data-testid=stMain]').innerText")]
    for fr in pg.frames[1:]:
        try:
            parts.append(fr.evaluate("() => document.body ? document.body.innerText : ''"))
        except Exception:  # noqa: BLE001
            pass
    return " ".join(parts)


def hero_state(pg) -> dict:
    for fr in pg.frames[1:]:
        try:
            st = fr.evaluate("""() => { const h = document.querySelector('.hero'); if (!h) return null;
              const fb = document.querySelector('.fallback'); const cv = document.querySelector('canvas');
              return {canvas: !!cv && cv.width > 0, fallback_visible: !!fb && getComputedStyle(fb).display !== 'none'
                      && getComputedStyle(fb).opacity !== '0'}; }""")
        except Exception:  # noqa: BLE001
            continue
        if st:
            return st
    return {}


def main():
    srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "src" / "dashboard" / "app.py"), "--server.headless",
                            "true", "--server.port", str(PORT), "--browser.gatherUsageStats", "false"], cwd=str(ROOT),
                           stdout=subprocess.DEVNULL, stderr=LOG.open("w", encoding="utf-8"))
    res = {"views": [], "problems": []}
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(BASE + "/_stcore/health")
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch(args=GPU_ARGS)
            # 1 + 2: every page, theme and width; the Word guide at each width
            for w, h in ((1440, 900), (768, 1024), (390, 844)):
                for theme in ("light", "dark"):
                    ctx = b.new_context(viewport={"width": w, "height": h})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    watch(pg, errs)
                    for slug, key in PAGES.items():
                        pg.goto(f"{BASE}/{slug}?theme={theme}", wait_until="commit")
                        settle(pg)
                        v = pg.evaluate(VIEW)
                        text = v.pop("text")
                        row = {"page": key, "width": w, "theme": theme, **v,
                               "current_ok": v["current"] == [C.PAGES[key][0]],
                               "dollar": "$" in text, "nan_or_none": bool(re.search(r"\bnan\b|\bNone\b", text)),
                               "banned": [m.group(0) for m in BANNED_RE.finditer(text)][:3],
                               "filler": [m.group(0) for m in FILLER_RE.finditer(text)][:3]}
                        res["views"].append(row)
                        bad = (not row["banner"] or not row["current_ok"] or row["sideways"] or row["dollar"]
                               or row["nan_or_none"] or row["banned"] or row["filler"])
                        if bad:
                            res["problems"].append(row)
                    # Word guide
                    if w <= 640:
                        pg.locator('[data-testid="stExpandSidebarButton"]').click()
                        pg.wait_for_timeout(600)
                    pg.locator('[data-testid="stSidebar"] [data-testid="stPopoverButton"]').click()
                    pg.wait_for_selector('[data-testid="stPopoverBody"] dt', timeout=10000)
                    terms = pg.locator('[data-testid="stPopoverBody"] dt').count()
                    res.setdefault("word_guide", {})[f"{w}_{theme}"] = terms
                    pg.keyboard.press("Escape")
                    res.setdefault("errors", {})[f"{w}_{theme}"] = real(errs)[:5]
                    res.setdefault("startup_404s", 0)
                    res["startup_404s"] += len(errs) - len(real(errs))
                    ctx.close()

            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()
            errs = []
            watch(pg, errs)
            # 3: choices
            pg.goto(f"{BASE}/costs")
            settle(pg)
            guides = lambda: [x.inner_text() for x in pg.locator(".chart-guide").all()]  # noqa: E731
            before = guides()
            pg.get_by_role("radio", name="Cautious").first.click()
            settle(pg, 2500)
            after = guides()  # costs hardly differ by outlook; the benefit-against-cost note does
            pg.get_by_role("radio", name="More cautious").first.click()
            settle(pg, 2500)
            res["choices"] = {"outlook_changes_story": before != after,
                              "caution_level_ok": not pg.locator('[data-testid="stException"]').count()}
            pg.goto(f"{BASE}/forecast")
            settle(pg)
            head1 = pg.locator(".fc-headline").first.inner_text()
            pg.get_by_role("radio", name=C.SERIES["eci_wages_quarterly"][0]).first.click()
            settle(pg, 2500)
            res["choices"]["trend_pill_changes_view"] = pg.locator(".fc-headline").first.inner_text() != head1
            # 4: Try your own numbers
            pg.goto(f"{BASE}/your_company")
            settle(pg)
            first = pg.locator(".kpi-card").first.inner_text()
            box = pg.get_by_role("spinbutton", name="Employees (people)")
            box.fill("1000")
            pg.get_by_role("button", name=re.compile("Update results")).click()
            settle(pg, 3000)
            changed = pg.locator(".kpi-card").first.inner_text()
            pg.get_by_role("button", name=re.compile("Reset to example")).click()
            settle(pg, 3000)
            back = pg.locator(".kpi-card").first.inner_text()
            res["your_numbers"] = {"example": first, "after_update": changed, "after_reset": back,
                                   "update_changes": changed != first, "reset_restores": back == first,
                                   "employees_after_reset": box.input_value()}
            # 6: frame time on the Overview
            pg.goto(f"{BASE}/overview")
            settle(pg, 2500)
            res["overview_frame_ms"] = pg.evaluate("""() => new Promise(r => { const t = []; let last = performance.now();
              const end = last + 5000; const f = now => { t.push(now - last); last = now; if (now < end) requestAnimationFrame(f);
              else r(Math.round(t.reduce((a, b) => a + b, 0) / t.length * 100) / 100); }; requestAnimationFrame(f); })""")
            # 7: ten numbers
            tot = pd.read_csv(TABLES / "totals_summary.csv").query("multiplier == 1.0").set_index("scenario")
            br = pd.read_csv(TABLES / "cost_breakdown.csv").query("multiplier == 1.0 and scenario == 'expected'").set_index("line")
            sens = pd.read_csv(TABLES / "sensitivity.csv").sort_values("swing_cum_net_T", ascending=False)
            want = {
                "overview": {"total cost (expected)": tot.loc["expected", "total_cost_p50"],
                             "benefit (expected)": tot.loc["expected", "total_value_p50"],
                             "year-end balance (expected)": tot.loc["expected", "cum_net_T_p50"],
                             "largest lever swing": sens["swing_cum_net_T"].iloc[0]},
                "costs": {"training and support": br.loc["enablement", "p50_total"],
                          "setup and connection work": br.loc["integration", "p50_total"],
                          "technology running costs": br.loc["hosting", "p50_total"]},
                "timing": {"most money tied up (expected)": tot.loc["expected", "peak_investment_p50"],
                           "most money tied up (cautious)": tot.loc["downside", "peak_investment_p50"],
                           "most money tied up (optimistic)": tot.loc["optimistic", "peak_investment_p50"]},
            }
            res["numbers"] = []
            for slug, items in want.items():
                pg.goto(f"{BASE}/{slug}")
                settle(pg, 3000)
                text = all_text(pg)
                for label, usd in items.items():
                    res["numbers"].append({"what": label, "page": slug, "phase4_usd": round(float(usd), 2),
                                           "expected_on_screen": _money(float(usd)), "found": _money(float(usd)) in text})
            res["errors"]["checks_1440"] = real(errs)[:5]
            ctx.close()

            # 5: 3D banner, blocked library, reduced motion
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()
            errs = []
            watch(pg, errs)
            pg.goto(BASE + "/")
            settle(pg, 6000)
            res["hero_3d"] = hero_state(pg)
            pg.get_by_text("Reduce motion").first.click()
            settle(pg, 4000)
            res["hero_reduced_motion"] = {**hero_state(pg), "still_marker": pg.locator(".aiwi-still").count() > 0}
            res["errors"]["hero"] = real(errs)[:5]
            ctx.close()
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            ctx.route(K3.THREE_URL, lambda r: r.abort())
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/")
            settle(pg, 6000)
            res["hero_library_blocked"] = {**hero_state(pg), "page_errors": errs[:3]}
            ctx.close()
            b.close()
    finally:
        srv.terminate()
        srv.wait(timeout=30)
        lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        res["server_tracebacks"] = [" | ".join(lines[i:i + 14]) for i, ln in enumerate(lines) if "Traceback" in ln][:3]
        res["server_exceptions_while_pages_ran"] = [t for t in res["server_tracebacks"]
                                                    if "ConnectionResetError" not in t and "WinError 10054" not in t]
    errs_any = {k: v for k, v in res.get("errors", {}).items() if v}
    res["summary"] = {
        "views": len(res["views"]), "view_problems": len(res["problems"]),
        "word_guide_ok": all(n >= 5 for n in res.get("word_guide", {}).values()) and len(res.get("word_guide", {})) == 6,
        "choices_ok": all(res.get("choices", {}).values()),
        "your_numbers_ok": res["your_numbers"]["update_changes"] and res["your_numbers"]["reset_restores"],
        "hero_3d_draws": res["hero_3d"].get("canvas", False),
        "reduced_motion_still": res["hero_reduced_motion"].get("still_marker") and not res["hero_reduced_motion"].get("canvas"),
        "blocked_library_falls_back": res["hero_library_blocked"].get("fallback_visible") and not res["hero_library_blocked"]["page_errors"],
        "numbers_found": f"{sum(n['found'] for n in res['numbers'])}/{len(res['numbers'])}",
        "overview_frame_ms": res["overview_frame_ms"], "errors": errs_any, "startup_404s_ignored": res.get("startup_404s", 0),
        "server_tracebacks": len(res["server_tracebacks"]),
        "server_exceptions_while_pages_ran": len(res["server_exceptions_while_pages_ran"])}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["summary"], indent=1, ensure_ascii=False))
    for p_ in res["problems"][:8]:
        print("PROBLEM", p_)


if __name__ == "__main__":
    main()
