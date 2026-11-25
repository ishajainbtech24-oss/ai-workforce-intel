"""Reusable pieces: CSS and theme, top bar with the Dark mode / Reduce motion switches, banner, KPI and insight
cards, tables, depth bars and the page-level motion script. The Three.js scenes live in `components_3d.py`.

KPI cards are plain HTML in the page (readable without JavaScript); `motion_script()` installs one small script in
the parent page that adds the count-up, the cursor light and tilt, and the gliding navigation pill. It does nothing
when the visitor prefers reduced motion or switched "Reduce motion" on.
"""
from __future__ import annotations

import functools
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from dashboard.ui import components_3d as K3
from dashboard.ui import copy as C
from dashboard.core import currency as CUR
from dashboard.ui import theme as T

CSS_PATH = Path(__file__).with_name("styles.css")
THREE_URL = K3.THREE_URL

ICONS = {  # 20 px line icons (stroke = currentColor)
    "cost": '<path d="M3 7h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 7l11-3v3M15 12.5h.01"/>',
    "benefit": '<path d="M3 16l5-5 3 3 6-7M13 7h4v4"/>',
    "balance": '<path d="M10 3v14M4 17h12M5 7l-2 5h4zM15 7l-2 5h4zM5 7h10"/>',
    "payback": '<path d="M5 18V3M5 4h10l-2 3.5L15 11H5"/>',
    "info": '<circle cx="10" cy="10" r="7.5"/><path d="M10 9v5M10 6.5h.01"/>',
    "see": '<path d="M2 10s3-5.5 8-5.5S18 10 18 10s-3 5.5-8 5.5S2 10 2 10z"/><circle cx="10" cy="10" r="2.4"/>',
    "means": '<path d="M7.5 15h5M8 17.5h4M10 2.5a5.2 5.2 0 0 0-3 9.5c.6.5 1 1.2 1 2V15h4v-1c0-.8.4-1.5 1-2a5.2 5.2 0 0 0-3-9.5z"/>',
    "why": '<path d="M5 18V3M5 4h10l-2 3.5L15 11H5"/>',
}


def icon(name: str, size: int = 18) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


# ---------------------------------------------------------------- theme, motion switches, CSS
def motion_on() -> bool:
    """True when 3D and decorative motion may run (ENABLE_3D on and 'Reduce motion' off)."""
    try:
        reduce = bool(st.session_state.get(T.MOTION_KEY, False))
    except Exception:  # noqa: BLE001 - no session
        reduce = False
    return T.ENABLE_3D and not reduce


def _reduce_block(css: str) -> str:
    """The body of the prefers-reduced-motion block in styles.css, applied unconditionally."""
    start, end = css.find("/*REDUCE*/"), css.find("/*END REDUCE*/")
    block = css[start:end]
    return block[block.find("{") + 1: block.rfind("}")]


@functools.lru_cache(maxsize=1)
def _css_text() -> str:
    """styles.css, read once per server (it only changes with a deploy, which restarts the server)."""
    return CSS_PATH.read_text(encoding="utf-8")


def inject_css() -> None:
    css = _css_text()
    extra = "" if motion_on() else _reduce_block(css)
    names = f"--pages-label:{json.dumps(C.PAGES_MENU)};--product-name:{json.dumps(C.PRODUCT)}"
    st.markdown(f"<style>{T.css_vars(T.mode())}:root{{{names}}}{css}{extra}</style>"
                + ('' if motion_on() else '<i class="aiwi-still" hidden></i>'), unsafe_allow_html=True)


def init_theme() -> None:
    """First visit: ?theme=dark|light from the address if given, else the visitor's own browser/Streamlit setting
    (st.context.theme), else light. Kept for the session; the Dark mode switch changes it."""
    if T.THEME_KEY not in st.session_state:
        asked = st.query_params.get("theme")
        if asked in ("dark", "light"):
            st.session_state[T.THEME_KEY] = asked == "dark"
        else:
            try:
                st.session_state[T.THEME_KEY] = getattr(st.context.theme, "type", None) == "dark"
            except Exception:  # noqa: BLE001 - older Streamlit or no browser context
                st.session_state[T.THEME_KEY] = False
    if T.MOTION_KEY not in st.session_state:
        st.session_state[T.MOTION_KEY] = st.query_params.get("motion") == "off"


def sidebar_controls() -> None:
    """Bottom of the side navigation: product name, the Word guide, the two switches and the rupee-rate note."""
    with st.container(key="aiwi_sidecontrols"):
        with st.popover(C.GLOSSARY_BUTTON, icon=":material/menu_book:", width="stretch"):
            glossary()
        st.toggle(C.DARK_MODE, key=T.THEME_KEY, help=C.DARK_HELP)
        st.toggle(C.REDUCE_MOTION, key=T.MOTION_KEY, help=C.MOTION_HELP)
        from dashboard.ui import analyst
        analyst.toggle()
        st.markdown(f'<div class="aiwi-rate-note">{html.escape(rate_note())}</div>', unsafe_allow_html=True)
        yours_note()


