"""Phase 2 settings: model grids, budgets, horizons and extra (exogenous) series.

Seasonal periods, d, D and the decomposition come from outputs/phase1/handoff.json, never
from here. Everything Phase 2 tunes or caps is listed in this one file for the review.
"""
from __future__ import annotations

from config import ROOT

OUT_DIR = ROOT / "outputs" / "phase2"
HANDOFF = ROOT / "outputs" / "phase1" / "handoff.json"
SEED = 42

FAMILY_ORDER = ["baseline", "smoothing", "arima", "ml", "deep", "ensemble"]  # simplest first
TIE_TOLERANCE = 0.01  # CV MASE within 1% of the best counts as a tie

# Smoothing: moving-average windows tried on the first training window.
MA_WINDOWS = {"daily": (3, 7, 14), "other": (3, 4, 8)}
VALIDATION_SHARE = 0.2  # last 20% of the first training window, for MA window and Ridge alpha

# ARIMA order grid (AICc on the first training window only).
ARIMA_P, ARIMA_Q, ARIMA_SP, ARIMA_SQ = (0, 1, 2), (0, 1, 2), (0, 1), (0, 1)
ARIMA_MAX_CANDIDATES, ARIMA_MAX_CANDIDATES_FAST = 24, 8
ARIMA_BUDGET_S = 90.0  # per driver, shared by the ARIMA, SARIMA and SARIMAX order searches
ARIMA_MAXITER = 50
FOURIER = {24: 3, 168: 3}  # period -> K for hourly SARIMAX

# Machine learning.
ML_LAGS = {"daily": (1, 2, 7, 14), "hourly": (1, 2, 24, 168)}
ML_ROLL = {"daily": 7, "hourly": 24}
RIDGE_ALPHAS = (0.1, 1.0, 10.0)
N_TREES, N_TREES_FAST = 200, 100
RF_MAX_DEPTH, XGB_MAX_DEPTH, XGB_LR = 6, 3, 0.05
TREE_JOBS = 2
ML_GRAINS = ("daily", "hourly")

# Extra series used as a multivariate feature. The lag equals the longest horizon the series
# is ever forecast for (hold-out and Phase 3: 14 days), so no future value is ever needed.
EXTRA_SERIES = {"burst_tokens_total_daily": {"file": "burstgpt_daily_wide", "col": "requests",
                                             "index_col": "day_index", "lag": 14}}

PROPHET_DRIVERS = ("burst_tokens_total_daily",)
PROPHET_START = "2000-01-03"  # an arbitrary Monday, used only as an index (BurstGPT has no dates)
LSTM_DRIVERS = ("burst_tokens_total_daily", "burst_requests_hourly")
LSTM = {"hidden": 16, "window": {"daily": 14, "hourly": 168}, "lr": 0.01, "epochs": 30, "batch": 32}

MODEL_BUDGET_S = 240.0  # wall-clock cap for one model on one driver (checked between fits)

# Intervals: leave-one-fold-out empirical quantiles of the absolute errors.
LEVELS = (0.80, 0.95)
COVERAGE_FLAG = {0.80: 0.60, 0.95: 0.85}
MIN_FOLDS_FOR_INTERVALS = 3

ANOMALY_Z = 3.5
DAY77 = {"driver": "burst_tokens_total_daily", "time": 77}

# Phase 3 forecast horizon by grain (Epoch monthly is 12 as well).
HORIZON_FOR_FORECAST = {"daily": 14, "hourly": 168, "weekly": 8, "quarterly": 8, "monthly": 12}
