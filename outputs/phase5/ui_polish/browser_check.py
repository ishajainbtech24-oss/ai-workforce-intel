"""Browser check of the polished dashboard (Playwright, Chromium). Needs the app on http://localhost:8501.

Runs, and writes the results to outputs/phase5/ui_polish/browser_check.json:
  1. main run (1440 px): every page through the top navigation, dark mode on and off, outlooks switched, the Costs
     "Flat view / 3D view" switch, a drag on the Overview 3D columns, Try your own numbers (1,000 employees, Update),
  2. smoothness: average frame time of the Overview for 5 seconds (requestAnimationFrame + performance.now),
  3. the 3D download blocked, 4. WebGL switched off, 5. reduced motion: every 3D piece must fall back silently,
  6. phone width (375 px): no sideways scrolling on any page,
  7. the banned-word scan on the final rendered text (page, 3D frames, tooltips and labels),
  8. ten or more on-screen numbers compared with the Phase 4 tables.
Console errors and page errors from every run are collected; Streamlit's own start-up 404 for <page>/_stcore/health
(only when a page address is opened directly) is listed separately.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
BASE = "http://localhost:8501"
OUT = Path(__file__).with_name("browser_check.json")
TABLES = ROOT / "outputs" / "phase4" / "tables"
NAV = {"overview": "/", "costs": "/costs", "timing": "/timing", "levers": "/levers", "your_company": "/your_company"}
GPU_ARGS = ["--enable-gpu", "--ignore-gpu-blocklist", "--use-angle=d3d11", "--enable-unsafe-swiftshader"]


def banned_re():
    src = (ROOT / "tests" / "test_phase5_dashboard.py").read_text(encoding="utf-8")
    words = eval(re.search(r"BANNED = (\[.*?\])\n", src, re.S).group(1))  # noqa: S307 - our own test file
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)


def money(x: float) -> str:
    a = abs(x)
    body = f"${a / 1e6:.1f}M" if a >= 1e6 else f"${a / 1e3:.1f}K" if a >= 1e3 else f"${a:,.0f}"
    return ("-" if x < 0 else "") + body


def settle(page, ms=1800):
    page.wait_for_selector('[data-testid="stMain"]', timeout=60000)
    try:
        page.wait_for_function("() => !document.querySelector('[data-testid=\"stSkeleton\"]')", timeout=45000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(ms)


def go(page, name):
    page.click(f'a[data-testid="stTopNavLink"][href="{BASE}{NAV[name]}"]')
    settle(page)


def frame_with(page, selector: str):
    for f in page.frames:
        try:
            if f.evaluate(f"() => !!document.querySelector({json.dumps(selector)})"):
                return f
        except Exception:  # noqa: BLE001
            pass
    return page.main_frame


def all_text(page) -> str:
    parts = []
    for f in page.frames:
        try:
            parts.append(f.evaluate("""() => { const t = [document.body ? document.body.innerText : ''];
              document.querySelectorAll('[title],[aria-label],[alt]').forEach(e => t.push(e.getAttribute('title') || '',
                e.getAttribute('aria-label') || '', e.getAttribute('alt') || ''));
              return t.join(' '); }"""))
        except Exception:  # noqa: BLE001
            pass
    return " ".join(parts)


def frames_state(page) -> dict:
    out = {}
    for f in page.frames:
        try:
            s = f.evaluate("() => { const r = document.getElementById('root'); const st = document.getElementById('stage');"
                           " return r && st ? {live: r.classList.contains('live'), canvas: !!st.querySelector('canvas'),"
                           " fallback: !!document.querySelector('.fallback')} : null }")
        except Exception:  # noqa: BLE001
            s = None
        if s:
            key = f.evaluate("() => { const c = document.getElementById('cfg'); return c ? JSON.parse(c.textContent).id :"
                             " (document.querySelector('.hero') ? 'hero' : document.querySelector('.fcol') ? 'flow' : 'donut') }")
            out[key] = s
    return out


def tooltips(page) -> str:
    """Hover every help icon once and collect the tooltip text."""
    texts = []
    for b in page.query_selector_all('[data-testid="stTooltipHoverTarget"] button')[:12]:
        try:
            b.hover()
            page.wait_for_timeout(350)
            t = page.query_selector('[data-testid="stTooltipContent"]')
            if t:
                texts.append(t.inner_text())
        except Exception:  # noqa: BLE001
            pass
    page.mouse.move(5, 5)
    return " ".join(texts)


def collect(page, sink: list):
    page.on("pageerror", lambda e: sink.append(f"pageerror: {e}"))
    page.on("console", lambda m: sink.append(f"console.{m.type}: {m.text} @ {m.location.get('url', '')}")
            if m.type == "error" else None)


def main() -> int:
    res: dict = {"errors": {}, "steps": [], "notes": []}
    bre = banned_re()
    with sync_playwright() as p:
        # ---------------------------------------------------------------- 1. main run
        b = p.chromium.launch(args=GPU_ARGS)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errs: list = []
        collect(page, errs)
        page.goto(BASE + "/")
        settle(page, 4000)
        res["webgl_renderer"] = frame_with(page, ".hero").evaluate(
            "() => { const g = document.createElement('canvas').getContext('webgl'); if (!g) return 'none';"
            " const i = g.getExtension('WEBGL_debug_renderer_info'); return i ? g.getParameter(i.UNMASKED_RENDERER_WEBGL) : 'unknown' }")
        res["frames_overview"] = frames_state(page)
        text = {"overview": all_text(page) + " " + tooltips(page)}
        # drag the 3D columns
        box = page.evaluate("""() => { for (const f of document.querySelectorAll('iframe')) {
            const d = f.contentDocument; if (d && d.querySelector('.fcol')) { f.scrollIntoView({block: 'center'});
              const r = f.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; } } return null; }""")
        page.wait_for_timeout(1500)
        box = page.evaluate("""() => { for (const f of document.querySelectorAll('iframe')) { const d = f.contentDocument;
            if (d && d.querySelector('.fcol')) { const r = f.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; } }
            return null; }""")
        if box:
            el = page.query_selector_all("iframe")
            target = [e for e in el if e.bounding_box() and abs(e.bounding_box()["y"] - box["y"]) < 2][0]
            before = target.screenshot()
            cx, cy = box["x"] + box["w"] * 0.5, box["y"] + box["h"] * 0.6
            page.mouse.move(cx, cy); page.mouse.down(); page.mouse.move(cx + 160, cy, steps=12); page.mouse.up()
            page.mouse.move(cx - 60, cy - 20)
            page.wait_for_timeout(600)
            after = target.screenshot()
            res["steps"].append({"step": "drag the 3D columns", "picture_changed": before != after})
        # 2. smoothness on the Overview (scroll back to the hero)
        page.evaluate("() => document.querySelector('[data-testid=stMain]').scrollTo(0, 0)")
        page.wait_for_timeout(1200)
        page.mouse.move(700, 300)
        ft = frame_with(page, ".hero").evaluate("""() => new Promise(done => { const d = []; let last = performance.now(); const t0 = last;
            const f = (t) => { d.push(t - last); last = t; if (t - t0 < 5000) requestAnimationFrame(f); else {
              d.sort((a, b) => a - b); done({frames: d.length, mean_ms: d.reduce((a, b) => a + b, 0) / d.length,
                p95_ms: d[Math.floor(d.length * 0.95)], max_ms: d[d.length - 1]}); } }; requestAnimationFrame(f); })""")
        res["frame_time_overview"] = ft
        # dark mode on, every page, outlooks, 3D switch
        page.get_by_text("Dark mode", exact=True).click()
        settle(page)
        res["steps"].append({"step": "dark mode on", "bg": page.evaluate(
            "() => getComputedStyle(document.querySelector('.stApp')).backgroundColor")})
        for name in ("costs", "timing", "levers", "your_company"):
            go(page, name)
            res["steps"].append({"step": f"open {name} (dark)", "charts": len(page.query_selector_all(".js-plotly-plot"))})
        page.get_by_text("Dark mode", exact=True).click()
        settle(page)
        go(page, "costs")
        text["costs"] = all_text(page) + " " + tooltips(page)
        res["frames_costs"] = frames_state(page)
        page.get_by_role("radio", name="Optimistic").first.click(); settle(page)
        page.get_by_role("radio", name="Flat view").click(); settle(page)
        flat = page.evaluate("() => [...document.querySelectorAll('.js-plotly-plot')].some(g => (g.data || []).some(t => t.type === 'pie'))")
        page.get_by_role("radio", name="3D view").click(); settle(page)
        res["steps"].append({"step": "costs: optimistic, flat view then 3D view", "flat_donut_shown": flat,
                             "3d_back": "donut" in frames_state(page)})
        go(page, "timing")
        page.get_by_role("radio", name="Cautious").first.click(); settle(page)
        page.get_by_role("radio", name="More cautious").click(); settle(page)
        text["timing"] = all_text(page) + " " + tooltips(page)
        page.get_by_role("radio", name="Expected").first.click(); page.get_by_role("radio", name="Standard").click(); settle(page)
        text["timing_standard"] = all_text(page)
        go(page, "levers")
        text["levers"] = all_text(page) + " " + tooltips(page)
        go(page, "your_company")
        emp = page.get_by_role("spinbutton", name="Employees (people)")
        emp.fill("1000"); emp.press("Tab")
        page.get_by_role("button", name=re.compile("Update results")).click()
        settle(page, 3500)
        text["your_company"] = all_text(page) + " " + tooltips(page)
        kp = page.evaluate("() => [...document.querySelectorAll('.kpi-value')].map(e => e.textContent)")
        res["steps"].append({"step": "your company: 1,000 employees, Update results", "cards": kp})
        page.get_by_role("button", name=re.compile("Reset to example")).click(); settle(page, 3000)
        page.wait_for_function("() => document.querySelectorAll('.kpi-value').length >= 4", timeout=60000)
        res["steps"].append({"step": "reset to example", "cards": page.evaluate(
            "() => [...document.querySelectorAll('.kpi-value')].map(e => e.textContent)")})
        go(page, "overview")
        text["overview_again"] = all_text(page)
        res["errors"]["main"] = errs
        ctx.close()

        # ---------------------------------------------------------------- 3-5. fallbacks
        def fallback_run(label, browser, ctx_kwargs=None, block=False):
            c = browser.new_context(viewport={"width": 1440, "height": 900}, **(ctx_kwargs or {}))
            if block:
                c.route(re.compile(r".*cdn\.jsdelivr\.net.*"), lambda r: r.abort())
            pg = c.new_page()
            e: list = []
            collect(pg, e)
            pg.goto(BASE + "/")
            settle(pg, 5000)
            st = {"overview": frames_state(pg)}
            go(pg, "costs")
            st["costs"] = frames_state(pg)
            res["errors"][label] = e
            res[f"frames_{label}"] = st
            c.close()

        fallback_run("cdn_blocked", b, block=True)
        fallback_run("reduced_motion", b, {"reduced_motion": "reduce"})
        b.close()
        b2 = p.chromium.launch(args=["--disable-webgl", "--disable-3d-apis"])
        fallback_run("no_webgl", b2)
        b2.close()

        # ---------------------------------------------------------------- 6. phone width
        b3 = p.chromium.launch(args=GPU_ARGS)
        c = b3.new_context(viewport={"width": 375, "height": 800}, is_mobile=False)
        pg = c.new_page()
        e: list = []
        collect(pg, e)
        widths = {}
        for name, path in NAV.items():
            pg.goto(BASE + path)
            settle(pg, 2500)
            widths[name] = pg.evaluate("() => { const m = document.querySelector('[data-testid=stMain]');"
                                       " return Math.max(document.documentElement.scrollWidth, m.scrollWidth) }")
        res["phone_375_scroll_width"] = widths
        res["errors"]["phone"] = e
        c.close()
        b3.close()

    # ---------------------------------------------------------------- 7. banned words
    hits = {}
    for k, t in text.items():
        m = [x.group(0) for x in bre.finditer(t)]
        if m:
            hits[k] = sorted(set(m))
    res["banned_word_hits"] = hits

    # ---------------------------------------------------------------- 8. numbers
    tot, be = pd.read_csv(TABLES / "totals_summary.csv"), pd.read_csv(TABLES / "break_even_summary.csv")
    br, se = pd.read_csv(TABLES / "cost_breakdown.csv"), pd.read_csv(TABLES / "sensitivity.csv")
    ms = pd.read_csv(TABLES / "monthly_summary.csv")
    r = lambda t, sc, k=1.0: t[(t.scenario == sc) & (t.multiplier == k)].iloc[0]  # noqa: E731
    eb = br[(br.scenario == "expected") & (br.multiplier == 1.0)].set_index("line")
    low = ms[(ms.scenario == "expected") & (ms.multiplier == 1.0) & (ms.line == "cumulative_net")]["p50"].min()
    checks = [
        ("overview", "Total cost (expected)", money(r(tot, "expected").total_cost_p50)),
        ("overview", "Estimated benefit (expected)", money(r(tot, "expected").total_value_p50)),
        ("overview", "Running balance at year end (expected)", money(r(tot, "expected").cum_net_T_p50)),
        ("overview", "3D columns: cautious year-end balance", money(r(tot, "downside").cum_net_T_p50)),
        ("overview", "3D columns: optimistic year-end balance", money(r(tot, "optimistic").cum_net_T_p50)),
        ("overview", "Lowest point of the expected line", money(low)),
        ("overview", "Training and support share", f"{eb.loc['enablement', 'p50_share_of_cost']:.0%}"),
        ("costs", "3D donut: training and support (optimistic outlook shown)", money(
            br[(br.scenario == "optimistic") & (br.multiplier == 1.0) & (br.line == "enablement")].p50_total.iloc[0])),
        ("timing_standard", "Expected most money tied up", money(r(tot, "expected").peak_investment_p50)),
        ("timing_standard", "Optimistic likely year-end balance",
         f"{money(r(tot, 'optimistic').cum_net_T_p10)} to {money(r(tot, 'optimistic').cum_net_T_p90)}"),
        ("timing_standard", "Optimistic pays for itself", f"Month {int(round(r(be, 'optimistic').p50_month))}"),
        ("levers", "Top lever gap (depth bars)", money(se.sort_values("swing_cum_net_T").swing_cum_net_T.iloc[-1])),
        ("levers", "Expected year-end balance in the box", money(r(tot, "expected").cum_net_T_p50)),
    ]
    res["numbers"] = [{"page": pg_, "what": w, "expected_text": v, "on_screen": v in text[pg_]} for pg_, w, v in checks]
    sys.path.insert(0, str(ROOT / "src"))
    from dashboard import copy as C
    res["banner_on_every_page"] = {k: C.BANNER in t for k, t in text.items()}

    def real(errors):
        return [x for x in errors if "_stcore/health" not in x and "status of 404" not in x]
    res["errors_excluding_streamlit_health_404"] = {k: real(v) for k, v in res["errors"].items()}
    # With the download blocked on purpose, Chrome itself prints one network notice for the blocked file; no page
    # script can silence that. Anything else in that run (a script error, a second notice) still fails the check.
    blocked = res["errors_excluding_streamlit_health_404"].get("cdn_blocked", [])
    res["expected_browser_network_notice"] = [x for x in blocked if "Failed to load resource" in x and "cdn.jsdelivr.net" in x]
    res["errors_excluding_streamlit_health_404"]["cdn_blocked"] = [x for x in blocked if x not in res["expected_browser_network_notice"]]
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    ok = (not any(res["errors_excluding_streamlit_health_404"].values()) and not hits
          and all(n["on_screen"] for n in res["numbers"]) and all(v <= 375 for v in widths.values())
          and all(res["banner_on_every_page"].values()) and "$276.9K" in res["steps"][-1]["cards"])
    print(json.dumps({k: res[k] for k in ("webgl_renderer", "frame_time_overview", "phone_375_scroll_width",
                                         "banned_word_hits", "errors_excluding_streamlit_health_404")}, indent=1))
    print("banner:", res["banner_on_every_page"])
    print("numbers:", sum(n["on_screen"] for n in res["numbers"]), "/", len(res["numbers"]))
    for k in ("frames_overview", "frames_costs", "frames_cdn_blocked", "frames_no_webgl", "frames_reduced_motion"):
        print(k, res.get(k))
    print("steps:", json.dumps(res["steps"]))
    print("ALL OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    t0 = time.time()
    code = main()
    print(f"{time.time() - t0:.0f} s")
    sys.exit(code)