def yours_note() -> None:
    """While the visitor's own figures are showing: a note in the side panel and a way back to the example."""
    from dashboard.core import data as D
    if D.yours() is None:
        return
    st.markdown(f'<div class="aiwi-yours-note">{icon("info", 16)}<span>{html.escape(C.SIDE_YOURS)}</span></div>',
                unsafe_allow_html=True)
    st.button(C.SIDE_YOURS_BACK, key="yours_back", icon=":material/undo:", on_click=D.clear_yours,
              help=C.SIDE_YOURS_HELP, width="stretch")


def header_strip() -> None:
    """Top of the main column: the 'Example company' pill and the banner, on every page."""
    st.markdown(f'<div class="aiwi-strip"><span class="aiwi-name">{html.escape(C.PRODUCT)}</span>'
                f'<span class="aiwi-pill">{html.escape(_words("EXAMPLE_PILL"))}</span></div>'
                f'<div class="aiwi-banner" role="note">{icon("info", 16)}<span>{html.escape(_words("BANNER"))}</span></div>',
                unsafe_allow_html=True)


PAGE_TINTS = {"welcome": "tint-sand", "overview": "tint-sand", "data": "tint-sky", "forecast": "tint-sky",
              "reliable": "tint-sky", "method": "tint-sky", "costs": "tint-blush", "timing": "tint-blush", "levers": "tint-blush",
              "company": "tint-sage"}


def page_tint(key: str) -> None:
    """A gentle colour personality per page group: the tint of the band behind the page title."""
    st.markdown(f'<i class="aiwi-tint {PAGE_TINTS.get(key, "tint-sand")}" hidden></i>', unsafe_allow_html=True)


def rate_note() -> str:
    """'Amounts are shown in Indian rupees, converted at the rate of ₹X per US dollar (source, date).'"""
    return C.RATE_NOTE.format(rate=CUR.rate_text(), source=CUR.RATE_SOURCE, date=CUR.date_text())


def _words(name: str) -> str:
    from dashboard.core import logic
    return logic.words(name)


def footer() -> None:
    st.markdown(f'<div class="aiwi-footer"><b>{html.escape(C.PRODUCT)}</b><span>{html.escape(_words("FOOTER_NOTE"))}</span>'
                f'<span>{html.escape(C.FOOTER.split(". ", 1)[1])}</span></div>', unsafe_allow_html=True)


def missing() -> None:
    st.info(C.MISSING, icon=":material/hourglass_empty:")


def how_to_read(page: str) -> None:
    with st.expander("How to read this", icon=":material/help:"):
        st.write(C.HOW_TO_READ[page])


def about() -> None:
    with st.expander(C.ABOUT_TITLE, icon=":material/info:"):
        st.write(_words("ABOUT"))
        st.caption(rate_note())
        for term, meaning in C.GLOSSARY.items():
            st.markdown(f"**{term}**: {meaning}")


def glossary() -> None:
    """Every everyday word the pages use with a special meaning, in one list (top bar button on every page)."""
    terms = {**C.GLOSSARY, **C.GLOSSARY_MORE}
    st.markdown('<dl class="glossary">' + "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>"
                                                  for t, d in terms.items()) + "</dl>", unsafe_allow_html=True)


GUIDE_ICONS = ("see", "means", "why")


def chart_guide(lines: tuple[str, str, str], stacked: bool = False) -> None:
    """The short guide under a chart: What you see / What it means / Why it matters."""
    rows = "".join(f'<div class="guide-row"><span class="guide-ic">{icon(ic, 16)}</span>'
                   f'<div><b>{html.escape(label)}</b><span>{html.escape(text)}</span></div></div>'
                   for ic, label, text in zip(GUIDE_ICONS, C.GUIDE_LABELS, lines))
    st.markdown(f'<div class="chart-guide{" stacked" if stacked else ""}" role="note">{rows}</div>', unsafe_allow_html=True)


def tech_details(rows: list[tuple[str, str]], extra: pd.DataFrame | None = None) -> None:
    """The closed 'Explore technical details' panel: each technical term with its plain explanation."""
    with st.expander(C.TECH_TITLE, icon=":material/science:"):
        st.markdown('<dl class="glossary tech">' + "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>"
                                                          for t, d in rows) + "</dl>", unsafe_allow_html=True)
        if extra is not None and len(extra):
            table(extra)


