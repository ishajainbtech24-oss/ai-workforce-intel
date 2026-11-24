"""AI Workforce Investment Intelligence dashboard (Phase 5). Run: streamlit run src/dashboard/app.py

Sets the theme for the session (light or dark), injects the design system, draws the top bar with the Dark mode
and Reduce motion switches and the banner, installs the page-level motion script and registers the nine pages
(Welcome first; forecast pages and money pages grouped in two menus), then adds the "Next" card under each page.
Streamlit puts this script's folder on the import path; it is removed again so that this folder's
`copy.py` can never shadow Python's own `copy` module (the module is imported as dashboard.copy).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != HERE]
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

import streamlit as st  # noqa: E402

# New code and results after every deploy. The hosting service pulls each push to GitHub into this folder while the
# server keeps running, and Python keeps the modules it already loaded, so a change would otherwise show only after
# a restart. When any source or result file is newer than what this server loaded, forget our modules and the
# cached data; the imports below then load the new files.
OURS = {"dashboard", "engine", "tsaf", "config", "config_phase2", "config_phase3", "config_phase4", "optional"}


def _newest_file() -> float:
    files = [*(ROOT / "src").rglob("*.py"), *HERE.glob("*.css"), *(ROOT / "config").glob("*.json"),
             *(ROOT / "outputs").glob("phase[1-4]/**/*.csv"), *(ROOT / "outputs").glob("phase[1-4]/**/*.json"),
             *(ROOT / "data" / "processed").glob("*.csv"), *(ROOT / ".streamlit").glob("*.toml")]
    return max((f.stat().st_mtime for f in files if f.exists()), default=0.0)


_stamp = _newest_file()
if getattr(sys, "_aiwi_loaded", None) is not None and _stamp > sys._aiwi_loaded:
    for name in [m for m in sys.modules if m.split(".")[0] in OURS]:
        del sys.modules[name]
    st.cache_data.clear()
    st.cache_resource.clear()
sys._aiwi_loaded = _stamp

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

from dashboard import components as K  # noqa: E402
from dashboard import copy as C  # noqa: E402

st.set_page_config(page_title=C.PRODUCT, page_icon=":material/insights:", layout="wide",
                   initial_sidebar_state="auto")
K.init_theme()
K.inject_css()
st.logo(str(HERE / "assets" / "mark.svg"), size="large", icon_image=str(HERE / "assets" / "mark.svg"))
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
nav.run()
K.next_card(current)
K.about()
K.footer()
