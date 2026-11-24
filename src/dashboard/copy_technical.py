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
