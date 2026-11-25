"""One source of truth for the visitor's view: company preset, outlook, caution level and trend.

Values live in st.session_state (so they persist across pages) and are mirrored to the address bar
(st.query_params), so a copied link reproduces the view: ?preset=small&outlook=optimistic&caution=more&trend=pay.
Nothing is stored on the server's disk.
"""
from __future__ import annotations

import streamlit as st

KEYS = {"preset": "sc_preset", "outlook": "sc_outlook", "caution": "sc_caution", "trend": "trend"}
DEFAULTS = {"preset": "example", "outlook": "expected", "caution": 1.0, "trend": "ppi_hosting_monthly"}
# readable values in the address <-> internal names
URL_OUTLOOK = {"cautious": "downside", "expected": "expected", "optimistic": "optimistic"}
URL_CAUTION = {"standard": 1.0, "more": 1.5, "most": 2.0}
URL_TREND = {"pay": "eci_wages_quarterly", "hosting": "ppi_hosting_monthly", "ai-total": "burst_tokens_total_daily",
             "ai-apps": "burst_tokens_api_daily", "ai-chat": "burst_tokens_chat_daily",
             "ai-requests": "burst_requests_hourly", "chats": "wildchat_conversations_daily"}
PRESETS = ("example", "small", "enterprise")


def _from_url(name: str, raw: str):
    if name == "outlook":
        return URL_OUTLOOK.get(raw)
    if name == "caution":
        return URL_CAUTION.get(raw)
    if name == "trend":
        return URL_TREND.get(raw, raw if raw in URL_TREND.values() else None)
    if name == "preset":
        return raw if raw in PRESETS else None
    return None


def _to_url(name: str, value) -> str | None:
    rev = {"outlook": {v: k for k, v in URL_OUTLOOK.items()}, "caution": {v: k for k, v in URL_CAUTION.items()},
           "trend": {v: k for k, v in URL_TREND.items()}}
    if name in rev:
        return rev[name].get(value)
    return value if value in PRESETS else None


def init() -> None:
    """Once per session: take any values from the address, else the defaults."""
    if st.session_state.get("_state_ready"):
        return
    for name, key in KEYS.items():
        raw = st.query_params.get(name)
        val = _from_url(name, raw) if raw else None
        st.session_state.setdefault(key, val if val is not None else DEFAULTS[name])
    st.session_state["_state_ready"] = True


def get(name: str):
    try:
        return st.session_state.get(KEYS[name], DEFAULTS[name])
    except Exception:  # noqa: BLE001 - outside a Streamlit run
        return DEFAULTS[name]


def set(name: str, value) -> None:  # noqa: A001 - mirrors get()
    st.session_state[KEYS[name]] = value


def sync_url(names: tuple[str, ...]) -> None:
    """Write the named values into the address bar (only those that are shareable), so the link reproduces the view."""
    for name in names:
        text = _to_url(name, get(name))
        if text is None:
            continue
        if st.query_params.get(name) != text:
            st.query_params[name] = text
