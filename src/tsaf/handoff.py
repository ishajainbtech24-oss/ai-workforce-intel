"""The Phase 1 -> Phase 2 hand-off file and its schema check (syllabus Module 4: model plan).

Phase 2 reads `handoff.json` to know, per driver, the season, differencing orders,
decomposition type, CV settings and the baseline score it has to beat.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

NUM = (int, float)
SCHEMA: dict[str, tuple] = {
    "name": (str,), "file": (str,), "value_col": (str,), "grain": (str,), "n_obs": (int,),
    "season": (int, type(None)), "extra_seasons": (list,), "decomposition": (str,),
    "d": (int,), "D": (int,), "tests_agree": (bool,), "log_candidate": (bool,),
    "cv_settings": (dict,), "best_baseline": (str,), "best_baseline_cv_mase": NUM,
    "best_baseline_holdout_mase": NUM + (type(None),), "seasonal_naive_cv_mase": NUM,
    "notes": (str,),
}
CV_KEYS = ("initial", "h", "step", "holdout")


def _clean(v):
    """JSON-safe value: NaN/inf become None, numpy scalars become Python numbers."""
    if hasattr(v, "item") and not isinstance(v, (list, dict, str)):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def make_entry(r: dict) -> dict:
    """Build one hand-off entry from a driver result dict produced by the pipeline."""
    cfg, best = r["cfg"], r["best"]
    cv = {k: int(r["cv_settings"][k]) for k in CV_KEYS}
    entry = {
        "name": cfg["name"], "file": cfg["file"], "value_col": cfg["value_col"],
        "grain": cfg["grain"], "n_obs": int(r["summary"]["n"]),
        "season": cfg["season"], "extra_seasons": list(cfg.get("extra_seasons") or []),
        "decomposition": r["decomp"]["type"], "d": int(r["diff"]["d"]), "D": int(r["diff"]["D"]),
        "tests_agree": bool(r["diff"]["tests_agree"]), "log_candidate": bool(r["decomp"]["log_candidate"]),
        "cv_settings": cv, "best_baseline": best["baseline"],
        "best_baseline_cv_mase": best["cv_mase"], "best_baseline_holdout_mase": best["holdout_mase"],
        "seasonal_naive_cv_mase": r["snaive_cv_mase"], "notes": " ".join(r["notes"]),
    }
    return {k: _clean(v) for k, v in entry.items()}


def validate(doc: dict) -> None:
    """Raise ValueError if the hand-off document does not match SCHEMA."""
    if not isinstance(doc.get("drivers"), list) or not doc["drivers"]:
        raise ValueError("handoff must contain a non-empty 'drivers' list")
    for e in doc["drivers"]:
        keys = set(e)
        if keys != set(SCHEMA):
            raise ValueError(f"{e.get('name')}: keys differ, missing {set(SCHEMA) - keys}, "
                             f"extra {keys - set(SCHEMA)}")
        for k, types in SCHEMA.items():
            if not isinstance(e[k], types) or (bool in types) != isinstance(e[k], bool):
                raise ValueError(f"{e['name']}: '{k}' has type {type(e[k]).__name__}")
        if set(e["cv_settings"]) != set(CV_KEYS):
            raise ValueError(f"{e['name']}: cv_settings must have keys {CV_KEYS}")
        if e["decomposition"] not in ("additive", "multiplicative"):
            raise ValueError(f"{e['name']}: bad decomposition '{e['decomposition']}'")


def write_handoff(results: list[dict], skipped: list[dict], window: str, path: Path) -> dict:
    """Write and validate handoff.json; returns the document."""
    doc = {"phase": 1, "modelling_window": window,
           "drivers": [make_entry(r) for r in results],
           "skipped": [{"name": s["name"], "reason": s["reason"]} for s in skipped]}
    validate(doc)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    validate(json.loads(path.read_text(encoding="utf-8")))
    return doc
