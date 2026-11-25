"""Colour checks used by the tests (and runnable on their own): WCAG contrast, see-through colours drawn over the page,
and a colour-blindness simulation (Machado, Oliveira and Fernandes 2009, full severity) with CIELAB distances.

Run: python -m dashboard.ui.colour_check   (from the src folder) prints every check for both themes.
"""
from __future__ import annotations

import itertools
import re

import numpy as np

# Machado et al. (2009), severity 1.0, applied to linear RGB
CVD = {"deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
       "protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
       "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]])}
TEXT_MIN, GRAPHIC_MIN, APART_MIN = 4.5, 3.0, 20.0  # WCAG text, WCAG non-text, CIELAB distance for 'clearly different'


def rgba(c: str) -> tuple[float, float, float, float]:
    """'#RRGGBB' or 'rgba(r,g,b,a)' -> (r, g, b, a) with r, g, b in 0..1."""
    c = c.strip()
    if c.startswith("#"):
        return tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)) + (1.0,)
    nums = [float(x) for x in re.findall(r"[\d.]+", c)]
    return nums[0] / 255, nums[1] / 255, nums[2] / 255, (nums[3] if len(nums) > 3 else 1.0)


def css_to_hex(c: str) -> tuple[str, float]:
    """A colour as a browser reports it ('rgb(1, 2, 3)', 'rgba(1, 2, 3, 0.5)', 'color(srgb 0.1 0.2 0.3 / 0.5)' or
    '#RRGGBB') -> ('#RRGGBB', alpha)."""
    c = c.strip()
    if c.startswith("#"):
        return c.upper(), 1.0
    nums = [float(x) for x in re.findall(r"-?[\d.]+", c)]
    if c.startswith("color("):
        r, g, b = (round(max(0.0, min(1.0, v)) * 255) for v in nums[:3])
    else:
        r, g, b = (round(v) for v in nums[:3])
    a = nums[3] if len(nums) > 3 else 1.0
    return f"#{r:02X}{g:02X}{b:02X}", a


def over(fg: str, bg: str) -> str:
    """The solid colour a see-through colour shows as when drawn over a solid background."""
    r, g, b, a = rgba(fg)
    R, G, B, _ = rgba(bg)
    mix = [a * x + (1 - a) * y for x, y in ((r, R), (g, G), (b, B))]
    return "#" + "".join(f"{round(v * 255):02X}" for v in mix)


def _lin(c: str) -> np.ndarray:
    v = np.array(rgba(c)[:3])
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def luminance(c: str) -> float:
    r, g, b = _lin(c)
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _lab(lin_rgb: np.ndarray) -> np.ndarray:
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ np.clip(lin_rgb, 0, 1)
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def distance(a: str, b: str, vision: str | None = None) -> float:
    """CIELAB distance between two colours as seen with normal vision or one colour-vision deficiency."""
    la, lb = _lin(a), _lin(b)
    if vision:
        la, lb = CVD[vision] @ la, CVD[vision] @ lb
    return float(np.linalg.norm(_lab(la) - _lab(lb)))


def min_distance(colours: dict[str, str]) -> tuple[float, str]:
    """Smallest distance between any two of the colours, over normal vision and the three deficiencies."""
    worst = (float("inf"), "")
    for (na, a), (nb, b) in itertools.combinations(colours.items(), 2):
        for v in (None, "deutan", "protan", "tritan"):
            d = distance(a, b, v)
            if d < worst[0]:
                worst = (d, f"{na}/{nb} ({v or 'normal'})")
    return worst


def chart_groups(m: str) -> dict[str, dict[str, str]]:
    """The colours each chart draws side by side (only these need to stay apart from each other)."""
    from dashboard.ui import theme as T
    c, t = T.CHART_COLORS[m], T.TOKENS[m]
    return {"running balance (outlooks)": dict(T.OUTLOOK_COLORS[m]),
            "what we expect next": {"history": c["history"], "forecast": c["forecast"]},
            "how reliable it is": {"history": c["history"], "predicted": c["predicted"], "inside": t["good"],
                                   "outside": t["warm"]},
            "the data we used": {"history": c["history"], "unusual": t["warm"], "outage": t["accent"]}}


def cost_types_told_apart(m: str) -> list[str]:
    """Pairs of cost types that look alike for some viewers AND share a fill pattern (should be empty)."""
    from dashboard.ui import theme as T
    cols, bad = T.LINE_COLORS[m], []
    for a, b in itertools.combinations(cols, 2):
        close = min(distance(cols[a], cols[b], v) for v in (None, "deutan", "protan", "tritan")) < APART_MIN
        if close and T.LINE_PATTERNS.get(a, "") == T.LINE_PATTERNS.get(b, ""):
            bad.append(f"{a}/{b}")
    return bad


def report(m: str) -> list[tuple[str, float, float]]:
    """(check, value, minimum) for one theme: text, buttons and chart lines on what they are drawn over."""
    from dashboard.ui import theme as T
    t = T.TOKENS[m]
    card = over(t["surface"], t["bg"])  # glass cards as drawn over the page
    elevated = over(t["elevated"], t["bg"])
    rows = []
    for fg in ("text", "muted", "faint", "accent", "warm", "warm-text", "good"):
        for name, bg in (("page", t["bg"]), ("card", card), ("solid card", t["surface-solid"]), ("raised card", elevated)):
            rows.append((f"text {fg} on {name}", contrast(t[fg], bg), TEXT_MIN))
    rows.append(("text warm-text on banner", contrast(t["warm-text"], over(t["warm-soft"], t["bg"])), TEXT_MIN))
    rows.append(("text accent on selected pill", contrast(t["accent"], over(t["accent-soft"], t["surface-solid"])), TEXT_MIN))
    rows.append(("button text on accent", contrast(t["on-accent"], t["accent"]), TEXT_MIN))
    # buttons and numbered circles run a gradient from accent to accent-2: the text must read at both ends
    rows.append(("button text on second accent", contrast(t["on-accent"], t["accent-2"]), TEXT_MIN))
    rows.append(("pill text warm-text on pill", contrast(t["warm-text"], over(t["warm-soft"], t["bg"])), TEXT_MIN))
    for role, col in T.CHART_COLORS[m].items():
        rows.append((f"line {role} on card", contrast(col, card), GRAPHIC_MIN))
    for role, col in T.LINE_COLORS[m].items():
        rows.append((f"cost type {role} on card", contrast(col, card), GRAPHIC_MIN))
    rows.append(("cost types told apart by colour or pattern", 0.0 if cost_types_told_apart(m) else 1.0, 1.0))
    for role, col in T.OUTLOOK_COLORS[m].items():
        rows.append((f"line outlook {role} on card", contrast(col, card), GRAPHIC_MIN))
    for chart, colours in chart_groups(m).items():
        d, pair = min_distance(colours)
        rows.append((f"apart on {chart}, all visions (closest: {pair})", d, APART_MIN))
    return rows


if __name__ == "__main__":  # pragma: no cover
    for theme in ("light", "dark"):
        print(f"== {theme}")
        for check, value, need in report(theme):
            print(f"  {'ok  ' if value >= need else 'FAIL'} {check}: {value:.2f} (need {need})")
