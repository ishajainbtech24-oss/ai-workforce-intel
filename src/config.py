"""Phase 1 configuration: paths, driver table and backtest settings.

Supports syllabus Module 1 (choosing the series and their seasonal periods) and
Module 2/4 (evaluation design: horizons, rolling-origin settings, hold-out sizes).
Every number Phase 1 depends on lives here, so the review can point to one file.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs" / "phase1"
SEED = 42  # Phase 1 uses no randomness; kept so any later addition is reproducible.

# BurstGPT modelling window (verified in preprocessing): days 0-86 inclusive.
BURST_WINDOW_DAYS = (0, 86)

# Minimum number of observations (after the window and NaN checks) per grain.
MIN_OBS = {"daily": 60, "hourly": 24 * 21, "weekly": 40, "quarterly": 24, "monthly": 36}

# Rolling-origin settings per grain. A float `initial` means a share of n.
CV_SETTINGS = {
    "daily": {"initial": 42, "h": 7, "step": 7, "holdout": 14, "max_folds": None},
    "hourly": {"initial": 336, "h": 24, "step": 72, "holdout": 168, "max_folds": 8},
    "weekly": {"initial": 0.6, "h": 4, "step": 4, "holdout": 8, "max_folds": None},
    "quarterly": {"initial": 0.6, "h": 4, "step": 2, "holdout": 4, "max_folds": None},
    "monthly": {"initial": 0.6, "h": 6, "step": 3, "holdout": 6, "max_folds": None},
}
FAST_MAX_FOLDS = 3

# pandas frequency for the dated grains (BurstGPT uses a plain integer index).
FREQ = {"daily": "D", "weekly": "W-MON", "monthly": "MS", "quarterly": "QS"}

# The one daily series used to compare the four trend-measurement methods.
TREND_DRIVER = "burst_tokens_total_daily"
# Cross-correlation pair (Module 1): requests vs tokens, BurstGPT daily.
CCF_FILE, CCF_X, CCF_Y = "burstgpt_daily_wide", "requests", "total_tokens"

_BURST = {"index_col": "day_index", "window_col": "in_model_window", "source": "burstgpt"}
_WILD_W = {"index_col": "week", "source": "wildchat", "invalid_col": "partial_week"}

# `value_col` may join several columns with "+": they are summed (e.g. API = ChatGPT + GPT-4).
DRIVERS: list[dict] = [
    {"name": "burst_tokens_total_daily", "file": "burstgpt_daily_wide", "value_col": "total_tokens",
     "filter": None, "grain": "daily", "season": 7, "extra_seasons": [], "horizon": 7,
     "unit": "tokens per day", "min_obs": MIN_OBS["daily"], **_BURST,
     "notes": "All BurstGPT traffic (ChatGPT + GPT-4, API + chat)."},
    {"name": "burst_tokens_api_daily", "file": "burstgpt_daily_wide",
     "value_col": "ChatGPT_api_total_tokens+GPT-4_api_total_tokens", "filter": None,
     "grain": "daily", "season": 7, "extra_seasons": [], "horizon": 7, "unit": "tokens per day",
     "min_obs": MIN_OBS["daily"], "max_zero_share": 0.30, **_BURST,
     "notes": "API segment = ChatGPT_api + GPT-4_api tokens."},
    {"name": "burst_tokens_chat_daily", "file": "burstgpt_daily_wide",
     "value_col": "ChatGPT_conversation_total_tokens+GPT-4_conversation_total_tokens",
     "filter": None, "grain": "daily", "season": 7, "extra_seasons": [], "horizon": 7,
     "unit": "tokens per day", "min_obs": MIN_OBS["daily"], "max_zero_share": 0.30, **_BURST,
     "notes": "Chat segment = ChatGPT_conversation + GPT-4_conversation tokens."},
    {"name": "burst_requests_hourly", "file": "burstgpt_hourly_total", "value_col": "requests",
     "filter": None, "grain": "hourly", "season": 24, "extra_seasons": [168], "horizon": 24,
     "unit": "requests per hour", "min_obs": MIN_OBS["hourly"], "source": "burstgpt",
     "index_col": "hour_index", "window_col": "in_model_window",
     "notes": "All BurstGPT requests per hour; 43 empty hours in the window are true zeros."},
    {"name": "wildchat_conversations_daily", "file": "wildchat_daily", "value_col": "conversations",
     "filter": None, "aggregate": "sum", "grain": "daily", "season": 7, "extra_seasons": [],
     "horizon": 7, "unit": "conversations per day", "min_obs": MIN_OBS["daily"],
     "index_col": "date", "source": "wildchat",
     "window_rule": "longest_clean_run", "missing_col": "missing_day", "last_is_partial": True,
     "notes": ("Added (not in the prompt's table) because WildChat weekly cannot be analysed. "
               "Summed over model families. Some dates have no data at all and GPT-4 is absent "
               "from late June to early November 2023, so only the longest run with both families "
               "present is used. The file's last date is cut off by the shard download and is dropped.")},
    {"name": "wildchat_conversations_weekly", "file": "wildchat_weekly", "value_col": "conversations",
     "filter": None, "grain": "weekly", "season": None, "extra_seasons": [], "horizon": 4,
     "unit": "conversations per week", "min_obs": MIN_OBS["weekly"], **_WILD_W,
     "notes": "Weekly usage."},
    {"name": "wildchat_new_users_weekly", "file": "wildchat_weekly", "value_col": "new_users",
     "filter": None, "grain": "weekly", "season": None, "extra_seasons": [], "horizon": 4,
     "unit": "new users per week", "min_obs": MIN_OBS["weekly"], **_WILD_W,
     "notes": "Users are hashed IPs."},
    {"name": "wildchat_returning_share_weekly", "file": "wildchat_weekly",
     "value_col": "returning_share", "filter": None, "grain": "weekly", "season": None,
     "extra_seasons": [], "horizon": 4, "unit": "share of active users", "min_obs": MIN_OBS["weekly"],
     **_WILD_W, "notes": "Returning users / active users."},
    {"name": "eci_wages_quarterly", "file": "eci_quarterly", "value_col": "eci_wages_sa",
     "filter": None, "grain": "quarterly", "season": 4, "extra_seasons": [], "horizon": 4,
     "unit": "index", "min_obs": MIN_OBS["quarterly"], "index_col": "date", "source": "fred",
     "notes": "Seasonally adjusted ECI wages. eci_monthly is interpolated and never analysed."},
    {"name": "ppi_hosting_monthly", "file": "ppi_hosting_monthly", "value_col": "ppi_hosting",
     "filter": None, "grain": "monthly", "season": 12, "extra_seasons": [], "horizon": 6,
     "unit": "index", "min_obs": MIN_OBS["monthly"], "index_col": "date", "source": "fred",
     "notes": "PPI data processing and hosting."},
    {"name": "epoch_cheapest_price_monthly", "file": "epoch_prices_monthly",
     "value_col": "cheapest_available", "filter": None, "grain": "monthly", "season": None,
     "extra_seasons": [], "horizon": 6, "unit": "USD per million tokens",
     "min_obs": MIN_OBS["monthly"], "index_col": "month", "source": "epoch",
     "notes": "Cheapest blended price available (running minimum)."},
]


def driver_by_name(name: str) -> dict:
    """Return the driver config called `name` (KeyError if unknown)."""
    for cfg in DRIVERS:
        if cfg["name"] == name:
            return cfg
    raise KeyError(f"unknown driver '{name}'. Known: {[c['name'] for c in DRIVERS]}")

# Phase 3: how bootstrap errors grow beyond the backtest horizon H_cv.
# "sqrt": the error at step h > H_cv is the drawn fold's error at H_cv times sqrt(h / H_cv)
# (spread grows like a random walk, conservative for seasonal series); "none": no growth.
GROWTH = "sqrt"

# Phase 3 interval options (each can be switched off; the pseudo-holdout picks among the enabled ones).
# RECENCY_HALF_LIFE: fold sampling weights halve every (share x n_folds) folds of age; "none" = equal weights.
RECENCY_HALF_LIFE = 0.25
# LEVEL_MATCH: positive series only use folds whose level is within (low, high) x the current level
# (fewer than 3 qualify -> the 3 closest levels); "none" = all folds.
LEVEL_MATCH = (0.5, 2.0)

# Phase 4: engine roles -> real Phase 3 forecast files (checked against outputs/phase3/manifest.json).
# token_demand uses the 30-day run-rate file of this driver; token_price is optional (no Epoch file yet).
ENGINE_DRIVERS = {
    "token_demand": {"driver": "burst_tokens_total_daily", "file": "forecasts/burstgpt_monthly_run_rate.csv",
                     "required": True},
    "wages": {"driver": "eci_wages_quarterly", "file": "forecasts/eci_wages_quarterly.parquet", "required": True},
    "hosting": {"driver": "ppi_hosting_monthly", "file": "forecasts/ppi_hosting_monthly.parquet", "required": True},
    "token_price": {"driver": "epoch_cheapest_price_monthly",
                    "file": "forecasts/epoch_cheapest_price_monthly.parquet", "required": False},
}