def page_title(text: str, sub: str | None = None, eyebrow: str | None = None) -> None:
    """The tinted header band of a page: the page name as a small label, a headline that makes the point, one line."""
    head = f'<div class="aiwi-eyebrow">{html.escape(eyebrow)}</div>' if eyebrow else ""
    tail = f'<p class="aiwi-sub">{html.escape(sub)}</p>' if sub else ""
    st.markdown(f'<header class="aiwi-pagehead">{head}<h1 class="aiwi-h1">{html.escape(text)}</h1>{tail}</header>',
                unsafe_allow_html=True)


def eyebrow(text: str) -> None:
    st.markdown(f'<div class="aiwi-eyebrow">{html.escape(text)}</div>', unsafe_allow_html=True)


def embed(markup: str, height: int) -> None:
    """Embed an HTML document: st.iframe on current Streamlit, components.html on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(markup, height=max(height, 1))
    else:
        components.html(markup, height=height)


# ---------------------------------------------------------------- navigation helpers (Phase 5D)
PAGE_FILES = {"welcome": "app_pages/welcome.py", "overview": "app_pages/overview.py", "data": "app_pages/data_used.py", "forecast": "app_pages/forecast.py",
              "reliable": "app_pages/reliability.py", "method": "app_pages/methodology.py",
              "costs": "app_pages/costs.py",
              "timing": "app_pages/timing.py", "levers": "app_pages/levers.py", "company": "app_pages/your_company.py"}


def next_card(key: str) -> None:
    """'Next: <page>' card at the foot of a page, with one line on what that page answers (nothing on the last)."""
    if key not in C.NEXT:
        return
    target, line = C.NEXT[key]
    title, ic = C.PAGES[target]
    with st.container(key=f"aiwi_next_{key}"):
        st.markdown(f'<div class="aiwi-next-label">{html.escape(C.NEXT_LABEL)}</div>', unsafe_allow_html=True)
        st.page_link(PAGE_FILES[target], label=f"{title} →", icon=ic)
        st.markdown(f'<div class="aiwi-next-line">{html.escape(line)}</div>', unsafe_allow_html=True)


def section_marker(section: str) -> None:
    """Invisible note of the current page's menu group, so the motion script can mark that group as active."""
    st.markdown(f'<i class="aiwi-cursec" data-sec="{html.escape(section)}" hidden></i>', unsafe_allow_html=True)


# ---------------------------------------------------------------- hero and 3D pieces (thin wrappers)
def hero_html(use_3d: bool = True) -> str:
    return K3.hero_html(use_3d, T.scene_palette(), sub=_words("HERO_SUB"))


def hero(use_3d: bool | None = None) -> None:
    embed(hero_html(motion_on() if use_3d is None else use_3d), 284)


def money_flow(items: list[dict]) -> None:
    embed(K3.money_flow_html(items, motion_on(), T.scene_palette()), 380)


def donut_3d(slices: list[dict]) -> None:
    embed(K3.donut_html(slices, motion_on(), T.scene_palette()), 400)


# ---------------------------------------------------------------- cards
def sparkline_svg(values, color: str = T.ACCENT, zero: bool = False) -> str:
    """Tiny inline SVG line of real monthly values that draws itself; optional dotted zero line."""
    v = [float(x) for x in values]
    lo, hi = min(v + ([0.0] if zero else [])), max(v + ([0.0] if zero else []))
    span = (hi - lo) or 1.0
    y = lambda x: 30 - (x - lo) / span * 26  # noqa: E731
    pts = [(i * 100 / max(len(v) - 1, 1), y(x)) for i, x in enumerate(v)]
    line = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    area = f"0,32 {line} 100,32"
    zl = f'<line class="zero" x1="0" x2="100" y1="{y(0):.1f}" y2="{y(0):.1f}" vector-effect="non-scaling-stroke"/>' if zero else ""
    gid = f"g{abs(hash((tuple(v), color))) % 10**8}"
    return (f'<svg class="spark" viewBox="0 -2 100 36" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{color}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon class="area" points="{area}" fill="url(#{gid})"/>{zl}'
            f'<polyline class="line" points="{line}" stroke="{color}" vector-effect="non-scaling-stroke"/></svg>')


