"""Phase 3 settings: sample paths, sanity guards, units and output layout.

The growth rule beyond the backtest horizon is `config.GROWTH`; everything else Phase 3
needs is listed here so the review can point to one file.
"""
from __future__ import annotations

from config import ROOT

OUT_DIR = ROOT / "outputs" / "phase3"
PHASE1_DIR = ROOT / "outputs" / "phase1"
PHASE2_DIR = ROOT / "outputs" / "phase2"
QUALITY_LOG = ROOT / "reports" / "data_quality.md"

N_SAMPLES = 200
SEED_BASE = 42           # driver seed = SEED_BASE + position in the sorted driver names
POINT_SAMPLE_ID = -1
SANITY_MAX_RATIO = 10.0  # a point forecast above 10 x the largest training value is rejected
BRACKET_SHARE = 0.90     # P10-P90 must bracket the point forecast in at least 90% of steps
MIN_FOLDS = 3
COVERAGE_FLAG = {0.80: 0.60, 0.95: 0.85}
HOURLY_SPLIT = 24        # hourly holdout coverage reported for steps 1-24 and 25-168

COLUMNS = ["driver", "period_index", "calendar_month", "sample_id", "value", "unit", "model",
           "source", "grain", "kind"]
GRAIN_NAME = {"hourly": "hour", "daily": "day", "weekly": "week", "monthly": "month", "quarterly": "quarter"}
# Standard unit from the first words of the driver's config unit (checked non-empty).
UNIT_MAP = {"tokens": "tokens", "requests": "requests", "conversations": "conversations",
            "new users": "users", "share": "share", "index": "index_points",
            "usd per million tokens": "usd_per_mtok"}
NON_NEGATIVE_UNITS = {"tokens", "requests", "conversations", "users", "usd_per_mtok", "index_points", "share"}

# BurstGPT 30-day run-rate: 14 simulated days + 16 x the mean of the last 7 simulated days.
RUN_RATE_DRIVERS = ("burst_tokens_total_daily", "burst_tokens_api_daily", "burst_tokens_chat_daily")
RUN_RATE = {"days": 30, "forecast_days": 14, "tail_days": 7}

FAN_HISTORY = {"hourly": 336, "daily": 42, "weekly": 52, "monthly": 60, "quarterly": 40}
FAN_THIN_PATHS = 30

# Processed files Phase 3 reads besides the driver files (token shares and scenario inputs).
DATA_FILES = ("burstgpt_daily", "genai_tracker", "genai_timesaved_panel", "metr_effect_summary", "metr_tasks")

# Interval options: choice per driver by a pseudo-holdout on the LAST backtest folds (never the final holdout).
PSEUDO_SHARE = 0.20           # share of folds held out (at least PSEUDO_MIN)
PSEUDO_MIN = 2
LEVEL_MATCH_MIN_FOLDS = 3
# Phase 4 sensitivity: scale each path's deviation from the point forecast; never applied to the saved files.
UNCERTAINTY_MULTIPLIER = 1.0
SENSITIVITY_MULTIPLIERS = (1.0, 1.5, 2.0)
