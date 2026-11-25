"""Text of the closed "Explore technical details" panels: the only place on screen where technical names appear,
and each one is explained in plain words in the same sentence. Kept apart from copy.py so the banned-word test on
copy.py still covers everything else."""
from __future__ import annotations

# technical name of each approach (dictionary keys are the engine names)
TECH_NAME = {"naive": "Naive", "seasonal_naive": "Seasonal naive", "mean": "Mean", "drift": "Drift",
             "seasonal_ma3": "Seasonal moving average (3 cycles)", "moving_average": "Moving average",
             "ses": "Simple exponential smoothing", "holt": "Holt's linear trend", "damped_holt": "Damped Holt",
             "hw_additive": "Holt-Winters (additive)", "hw_multiplicative": "Holt-Winters (multiplicative)",
             "arima": "ARIMA", "sarima": "SARIMA", "sarimax": "SARIMAX", "ridge": "Ridge regression",
             "random_forest": "Random forest", "xgboost": "XGBoost", "ridge_with_requests": "Ridge regression with requests",
             "random_forest_with_requests": "Random forest with requests", "xgboost_with_requests": "XGBoost with requests",
             "prophet": "Prophet", "lstm": "LSTM neural network", "ensemble": "Ensemble"}

TERMS = {
    "interval": ("Prediction interval (80%)", "the likely range: the band where the value lands in eight of ten "
                 "simulated futures."),
    "simulation": ("Simulated futures", "{n} possible paths for the trend, each built by adding errors of the size "
                   "seen in past checks to the expected line."),
    "percentile": ("10th and 90th percentile", "the low and high edges of the likely range: one in ten simulated "
                   "futures is below the low edge, one in ten above the high edge."),
    "horizon": ("Horizon", "how far ahead the forecast was saved: {h} {grains}. Shorter choices show part of it."),
    "mae": ("MAE (mean absolute error)", "the average size of a miss, ignoring whether it was too high or too low. "
            "Shown on the page as 'average miss'."),
    "cv": ("Cross-validation (earlier checks)", "the forecast was rerun from several past cut-off points, each "
           "time predicting values it had not seen, and the misses were averaged."),
    "holdout": ("Hold-out (held back)", "the most recent {n} {grains}, kept out of every fit and used once at the "
                "end to check the chosen approach."),
    "mase": ("MASE (scaled error)", "the average miss divided by the miss of a simple repeat; below 1 means better "
             "than the simple repeat. For the approach used: {value}."),
    "seasonal_naive": ("Seasonal naive", "the simple yardstick: repeat the value from the same point in the last "
                       "cycle."),
    "stl": ("Seasonal-trend decomposition (STL)", "splits the series into a long-term trend, a repeating pattern "
            "(seasonality) and what is left over (the remainder)."),
    "strength": ("Strength (0 to 1)", "how much of the movement the trend or the repeating pattern explains: trend "
                 "{trend}, repeating pattern {pattern}. Shown on the page as strong (0.6 and up), some (0.3 and up) "
                 "or little."),
    "zscore": ("Robust z-score above 3.5", "how unusual a value is: its distance from what a simple repeat "
               "predicted, measured against the typical distance. Above 3.5 counts as unusual."),
    "monte_carlo": ("Monte Carlo simulation", "{n} random futures for pay and technology prices, built from the "
                    "saved forecasts; the share that pays back is counted month by month."),
    "caution": ("Caution setting", "More cautious multiplies the spread of the pay and price futures by 1.5; Most "
                "cautious by 2. Phase 3 found the saved ranges too narrow, which is why these settings exist."),
    "sensitivity": ("One-at-a-time sensitivity", "each input is set 20% lower and 20% higher while every other "
                    "input stays at its example value, and the change in the year-end balance is recorded."),
    "approach": ("Approach used", "{plain} (technical name: {tech})."),
}
RANK_TABLE_COLS = ("Approach (plain name)", "Technical name", "Average miss (MAE)", "Scaled error (MASE)")

# ---------------------------------------------------------------- Analyst mode (off by default; technical names allowed)
ANALYST = "Analyst mode"
ANALYST_HELP = ("Adds the statistical checks behind each trend and each forecast: decomposition, stationarity tests, "
                "autocorrelation, model cards, rolling-origin cross-validation and residual checks. Off by default.")
