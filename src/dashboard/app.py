"""AI Workforce Investment Intelligence dashboard (Phase 5). Run: streamlit run src/dashboard/app.py

Sets the theme for the session (light or dark), injects the design system, draws the top bar with the Dark mode
and Reduce motion switches and the banner, installs the page-level motion script and registers the nine pages
(Welcome first; forecast pages and money pages grouped in two menus), then adds the "Next" card under each page.
Streamlit puts this script's folder on the import path; it is removed again so that this folder's
`copy.py` can never shadow Python's own `copy` module (the module is imported as dashboard.ui.copy).
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != HERE]
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

import streamlit as st  # noqa: E402

if not getattr(sys, "_aiwi_diag", False):  # one line per server start in the host's log (helps when a host differs)
    import importlib.util
    sys._aiwi_diag = True
    print(f"[aiwi] python {sys.version.split()[0]} ({sys.executable}); plistlib found: "
          f"{importlib.util.find_spec('plistlib') is not None}; path: {sys.path}", file=sys.stderr, flush=True)

# Load the engine once, now that src/ is on the import path: later calls inside the pages then find it already
# loaded and never depend on the import path at that moment (several visitors share one server process).
import config  # noqa: E402,F401
import config_phase4  # noqa: E402,F401
import engine.drivers  # noqa: E402,F401
import engine.inputs  # noqa: E402,F401
import engine.report  # noqa: E402,F401
import engine.sensitivity  # noqa: E402,F401
import engine.simulate  # noqa: E402,F401
import tsaf.loaders  # noqa: E402,F401

from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402
from dashboard.core import state  # noqa: E402
from streamlit.runtime.scriptrunner_utils.exceptions import (  # noqa: E402
    RerunException, ScriptControlException, StopException)

st.set_page_config(page_title=C.PRODUCT, page_icon=":material/insights:", layout="wide",
                   initial_sidebar_state="auto")
K.init_theme()
state.init()
K.inject_css()
st.logo(str(HERE / "ui" / "assets" / "mark.svg"), size="large", icon_image=str(HERE / "ui" / "assets" / "mark.svg"))
K.motion_script()

# Left side navigation, in reading order (the same order as the Next cards): two pages, two groups, then your own figures.
SECTIONS = {"": ["welcome", "overview"], C.SECTION_FORECASTS: ["data", "forecast", "reliable"],
            C.SECTION_MONEY: ["costs", "timing", "levers"], C.SECTION_YOURS: ["company"]}
pages = {sec: [st.Page(K.PAGE_FILES[key], title=C.PAGES[key][0], icon=C.PAGES[key][1], default=(key == "welcome"))
               for key in keys] for sec, keys in SECTIONS.items()}
nav = st.navigation(pages, position="sidebar")
current = next((key for key, (title, _) in C.PAGES.items() if title == nav.title), "")
K.section_marker(next((sec for sec, keys in SECTIONS.items() if current in keys), ""))
K.page_tint(current)
with st.sidebar:
    K.sidebar_controls()
K.header_strip()
if not getattr(sys, "_aiwi_warm", False):  # first visit after the server woke up: the saved results load once
    sys._aiwi_warm = True
    _warm = st.empty()
    _warm.caption(C.WARMUP)
else:
    _warm = None


@st.dialog(C.TOUR_TITLE)
def _tour() -> None:
    for i, (title, line) in enumerate(C.TOUR_STEPS, 1):
        st.markdown(f"**{i}. {title}**  \n{line}")
    if st.button(C.TOUR_DONE, type="primary", key="tour_done"):
        st.session_state["_tour_seen"] = True
        K.remember_tour()
        st.rerun()


def _tour_wanted() -> bool:
    if os.environ.get("AIWI_TOUR") == "off" or st.query_params.get("tour") == "off":
        return False
    if st.session_state.get("_tour_seen"):
        return False
    try:
        return st.context.cookies.get("aiwi_tour") != "seen"
    except Exception:  # noqa: BLE001
        return True


if current == "welcome" and _tour_wanted():
    st.session_state["_tour_seen"] = True  # once per session even if closed with the cross
    K.remember_tour()
    _tour()

try:  # error boundary: one page failing never takes the whole site down
    nav.run()
except (RerunException, StopException, ScriptControlException):
    raise
except Exception:  # noqa: BLE001
    if os.environ.get("AIWI_STRICT"):
        raise
    print("[aiwi] page error: " + traceback.format_exc(), file=sys.stderr, flush=True)
    K.error_state(C.ERROR_TITLE, C.ERROR_BODY)
if _warm is not None:
    _warm.empty()
K.next_card(current)
K.about()
K.footer()
