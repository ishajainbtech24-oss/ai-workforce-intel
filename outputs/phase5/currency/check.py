"""Browser check of the rupee display (Playwright, Chromium). Needs the app on http://localhost:8501.

For every page, light and dark, at 1440 px and 390 px: no "$", "USD" or "dollar" on screen (except the rate note,
which says what the rupees were converted from), no money in K/M, no sideways scrolling, and no money figure cut
off. On the Overview it records the KPI count-up while it runs and its final value. It checks that the 3D labels
use rupees, uses "Try your own numbers" (change, Update results, Reset to example), and compares on-screen numbers
with the Phase 4 tables x the rate. Writes check.json next to this file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))
from test_phase5_dashboard import _inr  # noqa: E402  (independent Indian formatter)

from dashboard import currency as CUR  # noqa: E402

BASE = "http://localhost:8501"
OUT = Path(__file__).with_name("check.json")
TABLES = ROOT / "outputs" / "phase4" / "tables"
PAGES = {"overview": "", "costs": "costs", "timing": "timing", "levers": "levers", "your_company": "your_company"}
RATE = CUR.INR_PER_USD
DOLLAR_RE = re.compile(r"\$|\bUSD\b|dollar", re.IGNORECASE)
KM_RE = re.compile(r"₹\s?[0-9.,]+\s?[KM]\b")
NOTE_RE = re.compile(r"Amounts are shown in Indian rupees, converted at the rate of .{1,40}? per US dollar")
TEXT_JS = """() => { const t = [document.body ? document.body.innerText : ''];
  document.querySelectorAll('svg text').forEach(e => t.push(e.textContent));
  document.querySelectorAll('[title],[aria-label],[alt]').forEach(e => t.push(e.getAttribute('title') || '',
     e.getAttribute('aria-label') || '', e.getAttribute('alt') || ''));
  return t.join(' \\n '); }"""
CLIP_JS = """() => [...document.querySelectorAll('.kpi-value, .depth-value, .aiwi-table td, .am, .fval, .flow span, span')]
  .filter(e => e.textContent.includes('\\u20b9') && e.children.length === 0 && e.offsetParent !== null)
  .filter(e => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible')
  .map(e => e.textContent)"""


def nav(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=120000)


def settle(page, ms=2500):
    page.wait_for_selector('[data-testid="stMain"]', timeout=60000)
    try:
        page.wait_for_function("() => !document.querySelector('[data-testid=\"stSkeleton\"]')", timeout=60000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(ms)


def all_text(page) -> str:
    out = []
    for f in page.frames:
        try:
            out.append(f.evaluate(TEXT_JS))
        except Exception:  # noqa: BLE001
            pass
    return " ".join(out)


def clipped(page) -> list[str]:
    out = []
    for f in page.frames:
        try:
            out += f.evaluate(CLIP_JS)
        except Exception:  # noqa: BLE001
            pass
    return out


def expected_numbers() -> list[tuple[str, str, float, str]]:
    """(page, what, Phase 4 USD value, expected rupee text)."""
    tot = pd.read_csv(TABLES / "totals_summary.csv").query("multiplier == 1.0").set_index("scenario")
    sens = pd.read_csv(TABLES / "sensitivity.csv").sort_values("swing_cum_net_T", ascending=False)
    e = tot.loc["expected"]
    rows = [("overview", "Total cost over the year (expected)", e.total_cost_p50),
            ("overview", "Estimated benefit (expected)", e.total_value_p50),
            ("overview", "Running balance at year end (expected)", e.cum_net_T_p50),
            ("overview", "Year-end balance, cautious (3D / bars)", tot.loc["downside"].cum_net_T_p50),
            ("overview", "Year-end balance, optimistic (3D / bars)", tot.loc["optimistic"].cum_net_T_p50),
            ("overview", "Top choice swing / 2 (finding)", sens.swing_cum_net_T.iloc[0] / 2),
            ("timing", "Expected: most money tied up", e.peak_investment_p50),
            ("timing", "Optimistic: most money tied up", tot.loc["optimistic"].peak_investment_p50),
            ("timing", "Expected: likely year-end balance, low end", e.cum_net_T_p10),
            ("timing", "Optimistic: likely year-end balance, high end", tot.loc["optimistic"].cum_net_T_p90),
            ("levers", "Year-end balance in the box (expected)", e.cum_net_T_p50),
            ("levers", "Largest swing (depth bar)", sens.swing_cum_net_T.iloc[0]),
            ("levers", "Second swing (depth bar)", sens.swing_cum_net_T.iloc[1])]
    return [(p, w, float(v), _inr(float(v) * RATE)) for p, w, v in rows]


def main() -> int:
    res = {"rate": RATE, "pages": [], "numbers": [], "countup": {}, "company": {}, "errors": []}
    texts = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
        for theme in ("light", "dark"):
            for w in (1440, 390):
                ctx = b.new_context(viewport={"width": w, "height": 1000}, color_scheme=theme)
                page = ctx.new_page()
                page.on("pageerror", lambda e: res["errors"].append(f"pageerror: {e}"))
                for name, path in PAGES.items():
                    nav(page, f"{BASE}/{path}?theme={theme}")
                    if name == "overview" and theme == "light" and w == 1440:
                        page.wait_for_selector(".kpi-value[data-count]", timeout=60000)
                        seen = []
                        for _ in range(80):
                            seen.append(page.eval_on_selector(".kpi-value[data-count]", "e => e.textContent"))
                            page.wait_for_timeout(50)
                        settle(page, 1500)
                        final = page.eval_on_selector_all(".kpi-value[data-count]", "es => es.map(e => e.textContent)")
                        res["countup"] = {"frames": list(dict.fromkeys(seen)), "final": final}
                    settle(page)
                    text = all_text(page)
                    texts[(name, theme, w)] = text
                    scan = NOTE_RE.sub(" ", text)
                    over = page.evaluate("() => { const m = document.querySelector('[data-testid=\"stMain\"]');"
                                         " return Math.max(document.documentElement.scrollWidth, m ? m.scrollWidth : 0) - window.innerWidth; }")
                    res["pages"].append({"page": name, "theme": theme, "width": w,
                                         "dollar_hits": [scan[max(0, m.start() - 40): m.end() + 40] for m in DOLLAR_RE.finditer(scan)],
                                         "km_hits": KM_RE.findall(scan), "rupee_amounts": len(re.findall("₹", text)),
                                         "rate_note_shown": bool(NOTE_RE.search(text)), "sideways_px": over,
                                         "clipped": clipped(page)})
                ctx.close()

        # 3D labels (overview columns and costs donut) use rupees
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        nav(page, f"{BASE}/")
        settle(page, 4000)
        flow = [f.evaluate("() => document.body.innerText") for f in page.frames if f != page.main_frame]
        nav(page, f"{BASE}/costs")
        settle(page, 4000)
        donut = [f.evaluate("() => document.body.innerText") for f in page.frames if f != page.main_frame]
        res["three_d"] = {"overview_frames_with_rupees": [t[:200] for t in flow if "₹" in t],
                          "costs_frames_with_rupees": [t[:300] for t in donut if "₹" in t]}

        # Try your own numbers
        nav(page, f"{BASE}/your_company")
        page.wait_for_selector('[data-testid="stNumberInput"] input', timeout=120000)
        page.wait_for_selector(".kpi-value", timeout=120000)
        settle(page, 3000)
        def box(label):
            return page.locator(f'input[aria-label="{label}"]').first
        try:
          labels = page.eval_on_selector_all("input[aria-label]", "es => es.map(e => e.getAttribute('aria-label'))")
          res["company"]["input_labels"] = labels
          before = page.eval_on_selector_all(".kpi-value", "es => es.map(e => e.textContent)")
          staff = box("Hourly pay for staff (₹ per hour)")
          res["company"]["defaults"] = {lab: box(lab).input_value() for lab in (
              "Hourly pay for staff (₹ per hour)", "Hourly pay for engineers (₹ per hour)",
              "Monthly training and support budget (₹ per month)", "AI usage price (₹ per million units)",
              "Technology running cost (₹ per month)")}
          staff.fill("8470")  # about 2x the example (45 x rate = 4,235)
          page.get_by_role("button", name="Update results").click()
          settle(page, 4000)
          after = page.eval_on_selector_all(".kpi-value", "es => es.map(e => e.textContent)")
          page.get_by_role("button", name="Reset to example").click()
          settle(page, 4000)
          reset = page.eval_on_selector_all(".kpi-value", "es => es.map(e => e.textContent)")
          res["company"].update({"cards_example": before, "cards_staff_pay_8470": after, "cards_after_reset": reset,
                                 "staff_after_reset": box("Hourly pay for staff (₹ per hour)").input_value()})
        except Exception as exc:  # noqa: BLE001
          res["company"]["error"] = str(exc)[:300]
        ctx.close()
        b.close()

    for page_name, what, usd, want in expected_numbers():
        shown = any(want in t for (n, th, w), t in texts.items() if n == page_name)
        res["numbers"].append({"page": page_name, "what": what, "phase4_usd": round(usd, 2),
                               "x_rate_inr": round(usd * RATE, 2), "expected_on_screen": want, "found": shown})
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    bad = [r for r in res["pages"] if r["dollar_hits"] or r["km_hits"] or r["sideways_px"] > 1 or r["clipped"]]
    print(json.dumps({"bad_pages": bad, "numbers_found": sum(n["found"] for n in res["numbers"]),
                      "numbers": len(res["numbers"]), "countup": res["countup"], "company": res["company"],
                      "three_d": res["three_d"], "errors": res["errors"][:5]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
