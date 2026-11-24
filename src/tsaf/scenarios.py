"""Scenario inputs (assumptions, NOT forecasts) and the measured inputs handed to Phase 4.

Scenario rows use only numbers that exist in the processed data or the preprocessing quality
log; a number that cannot be found is left out (and reported), never invented. Column meanings:
`time_saved_pct_hours` in genai_tracker / genai_timesaved_panel is FRED RPSGENAITS* "GenAI time
savings, % of work hours" (renamed in prep_fred.py); METR times are minutes per task.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

import config
from tsaf.loaders import read_table

PAPER_RE = re.compile(r"paper_estimate:\*\*\s*([+-]?\d+(?:\.\d+)?)%\s*([^\n]*)")


def _row(scenario, parameter, value, unit, source, derivation, status) -> dict:
    return {"scenario": scenario, "parameter": parameter, "value": float(value), "unit": unit,
            "source": source, "derivation": derivation, "status": status, "kind": "assumption"}


def metr_rows(data_dir: Path, quality_log: Path, notes: list[str]) -> list[dict]:
    """Downside: the METR paper estimate (from the quality log) and the naive ratio from the data."""
    rows = []
    text = quality_log.read_text(encoding="utf-8") if quality_log.exists() else ""
    m = PAPER_RE.search(text)
    if m:
        rows.append(_row("downside", "task_time_change_with_ai", m.group(1), "pct_change_in_task_time",
                         "METR RCT (paper estimate, recorded in reports/data_quality.md)",
                         f"Read from the quality log line 'paper_estimate: {m.group(1)}% {m.group(2).strip()}': "
                         "AI-allowed tasks took this much LONGER, so no time is saved.", "from_quality_log"))
    else:
        notes.append("METR paper estimate not found in the quality log; that row is left out.")
    eff = read_table(data_dir, "metr_effect_summary").set_index("ai_treatment")
    ratio = 100 * (eff.loc[1, "mean_minutes"] / eff.loc[0, "mean_minutes"] - 1)
    rows.append(_row("downside", "task_time_change_with_ai_naive", round(ratio, 3), "pct_change_in_task_time",
                     "METR RCT (metr_effect_summary)",
                     f"Mean minutes per task with AI allowed ({eff.loc[1, 'mean_minutes']:.2f}, "
                     f"{int(eff.loc[1, 'tasks'])} tasks) divided by without AI ({eff.loc[0, 'mean_minutes']:.2f}, "
                     f"{int(eff.loc[0, 'tasks'])} tasks), minus 1; a ratio of means, not the paper's regression.",
                     "measured"))
    return rows


def tracker_rows(data_dir: Path) -> list[dict]:
    """Expected: latest national time saved; optimistic: highest value in the occupation/industry panel."""
    tr = read_table(data_dir, "genai_tracker").sort_values("date")
    last = tr.dropna(subset=["time_saved_pct_hours"]).iloc[-1]
    rows = [_row("expected", "time_saved_share_of_work_hours", last["time_saved_pct_hours"], "pct_of_work_hours",
                 "FRED GenAI tracker RPSGENAITSALL (genai_tracker)",
                 f"Latest quarter ({pd.Timestamp(last['date']).date()}) of time_saved_pct_hours, "
                 "GenAI time savings as % of work hours, all employed adults.", "measured")]
    pan = read_table(data_dir, "genai_timesaved_panel").dropna(subset=["time_saved_pct_hours"])
    top = pan.loc[pan["time_saved_pct_hours"].idxmax()]
    rows.append(_row("optimistic", "time_saved_share_of_work_hours", top["time_saved_pct_hours"], "pct_of_work_hours",
                     f"FRED GenAI tracker panel {top['series_id']} (genai_timesaved_panel)",
                     f"Highest value in the {len(pan['series_id'].unique())}-series occupation/industry panel: "
                     f"'{top['description']}' ({top['group_type']}) in {pd.Timestamp(top['date']).date()}.", "measured"))
    return rows


def build_scenarios(data_dir: Path, quality_log: Path) -> tuple[pd.DataFrame, list[str]]:
    """The scenario table (kind = assumption) and notes on anything left out."""
    notes: list[str] = []
    rows: list[dict] = []
    for part in (lambda: metr_rows(data_dir, quality_log, notes), lambda: tracker_rows(data_dir)):
        try:
            rows += part()
        except Exception as exc:  # noqa: BLE001 - a missing source drops its rows, never invents them
            notes.append(f"scenario rows skipped: {type(exc).__name__}: {exc}")
    return pd.DataFrame(rows), notes


def token_shares(data_dir: Path) -> dict:
    """Input-token share (request tokens / all tokens) and API / chat shares in the BurstGPT window."""
    lo, hi = config.BURST_WINDOW_DAYS
    out: dict = {"window": f"BurstGPT days {lo}-{hi}"}
    try:
        d = read_table(data_dir, "burstgpt_daily")
        d = d[d["day_index"].between(lo, hi)]
        tot = float(d["total_tokens"].sum())
        out["input_token_share"] = float(d["request_tokens"].sum()) / tot
        out["output_token_share"] = float(d["response_tokens"].sum()) / tot
        out["input_token_note"] = "request_tokens / total_tokens summed over the window (burstgpt_daily)"
    except Exception as exc:  # noqa: BLE001
        out["input_token_share"] = None
        out["input_token_note"] = f"not measurable: {exc}"
    try:
        w = read_table(data_dir, "burstgpt_daily_wide")
        w = w[w["day_index"].between(lo, hi)]
        tot = float(w["total_tokens"].sum())
        api = w[["ChatGPT_api_total_tokens", "GPT-4_api_total_tokens"]].to_numpy().sum()
        chat = w[["ChatGPT_conversation_total_tokens", "GPT-4_conversation_total_tokens"]].to_numpy().sum()
        out["api_token_share"], out["chat_token_share"] = float(api / tot), float(chat / tot)
    except Exception as exc:  # noqa: BLE001
        out["api_token_share"] = out["chat_token_share"] = None
        out["segment_note"] = f"not measurable: {exc}"
    return {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in out.items()}