def kpi_card(label: str, value: str, meaning: str, spark: str = "", count: float | None = None, tone: str = "",
             icon_name: str = "", chip: tuple[str, str] | None = None, i: int = 0,
             delta: tuple[str, str] | None = None) -> str:
    """One KPI card; `count` (the raw amount in rupees) enables the count-up, the final text is already in place.
    `delta` = (text, 'up' | 'down' | 'flat') shows a change next to the value, in words as well as colour."""
    data = f' data-count="{count}"' if count is not None else ""
    kind = "" if value.lstrip("-").startswith(CUR.SYM) else " text"  # words such as 'Not within 12 months'
    ic = f'<span class="kpi-icon">{icon(icon_name)}</span>' if icon_name else ""
    ch = f'<span class="chip {chip[0]}">{html.escape(chip[1])}</span>' if chip else ""
    return (f'<div class="kpi-card {tone}{kind}" tabindex="0" style="--i:{i}">'
            f'<div class="kpi-head">{ic}{ch}</div><div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value"{data}>{html.escape(value)}</div>'
            + (f'<div class="kpi-delta {html.escape(delta[1])}">{html.escape(delta[0])}</div>' if delta else "")
            + f'<div class="kpi-meaning">{html.escape(meaning)}</div>{spark}</div>')


def kpi_row(cards: list[str], lead: bool = False) -> None:
    """A row of KPI cards; lead=True makes the first one a large lead card with a bold figure."""
    st.markdown(f'<div class="kpi-grid{" lead" if lead else ""}">{"".join(cards)}</div>', unsafe_allow_html=True)


def insight_cards(items: list[tuple[str, str]], kind: str = "") -> None:
    body = "".join(f'<div class="insight {kind}" style="--i:{n}"><div class="insight-icon">{html.escape(ic)}</div>'
                   f'<div class="insight-text">{html.escape(text)}</div></div>' for n, (ic, text) in enumerate(items))
    st.markdown(f'<div class="insight-grid">{body}</div>', unsafe_allow_html=True)


