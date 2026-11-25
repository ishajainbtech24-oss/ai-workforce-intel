"""Read the precomputed Analyst-mode files in artifacts/ (written by src/build_artifacts.py). Nothing is fitted on a
page load: every table here is small and read once per server. A missing file raises data.Missing, so the page
shows its empty state instead of an error."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from dashboard.core import data as D


def _dir():
    return D.root() / "artifacts"


@st.cache_data(show_spinner=False)
def _json(name: str, root_str: str) -> dict:
    p = _dir() / f"{name}.json"
    if not p.exists():
        raise D.Missing(f"artifacts/{name}.json")
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _csv(rel: str, root_str: str) -> pd.DataFrame:
    p = _dir() / rel
    if not p.exists():
        raise D.Missing(f"artifacts/{rel}")
    return pd.read_csv(p)


def diagnostics(name: str) -> dict:
    return _json("diagnostics", str(D.root()))[name]


def residuals(name: str) -> dict:
    return _json("residuals", str(D.root()))[name]


def conformal(name: str) -> dict:
    return _json("conformal", str(D.root()))[name]


def stl(name: str) -> pd.DataFrame:
    return _csv(f"stl/{name}.csv", str(D.root()))


def fan(name: str) -> pd.DataFrame:
    return _csv(f"fan/{name}.csv", str(D.root()))


def _for(table: str, name: str) -> pd.DataFrame:
    t = _csv(f"{table}.csv", str(D.root()))
    return t[t["series"] == name].reset_index(drop=True)


def cv_metrics(name: str) -> pd.DataFrame:
    return _for("cv_metrics", name)


def cv_horizon(name: str) -> pd.DataFrame:
    return _for("cv_horizon", name)


def dm_tests(name: str) -> pd.DataFrame:
    return _for("dm_tests", name)


def model_cards(name: str) -> pd.DataFrame:
    return _for("model_cards", name)


def available() -> bool:
    return (_dir() / "conformal.json").exists()


def cal(name: str) -> dict | None:
    """Calibrated ranges of one trend for the Forecast pages: the fan table and how often its 80% range held in the
    rolling check. None when artifacts/ is missing (the pages then show the saved ranges)."""
    try:
        c, f = conformal(name), fan(name)
    except (D.Missing, KeyError):
        return None
    return {"fan": f, "coverage": c["coverage"].get("0.8"), "points": c["scored_points"]}