ANALYST_DATA_TITLE = "Analyst view: what the series is made of"
ANALYST_REL_TITLE = "Analyst view: how the forecasts were tested"
STL_PANELS = ("Series", "Trend (long-run level)", "Seasonal (repeating pattern)", "Remainder (what is left over)")
STL_STRENGTH = "STL decomposition. Trend strength {trend:.2f}, seasonal strength {season:.2f} (0 = none, 1 = all of the movement)."
STAT_TITLE = "Stationarity (does the level wander?)"
STAT_LINE = ("ADF p = {adf:.3f} (small p: no wandering), KPSS p = {kpss:.3f} (small p: wandering). Verdict: {verdict}.")
ACF_TITLE, PACF_TITLE = "Autocorrelation (ACF)", "Partial autocorrelation (PACF)"
ACF_AXIS, PACF_AXIS, LAG = "Correlation", "Partial correlation", "Lag"
BAND_NOTE = "Dashed lines: ±{band:.2f}, the range expected if there were no correlation (about 95%)."
SUBSERIES_TITLE = "Average at each point of the cycle (subseries)"
SUBSERIES_MEAN, CYCLE_POS = "Average", "Position in the cycle"
BREAK_LINE = "Structural break (CUSUM test): statistic {stat:.2f}, p = {p:.3g}. Most likely shift near {at}."
BREAK_NONE = "Structural break (CUSUM test): statistic {stat:.2f}, p = {p:.3g}. No clear shift."
OUTLIER_LINE = "Unusual points (outliers): {n}; {treatment}."
CARDS_TITLE = "Model cards"
CARDS_COLS = {"title": "Approach", "model": "Fitted as", "settings": "Settings", "aicc": "AICc", "fit_seconds": "Fit time (s)",
              "cv_mase": "CV MASE", "status": "Status"}
CV_TITLE = "Rolling-origin cross-validation"
CV_SUB = ("Each approach was refitted at {folds} earlier cut-off points and scored on what happened next. MASE below 1 "
          "beats the seasonal-naive rule; bias is the average signed error.")
CV_COLS = {"model": "Approach", "n": "Points scored", "mae": "MAE", "rmse": "RMSE", "mase": "MASE", "bias": "Bias",
           "coverage80": "80% range coverage", "dm_p": "DM p vs seasonal naive"}
HORIZON_TITLE = "Error by how far ahead (MASE by step)"
STEP_AXIS, MASE_ONE = "Steps ahead", "MASE = 1 (in-sample seasonal-naive error)"
DM_NOTE = ("Diebold–Mariano test: a small p (below 0.05) means the approach's errors differ from seasonal naive's by more "
           "than chance.")
RESID_TITLE = "One-step errors of the chosen approach (residuals)"
FOLD_AXIS, ERROR_AXIS = "Cut-off point", "Error (relative)"
QQ_TITLE, QQ_X, QQ_Y = "Normal Q–Q plot of the errors", "Normal quantile", "Error quantile"
LJUNG_LINE = "Ljung–Box p = {p:.3f} ({word}). Errors that still carry a pattern mean the approach missed something."
LJUNG_OK, LJUNG_BAD = "no pattern left", "a pattern is left"
COVERAGE_TITLE = "Calibrated ranges: promised vs real coverage"
NOMINAL, REAL = "Promised", "Real"
COVERAGE_LINE = ("Conformal calibration on {folds} scored cut-off points ({pts} values): the 80% range held {cov:.0%} of the "
                 "real values (before calibration: {boot:.0%}). Interval score {score:.2f} (before {score_b:.2f}; lower is better).")
COVERAGE_THIN = "Only {folds} cut-off point(s) could be scored for this series, so its coverage figure is rough."
RESID_FEW = ("Only {n} one-step errors exist for this series (few cut-off points), too few for a Q–Q plot or a "
             "Ljung–Box test.")
HORIZON_NOTE = "Shown: the five approaches with the smallest overall MASE, the chosen one and seasonal naive (all are in the table above)."