def table(df: pd.DataFrame, dots: list[str] | None = None) -> None:
    """A small, theme-aware HTML table (first column can carry a colour dot)."""
    head = "".join(f"<th scope='col'>{html.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for n, r in enumerate(df.itertuples(index=False)):
        cells = [html.escape(str(x)) for x in r]
        if dots:
            cells[0] = f'<span class="dot" style="background:{dots[n]}"></span>{cells[0]}'
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    st.markdown(f'<div class="aiwi-table-wrap"><table class="aiwi-table"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table></div>', unsafe_allow_html=True)


def depth_bars_html(items: list[dict], color: str) -> str:
    """Ranked bars with a CSS 3D extrusion and hover lift (no WebGL needed). Values are the real ones."""
    top = max((it["value"] for it in items), default=1.0) or 1.0
    rows = "".join(f'<div class="depth-row" style="--i:{n}"><div class="depth-label">{html.escape(it["label"])}</div>'
                   f'<div class="depth-track"><div class="depth-bar" style="--w:{max(it["value"] / top * 100, 1.5):.1f}%;--c:{color}">'
                   f'</div></div><div class="depth-value">{html.escape(it["text"])}</div></div>' for n, it in enumerate(items))
    return (f'<div class="depth-card" role="figure" aria-label="{html.escape(C.DEPTH_TITLE)}">'
            f'<div class="depth-title">{html.escape(C.DEPTH_TITLE)}</div><div class="depth-note">{html.escape(C.DEPTH_NOTE)}</div>'
            f'{rows}</div>')


def depth_bars(items: list[dict]) -> None:
    st.markdown(depth_bars_html(items, T.tok("accent")), unsafe_allow_html=True)


# ---------------------------------------------------------------- motion in the parent page
_MOTION_JS = r"""
(function () {
  const W = window.parent, D = W.document;
  if (W.__aiwiFx) { W.__aiwiFx(); return; }
  const still = () => W.matchMedia('(prefers-reduced-motion: reduce)').matches || !!D.querySelector('.aiwi-still');
  function markActive() {  // side navigation: the current page carries aria-current="page" and a solid marker
    const nav = D.querySelector('[data-testid="stSidebarNav"]'); if (!nav) return;
    const here = W.location.pathname.replace(/\/+$/, '') || '/';
    nav.querySelectorAll('a[href]').forEach(a => {
      const p = new URL(a.href).pathname.replace(/\/+$/, '') || '/';
      const on = p === here; a.classList.toggle('is-active', on);
      if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
  }
  // the same Indian style as dashboard/currency.py: ₹950, ₹12,345, ₹23.1 L, ₹1.2 Cr, -₹23.1 L, ₹0
  function group(n) { const s = String(n); if (s.length <= 3) return s;
    let head = s.slice(0, -3); const parts = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    if (head) parts.unshift(head); return parts.concat([s.slice(-3)]).join(','); }
  function inr(x) { const a = Math.abs(x); let body;
    if (Math.round(a) < 1e5) body = '₹' + group(Math.round(a));
    else if (Math.round(a / 1e4) / 10 < 100) body = '₹' + (a / 1e5).toFixed(1) + ' L';
    else { let c = (a / 1e7).toFixed(2); if (c.endsWith('0')) c = c.slice(0, -1); body = '₹' + c + ' Cr'; }
    return (x < 0 && body !== '₹0' ? '-' : '') + body; }
  function countUps() {
    D.querySelectorAll('.kpi-value[data-count]:not([data-done])').forEach(el => {
      el.dataset.done = '1'; if (still()) return;
      const text = el.textContent, target = parseFloat(el.dataset.count);
      if (!text.includes('₹') || !isFinite(target)) return;
      const t0 = performance.now();
      const step = t => { const p = Math.min((t - t0) / 900, 1), e = 1 - Math.pow(1 - p, 3);
        el.textContent = inr(target * e); if (p < 1) W.requestAnimationFrame(step); else el.textContent = text; };
      W.requestAnimationFrame(step);
    });
  }
  function drawLines() {  // measure solid lines in relative units so the draw-on shows the whole line
    D.querySelectorAll('.js-plotly-plot .scatterlayer .js-line:not([data-draw])').forEach(l => {
      l.dataset.draw = '1';
      const dash = (l.style.strokeDasharray || '').trim();
      if (still() || (dash && dash !== 'none' && !/^0(px)?(,\s*0(px)?)?$/.test(dash))) return;
      l.setAttribute('pathLength', '1'); l.classList.add('aiwi-draw');
    });
  }
  function iconsReady() {  // icons are glyphs of an icon font: show them only once it has loaded (see styles.css)
    const font = '20px "Material Symbols Rounded"', mark = () => D.documentElement.classList.add('aiwi-icons');
    try {
      if (D.fonts.check(font)) { mark(); return; }
      D.fonts.load(font).then(f => { if (f.length) mark(); }).catch(() => {});
      D.fonts.addEventListener('loadingdone', () => { if (D.fonts.check(font)) mark(); });
    } catch (e) { mark(); }
  }
  iconsReady();
  let queued = false;
  const run = () => { queued = false; try { markActive(); countUps(); drawLines(); } catch (e) {} };
  const kick = () => { if (!queued) { queued = true; W.requestAnimationFrame(run); } };
  W.__aiwiFx = kick;
  new W.MutationObserver(kick).observe(D.body, {childList: true, subtree: true});
  W.addEventListener('resize', kick); W.addEventListener('popstate', () => setTimeout(kick, 60));
  kick();
})();
"""


def motion_script() -> None:
    """Install the page-level motion script once, in the parent page's own context (survives page changes)."""
    code = json.dumps(_MOTION_JS)
    with st.container(key="aiwi_fx"):
        embed(f"""<script>
(function(){{try{{const D = window.parent.document;
 if (!D.getElementById('aiwi-fx')) {{ const s = D.createElement('script'); s.id = 'aiwi-fx'; s.textContent = {code};
   D.head.appendChild(s); }} else if (window.parent.__aiwiFx) window.parent.__aiwiFx();
}}catch(e){{}}}})();
</script>""", 1)


# ---------------------------------------------------------------- selectors and tags
def pickers(key: str, outlooks: list[str], cautions: list[float]) -> tuple[str, float]:
    """Outlook and 'how cautious' selectors; returns the engine names (scenario, caution level)."""
    c1, c2 = st.columns([3, 2])
    with c1:
        o_label = st.segmented_control(C.OUTLOOK_PICK, [C.OUTLOOK_SHORT[s] for s in outlooks],
                                       default=C.OUTLOOK_SHORT["expected"], key=f"{key}_outlook", help=C.HINT["outlook"])
    with c2:
        k_label = st.segmented_control(C.CAUTION_PICK, [C.CAUTION[k] for k in cautions], default=C.CAUTION[1.0],
                                       key=f"{key}_caution", help=C.CAUTION_HELP)
    scenario = next((s for s in outlooks if C.OUTLOOK_SHORT[s] == o_label), "expected")
    k = next((k for k in cautions if C.CAUTION[k] == k_label), 1.0)
    return scenario, k


def tags(lines: list[str]) -> None:
    st.markdown("".join(f'<span class="tag"><i style="background:{T.line_color(ln)}"></i><b>{html.escape(C.LINE[ln])}</b>'
                        f'<span>{html.escape(C.LINE_TAG[ln])}</span></span>' for ln in lines), unsafe_allow_html=True)



# ---------------------------------------------------------------- MVP design system: the one set of page parts
# Every page builds its layout from these; no page writes its own HTML.
def page_header(text: str, sub: str | None = None, eyebrow: str | None = None) -> None:
    """Page title band: small page name, a headline that makes the point, one line of context."""
    page_title(text, sub, eyebrow)


def insight_row(see: str, mean: str, why: str, stacked: bool = False) -> None:
    """The 'What you see / What it means / Why it matters' row under a chart."""
    chart_guide((see, mean, why), stacked)


def next_step_card(key: str) -> None:
    next_card(key)


def section_title(text: str, sub: str | None = None, anchor: str | None = None) -> None:
    ida = f' id="{html.escape(anchor)}"' if anchor else ""
    tail = f'<p class="aiwi-sub">{html.escape(sub)}</p>' if sub else ""
    st.markdown(f'<h2 class="aiwi-h2"{ida}>{html.escape(text)}</h2>{tail}', unsafe_allow_html=True)


def chart_title(text: str) -> None:
    st.markdown(f'<div class="aiwi-chart-title">{html.escape(text)}</div>', unsafe_allow_html=True)


def lede(text: str) -> None:
    """One plain line describing what a chart or series is."""
    st.markdown(f'<p class="aiwi-sub fc-desc">{html.escape(text)}</p>', unsafe_allow_html=True)


def note(text: str, tone: str = "", trusted_html: bool = False) -> None:
    """A quiet note; tone='warm' for a caution. trusted_html only for our own copy with <b>/<i>."""
    body = text if trusted_html else html.escape(text)
    cls = " warm-note" if tone == "warm" else ""
    st.markdown(f'<div class="note{cls}" role="note">{body}</div>', unsafe_allow_html=True)


def verdict(text: str, sub: str | list[str] | None = None, tone: str = "", small: str | None = None,
            trusted_html: bool = False) -> None:
    """A verdict box: the sentence a reader should leave with (tone: 'warm' warning, 'card' forecast card, 'rel')."""
    body = text if trusted_html else html.escape(text)
    cls = {"warm": " warm-box", "card": " fc-card", "rel": " rel-verdict"}.get(tone, "")
    inner = f'<span class="fc-headline">{body}</span>' if tone == "card" else body
    subs = [sub] if isinstance(sub, str) else list(sub or [])
    extra = "".join(f'<span class="sub">{html.escape(x)}</span>' for x in subs) + \
            (f'<span class="fc-small">{html.escape(small)}</span>' if small else "")
    st.markdown(f'<div class="verdict{cls}">{inner}{extra}</div>', unsafe_allow_html=True)


def numbered_card(title: str, sub: str, items: list[tuple[str, str, str]]) -> None:
    """A titled card with a numbered list; each item is (bold label, line, small helper line)."""
    lis = "".join(f'<li><b>{html.escape(a)}</b><span>{html.escape(b)}</span><span class="helps">{html.escape(c)}</span></li>'
                  for a, b, c in items)
    st.markdown(f'<div class="decide-card glass"><div class="decide-title">{html.escape(title)}</div>'
                f'<div class="decide-sub">{html.escape(sub)}</div><ol>{lis}</ol></div>', unsafe_allow_html=True)


def card_grid(cards_html: list[str], kind: str = "kpi-grid") -> None:
    """A grid of cards already built by kpi_card / insight helpers (kind: kpi-grid or insight-grid stack)."""
    st.markdown(f'<div class="{html.escape(kind)}">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def assumption_chip(label: str, value: str, kind: str = "estimate") -> str:
    """A small chip naming an assumption and where it comes from (kind: trend / estimate / input / study)."""
    title = html.escape(C.ASSUMPTION_KIND.get(kind, ""))
    return (f'<span class="chip assumption {html.escape(kind)}" title="{title}">'
            f'<b>{html.escape(label)}</b> {html.escape(value)}</span>')


def assumption_chips(chips: list[str]) -> None:
    st.markdown(f'<div class="chip-row">{"".join(chips)}</div>', unsafe_allow_html=True)


def source_note(text: str, url: str | None = None) -> None:
    link = ""
    if url:
        host = url.split("//")[-1].split("/")[0]
        link = f' <a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(host)}</a>'
    st.markdown(f'<p class="aiwi-source">{html.escape(C.SOURCE_PREFIX)}: {html.escape(text)}{link}</p>',
                unsafe_allow_html=True)


def empty_state(body: str | None = None, title: str | None = None, icon_name: str = ":material/hourglass_empty:") -> None:
    """Shown instead of a chart or section when its data is missing: says what is missing, never a raw error."""
    st.info(f"**{title or C.EMPTY_TITLE}**  \n{body or C.MISSING}", icon=icon_name)


def loading_skeleton(lines: int = 3) -> None:
    bars = "".join('<div class="sk-line"></div>' for _ in range(lines))
    st.markdown(f'<div class="aiwi-skeleton" aria-busy="true" aria-label="{html.escape(C.LOADING)}">{bars}</div>',
                unsafe_allow_html=True)


def _chart_config(filename: str) -> dict:
    return {"displayModeBar": "hover", "displaylogo": False, "responsive": True, "modeBarButtons": [["toImage"]],
            "toImageButtonOptions": {"format": "png", "scale": 2, "filename": filename}}


def figure_table(fig) -> pd.DataFrame:
    """The numbers behind a chart, one row per point, money in rupees (charts keep dollars and label in rupees)."""
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    money = set(meta.get("money", []))
    xt = fig.layout.xaxis.title.text if fig.layout.xaxis and fig.layout.xaxis.title.text else C.TABLE_X
    yt = fig.layout.yaxis.title.text if fig.layout.yaxis and fig.layout.yaxis.title.text else C.TABLE_Y
    frames = []
    for tr in fig.data:
        if tr.type == "pie":
            vals = np.asarray(tr.values, float)
            frames.append(pd.DataFrame({C.TABLE_SERIES: list(tr.labels),
                                        C.TABLE_Y: np.round(CUR.to_inr(vals), 0) if "values" in money else vals}))
            continue
        x, y = getattr(tr, "x", None), getattr(tr, "y", None)
        if x is None or y is None or (not tr.name and tr.showlegend is False):
            continue
        xs, ys, xcol, ycol, as_money = list(x), list(y), xt, yt, "y" in money
        if getattr(tr, "orientation", None) == "h":
            xs, ys, xcol, ycol, as_money = list(y), list(x), yt, xt, "x" in money
        yv = pd.to_numeric(pd.Series(ys), errors="coerce").to_numpy(float)
        if as_money:
            yv = np.round(CUR.to_inr(yv), 0)
        frames.append(pd.DataFrame({C.TABLE_SERIES: tr.name or "", xcol: xs, ycol: yv}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def chart(fig, key: str, filename: str | None = None, table: pd.DataFrame | None = None) -> None:
    """Every chart: the figure (PNG download on hover), then 'View as table' with a CSV download of its numbers."""
    name = filename or key
    st.plotly_chart(fig, config=_chart_config(name), width="stretch", theme=None, key=key)
    df = table if table is not None else figure_table(fig)
    if df is None or not len(df):
        return
    with st.expander(C.VIEW_TABLE, icon=":material/table_chart:"):
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button(C.DOWNLOAD_CSV, df.to_csv(index=False).encode("utf-8-sig"), file_name=f"{name}.csv",
                           mime="text/csv", key=f"{key}_csv", icon=":material/download:", on_click="ignore")



def hidden_heading(text: str) -> None:
    """The page's main heading for screen readers when the visible headline is drawn elsewhere (Welcome banner)."""
    st.markdown(f'<h1 class="welcome-title sr-only">{html.escape(text)}</h1>', unsafe_allow_html=True)


def anchor_link(text: str, anchor: str) -> None:
    st.markdown(f'<a class="aiwi-ghost" href="#{html.escape(anchor)}">{html.escape(text)}</a>', unsafe_allow_html=True)


def chart_note(text: str) -> None:
    st.markdown(f'<div class="aiwi-chart-note">{html.escape(text)}</div>', unsafe_allow_html=True)


def steps(items: list[tuple[str, str]], title: str, anchor: str) -> None:
    """Numbered steps (title + line each) under an h2 that a link can jump to."""
    st.markdown(f'<h2 class="aiwi-h2 steps-title" id="{html.escape(anchor)}">{html.escape(title)}</h2>', unsafe_allow_html=True)
    body = "".join(f'<div class="insight" style="--i:{n}"><div class="insight-icon">{n + 1}</div>'
                   f'<div class="insight-text"><b>{html.escape(t)}</b><br>{html.escape(s)}</div></div>'
                   for n, (t, s) in enumerate(items))
    card_grid([body], "insight-grid stack")



# ---------------------------------------------------------------- shared view state (scenario bar, trend picker)
def _bound(make, name: str, **kw):
    """A widget tied to the shared state: drawn from it each run, writing back on change. The widget keeps its own key
    (Streamlit forgets widget values on pages that do not draw them; the shared key survives page changes)."""
    from dashboard.core import state
    wkey = f"_w_{name}"
    st.session_state[wkey] = state.get(name)

    def _save():
        value = st.session_state.get(wkey)
        state.set(name, value if value is not None else state.DEFAULTS[name])

    return make(key=wkey, on_change=_save, **kw)


def scenario_bar(outlooks: list[str], cautions: list[float]) -> tuple[str, float]:
    """Every Money page: company preset, outlook and caution level in one bar. One source of truth in the session,
    mirrored to the address so a shared link reproduces the view. Returns (outlook, caution level)."""
    from dashboard.core import state
    from dashboard.core import data as D
    with st.container(key="aiwi_scenario"):
        c0, c1, c2 = st.columns([1.25, 1.55, 1.5], gap="small")
        with c0:
            if D.yours() is not None:
                st.markdown(f'<div class="scenario-yours"><span class="label">{html.escape(C.PRESET_PICK)}</span>'
                            f'<b>{html.escape(C.SCENARIO_YOURS)}</b></div>', unsafe_allow_html=True)
            else:
                _bound(st.selectbox, "preset", label=C.PRESET_PICK, options=list(C.PRESET_LABEL),
                       format_func=C.PRESET_LABEL.get, help=C.PRESET_HELP)
        with c1:
            _bound(st.segmented_control, "outlook", label=C.OUTLOOK_PICK, options=outlooks,
                   format_func=C.OUTLOOK_SHORT.get, help=C.HINT["outlook"])
        with c2:
            _bound(st.segmented_control, "caution", label=C.CAUTION_PICK, options=cautions,
                   format_func=C.CAUTION.get, help=C.CAUTION_HELP)
    state.sync_url(("preset", "outlook", "caution"))
    outlook = state.get("outlook") if state.get("outlook") in outlooks else "expected"
    caution = float(state.get("caution")) if float(state.get("caution")) in cautions else 1.0
    return outlook, caution


def trend_picker(available: list[str]) -> str:
    """The three Forecast pages: pick a group (Pay / Technology / AI usage), then a trend within it. Shared by the
    three pages and mirrored to the address."""
    from dashboard.core import state
    group_of = {s: g for g, members in C.TREND_GROUPS.items() for s in members}
    if state.get("trend") not in available:
        state.set("trend", available[0])
    groups = [g for g, members in C.TREND_GROUPS.items() if any(s in available for s in members)]
    gkey = "_w_trend_group"
    st.session_state[gkey] = group_of.get(state.get("trend"), groups[0])

    def _group_changed():
        g = st.session_state.get(gkey)
        if g and group_of.get(state.get("trend")) != g:
            state.set("trend", next(s for s in C.TREND_GROUPS[g] if s in available))

    with st.container(key="aiwi_trend"):
        st.segmented_control(C.PICK_GROUP, groups, key=gkey, on_change=_group_changed, help=C.HINT["series"])
        members = [s for s in C.TREND_GROUPS[group_of.get(state.get("trend"), groups[0])] if s in available]
        if len(members) > 1:
            _bound(st.pills, "trend", label=C.PICK_SERIES, options=members, format_func=lambda s: C.SERIES[s][0],
                   selection_mode="single", label_visibility="collapsed")
    state.sync_url(("trend",))
    return state.get("trend")


def remember_tour() -> None:
    """Set a small first-party cookie so the welcome tour is shown once per browser (no personal data)."""
    embed("""<script>try{window.parent.document.cookie='aiwi_tour=seen; max-age=31536000; path=/; SameSite=Lax';}
catch(e){}</script>""", 1)


def error_state(title: str, body: str) -> None:
    """What a visitor sees when a page fails to draw: plain words, no traceback."""
    st.warning(f"**{title}**  \n{body}", icon=":material/report:")


def provenance(name: str, hist: pd.DataFrame) -> None:
    """Closed panel: where one trend comes from (source, publisher, dataset, link, licence, how often, what it covers,
    what we did to it). Source names are proper nouns, so this panel, like the technical details, may name them."""
    from dashboard.ui import copy_technical as CT
    p = CT.PROVENANCE.get(name)
    if p is None:
        return
    x0, x1, n = hist["x"].iloc[0], hist["x"].iloc[-1], len(hist)
    if isinstance(x0, (pd.Timestamp,)) or hasattr(x0, "strftime"):
        covers = f"{pd.Timestamp(x0):%b %Y} to {pd.Timestamp(x1):%b %Y} ({n:,} values)"
    else:
        covers = f"{n:,} values in a row (counted from the start of the records; no calendar dates)"
    vals = (p["source"], p["publisher"], p["dataset"], p["link"], p["licence"], p["freq"], covers, p["did"])
    rows = "".join(f"<dt>{html.escape(k)}</dt><dd>" + (f'<a href="{html.escape(v)}" target="_blank" rel="noopener">'
                                                         f"{html.escape(v)}</a>" if k == "Link" else html.escape(v))
                   + "</dd>" for k, v in zip(CT.SOURCE_FIELDS, vals))
    with st.expander(f"{CT.SOURCE_TITLE}: {C.SERIES[name][0]}", icon=":material/source:"):
        st.markdown(f'<dl class="glossary tech">{rows}</dl>', unsafe_allow_html=True)
