"""How we forecast: the method in plain words, step by step (data, checks, approaches, testing, ranges, the money
model), where each of the seven trends comes from, and what the numbers cannot tell you."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from dashboard.core import data as D  # noqa: E402
from dashboard.ui import components as K  # noqa: E402
from dashboard.ui import copy as C  # noqa: E402


def render() -> None:
    K.page_header(C.METHOD_HEAD, C.METHOD_SUB, C.PAGES["method"][0])
    K.steps(C.METHOD_STEPS, C.METHOD_STEPS_TITLE, anchor="steps")
    K.section_title(C.METHOD_LIMITS_TITLE)
    for line in C.METHOD_LIMITS:
        K.note(line)
    K.section_title(C.METHOD_SOURCES_TITLE, C.METHOD_SOURCES_SUB)
    try:
        for name in D.forecast_series():
            K.provenance(name, D.history(name))
    except D.Missing:
        K.empty_state()
    K.section_title(C.METHOD_REPRO_TITLE)
    st.markdown(C.METHOD_REPRO)


render()
