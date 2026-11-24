"""Design tokens (colours, type, spacing, elevation) for the light and dark themes, the Plotly templates,
the 3D switch and the number formatters (money is shown in rupees; the rate lives in currency.py).

Every colour on screen comes from `TOKENS`: the CSS gets them as custom properties (`css_vars`), the charts
through the two Plotly templates, and the 3D scenes through `scene_palette`. Change a colour here only.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
import plotly.io as pio

from dashboard import currency as CUR

# One switch for every 3D scene and decorative animation (the in-app "Reduce motion" sets the same fallback).
ENABLE_3D = True

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
DISPLAY_FONT = "Fraunces, 'Source Serif 4', Georgia, 'Times New Roman', serif"
SPACE = (4, 8, 12, 16, 24, 32, 48)              # the only spacing steps used in styles.css
RADIUS = {"sm": 8, "md": 12, "lg": 16, "pill": 999}
RADIUS_PX, GAP = RADIUS["md"], SPACE[4]

# UI v3: warm and confident. Light: warm off-white page, white cards, ink-navy text. Dark: deep ink navy (not black),
# warm white text. One primary (deep blue), one warm accent (marigold), one support colour (teal), soft page tints.
# Every pair is measured in dashboard/colour_check.py and the tests.
TOKENS = {
    "light": {
        "bg": "#FBF7F0", "bg-2": "#F3ECE0", "surface": "#FFFFFF", "surface-solid": "#FFFFFF", "elevated": "#FFFFFF",
        "border": "rgba(52,40,24,0.12)", "border-strong": "rgba(52,40,24,0.24)",
        "text": "#1C2230", "muted": "#4A5163", "faint": "#5A6070", "accent": "#1F4E8C", "accent-2": "#0F766E",
        "accent-soft": "rgba(31,78,140,0.10)", "marigold": "#E8A33D", "marigold-soft": "#FBEBD0",
        "warm": "#9A4A08", "warm-soft": "rgba(232,163,61,0.20)", "warm-text": "#6B3405",
        "good": "#1F6F5C", "good-soft": "rgba(31,111,92,0.10)", "grid": "rgba(28,34,48,0.08)",
        "neutral-bar": "#D4CCBF", "hover-bg": "#FFFFFF", "shadow-rgb": "60,44,20", "on-accent": "#FFFFFF",
        "tint-sand": "#F6EBD9", "tint-sky": "#E4EDF7", "tint-blush": "#F8E7E0", "tint-sage": "#E5EEE3",
    },
    "dark": {
        "bg": "#141A24", "bg-2": "#1A2130", "surface": "#1D2431", "surface-solid": "#1D2431", "elevated": "#242C3B",
        "border": "rgba(255,246,230,0.10)", "border-strong": "rgba(255,246,230,0.22)",
        "text": "#F3EEE5", "muted": "#CBC4B7", "faint": "#ADA699", "accent": "#8DB3EC", "accent-2": "#5CC2B0",
        "accent-soft": "rgba(141,179,236,0.16)", "marigold": "#F2B45A", "marigold-soft": "rgba(242,180,90,0.16)",
        "warm": "#F2B45A", "warm-soft": "rgba(242,180,90,0.14)", "warm-text": "#F6CC8F",
        "good": "#86CF94", "good-soft": "rgba(134,207,148,0.12)", "grid": "rgba(255,246,230,0.08)",
        "neutral-bar": "#3A4354", "hover-bg": "#242C3B", "shadow-rgb": "0,0,0", "on-accent": "#141A24",
        "tint-sand": "#262420", "tint-sky": "#1C2737", "tint-blush": "#2B2226", "tint-sage": "#1E2A25",
    },
}

OUTLOOK_COLORS = {"light": {"downside": "#B4580A", "expected": "#1F4E8C", "optimistic": "#0F8F8A"},
                  "dark": {"downside": "#F2B45A", "expected": "#8DB3EC", "optimistic": "#5FD8B5"}}
# one colour per meaning on the forecast charts; checked for contrast (3:1 on cards) and for staying apart with
# red-weak, green-weak and blue-weak vision in dashboard/colour_check.py and the tests
CHART_COLORS = {"light": {"history": "#1C2230", "forecast": "#1F4E8C", "predicted": "#7B3F98"},
                "dark": {"history": "#F3EEE5", "forecast": "#8DB3EC", "predicted": "#B9A3F2"}}
LINE_COLORS = {"light": {"token_expenditure": "#B4580A", "hosting": "#0F766E", "enablement": "#1F4E8C",
                         "integration": "#B8452B"},
               "dark": {"token_expenditure": "#F2B45A", "hosting": "#5CC2B0", "enablement": "#8DB3EC",
                        "integration": "#EE8A6E"}}

# Light values stay importable under their Phase 5 names.
INK, INK_SOFT, PAPER = TOKENS["light"]["text"], TOKENS["light"]["muted"], TOKENS["light"]["bg"]
CARD, BORDER, GRID = TOKENS["light"]["surface"], TOKENS["light"]["border"], TOKENS["light"]["grid"]
ACCENT, ACCENT_2, WARM = TOKENS["light"]["accent"], TOKENS["light"]["accent-2"], TOKENS["light"]["marigold"]
OUTLOOK_COLOR, LINE_COLOR = OUTLOOK_COLORS["light"], LINE_COLORS["light"]

THEME_KEY, MOTION_KEY = "aiwi_dark", "aiwi_reduce_motion"


def mode() -> str:
    """'dark' or 'light' for the current session (light outside a running app)."""
    try:
        import streamlit as st
        return "dark" if st.session_state.get(THEME_KEY, False) else "light"
    except Exception:  # noqa: BLE001 - no session (tests, notebooks)
        return "light"


def tok(name: str, m: str | None = None) -> str:
    return TOKENS[m or mode()][name]


def outlook_color(scenario: str, m: str | None = None) -> str:
    return OUTLOOK_COLORS[m or mode()][scenario]


# Fill pattern per cost type, so the four types never rely on colour alone (some pairs look alike with red-weak or
# green-weak vision; see dashboard/colour_check.py). The biggest type stays solid.
LINE_PATTERNS = {"token_expenditure": "x", "hosting": "/", "enablement": "", "integration": "."}


def line_pattern(line: str, m: str | None = None) -> dict:
    """Plotly marker.pattern for a cost type: a light texture drawn over its colour."""
    m = m or mode()
    return dict(shape=LINE_PATTERNS.get(line, ""), fillmode="overlay", fgcolor=TOKENS[m]["surface-solid"],
                fgopacity=0.55, solidity=0.25, size=7)


def chart_color(role: str, m: str | None = None) -> str:
    """Colour of a meaning on the forecast charts: 'history', 'forecast' or 'predicted'."""
    return CHART_COLORS[m or mode()][role]


def line_color(line: str, m: str | None = None) -> str:
    return LINE_COLORS[m or mode()][line]


def css_vars(m: str) -> str:
    """The tokens of one theme as CSS custom properties."""
    t = TOKENS[m]
    body = ";".join(f"--{k}:{v}" for k, v in t.items())
    oc = ";".join(f"--o-{k}:{v}" for k, v in OUTLOOK_COLORS[m].items())
    sp = ";".join(f"--s{i}:{v}px" for i, v in enumerate(SPACE))
    rd = ";".join(f"--r-{k}:{v}px" for k, v in RADIUS.items())
    return f":root{{{body};{oc};{sp};{rd};color-scheme:{m}}}"


def scene_palette(m: str | None = None) -> dict:
    """Colours handed to the 3D scenes (JSON-safe)."""
    m = m or mode()
    t = TOKENS[m]
    return {"mode": m, "text": t["text"], "muted": t["muted"], "accent": t["accent"], "accent2": t["accent-2"],
            "warm": t["warm"], "grid": t["grid"], "surface": t["elevated"], "border": t["border-strong"],
            "outlook": OUTLOOK_COLORS[m], "line": LINE_COLORS[m], "history": CHART_COLORS[m]["history"],
            "forecast": CHART_COLORS[m]["forecast"]}


def _template(m: str) -> go.layout.Template:
    t = TOKENS[m]
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family=FONT, color=t["text"], size=13), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[t["accent"], t["accent-2"], OUTLOOK_COLORS[m]["downside"], t["faint"]],
        hoverlabel=dict(font=dict(family=FONT, size=13, color=t["text"]), bgcolor=t["hover-bg"],
                        bordercolor=t["border-strong"], align="left"),
        margin=dict(l=16, r=20, t=56, b=72),
        title=dict(font=dict(family=DISPLAY_FONT, size=16, color=t["text"], weight=700), x=0.012, xanchor="left", y=0.97),
        xaxis=dict(gridcolor=t["grid"], zeroline=False, linecolor=t["border"], tickfont=dict(color=t["muted"], size=12),
                   title=dict(font=dict(color=t["muted"], size=12)), showspikes=False, automargin=True),
        yaxis=dict(gridcolor=t["grid"], zeroline=False, linecolor=t["border"], tickfont=dict(color=t["muted"], size=12),
                   title=dict(font=dict(color=t["muted"], size=12), standoff=10), automargin=True),
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0, font=dict(color=t["muted"], size=12),
                    itemclick=False, itemdoubleclick=False),
        barcornerradius=5, bargap=0.28,
        transition=dict(duration=400, easing="cubic-in-out"))
    return tpl


pio.templates["aiwi"] = _template("light")
pio.templates["aiwi_dark"] = _template("dark")
TEMPLATE = "aiwi"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


def template() -> str:
    return "aiwi_dark" if mode() == "dark" else "aiwi"


def money(x) -> str:
    """A dollar amount from the results, shown in rupees (converted here, at the last step):
    Indian style, see dashboard.currency.fmt: ₹950, ₹12,345, ₹23.1 L, ₹1.2 Cr."""
    return CUR.fmt_usd(x)


def money_tick(x: float) -> str:
    """Axis label for a dollar value, in rupees without a needless '.0': '₹50 L', '-₹2 Cr', '₹0'."""
    return CUR.tick(CUR.to_inr(float(x)))


def share(x) -> str:
    """Whole percentages, one decimal under 10% (but 0% stays 0%)."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "Not available"
    p = 100 * float(x)
    return f"{p:.1f}%" if 0 < abs(p) < 10 else f"{p:.0f}%"


def month(x, horizon: int = 12) -> str:
    """'Month 9', or 'Not within 12 months' for none."""
    from dashboard import copy as C
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return C.NOT_WITHIN.format(months=horizon)
    return C.MONTH.format(month=int(round(float(x))))
