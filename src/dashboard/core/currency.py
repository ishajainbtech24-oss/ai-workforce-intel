"""The one place for the display currency: the exchange rate, its date and source, and the rupee formatter.

The saved results and the engine work in US dollars. The dashboard converts an amount to rupees only at the last
step before it is formatted (`T.money` calls `fmt_usd`). On "Try your own numbers" it also converts typed rupee
amounts back to dollars before calling the engine. To update the rate, change INR_PER_USD, RATE_DATE and
RATE_SOURCE here and nothing else.
"""
from __future__ import annotations

import datetime as _dt
import math

INR_PER_USD = 94.1159                      # RBI reference rate
RATE_DATE = _dt.date(2026, 11, 16)
RATE_SOURCE = "RBI reference rate"
CURRENCY = {"symbol": "₹", "code": "INR"}
SYM = CURRENCY["symbol"]
LAKH, CRORE = 1e5, 1e7


def rate() -> float:
    """The current rate (read at call time, so a test can change INR_PER_USD)."""
    return float(INR_PER_USD)


def to_inr(usd):
    return usd * rate()


def to_usd(inr):
    return inr / rate()


def group(n: int) -> str:
    """Indian digit grouping of a whole number >= 0: 12345 -> '12,345', 1234567 -> '12,34,567'."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def fmt(inr) -> str:
    """A rupee amount in the Indian style: ₹950, ₹12,345, ₹23.1 L, ₹1.2 Cr, ₹2.61 Cr, -₹23.1 L, ₹0."""
    if inr is None or (isinstance(inr, float) and not math.isfinite(inr)):
        return "Not available"
    x = float(inr)
    a = abs(x)
    if round(a) < LAKH:
        body = f"{SYM}{group(round(a))}"
    elif round(a / LAKH, 1) < 100:
        body = f"{SYM}{a / LAKH:.1f} L"
    else:  # one or two decimals: ₹1.2 Cr, ₹2.61 Cr
        cr = f"{a / CRORE:.2f}"
        body = f"{SYM}{cr[:-1] if cr.endswith('0') else cr} Cr"
    return ("-" if x < 0 and body != f"{SYM}0" else "") + body


def tick(inr: float) -> str:
    """Axis label in the same style without a needless '.0': 5000000 -> '₹50 L', -20000000 -> '-₹2 Cr'."""
    return fmt(inr).replace(".0 L", " L").replace(".0 Cr", " Cr")


def fmt_usd(usd) -> str:
    """A dollar amount from the saved results, shown in rupees."""
    if usd is None or (isinstance(usd, float) and not math.isfinite(usd)):
        return "Not available"
    return fmt(to_inr(float(usd)))


def rate_text() -> str:
    """'₹94.1159' (the rate as given, without trailing zeros)."""
    return f"{SYM}{rate():.4f}".rstrip("0").rstrip(".")


def date_text() -> str:
    return f"{RATE_DATE.day} {RATE_DATE.strftime('%b %Y')}"
