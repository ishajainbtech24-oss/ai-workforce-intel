"""Phase 4 settings: Monte Carlo size, horizons, scenarios, sensitivity and output layout."""
from __future__ import annotations

from config import ROOT

OUT_DIR = ROOT / "outputs" / "phase4"
PHASE3_DIR = ROOT / "outputs" / "phase3"
EXAMPLE_INPUTS = ROOT / "config" / "example_company.json"

N_DRAWS, N_DRAWS_FAST = 5000, 1000
SEED = 42
HORIZON_RANGE = (6, 24)
MULTIPLIERS_DEFAULT = (1.0, 1.5, 2.0)  # overridden by inputs_for_phase4.json when present

# Which scenario_tables.csv row feeds each scenario (the first one found is used).
SCENARIO_ROWS = {"downside": ["task_time_change_with_ai", "task_time_change_with_ai_naive"],
                 "expected": ["time_saved_share_of_work_hours"],
                 "optimistic": ["time_saved_share_of_work_hours"]}
SCENARIOS = ("downside", "expected", "optimistic")

# Input uncertainty inside the Monte Carlo (workstream D). Each draw multiplies the entered value by a PERT draw
# (low, most likely, high), so a range is applied to any company's inputs, not only the example. Shares stay in
# [0, 1]. Pass input_spread={} to run_engine for the old fixed-input behaviour.
INPUT_SPREAD = {"time_saved": (0.5, 1.0, 1.6),               # how much time AI saves (the outlook's figure)
                "realisation_rate": (0.7, 1.0, 1.3),          # share of saved time that becomes value
                "adoption_target": (0.75, 1.0, 1.15),         # how many people end up using it
                "training_hours_per_new_user": (0.75, 1.0, 1.5)}

LINES = ("token_expenditure", "hosting", "enablement", "integration")
LINE_TYPE = {"token_expenditure": "Forecast-driven", "hosting": "Forecast-driven",
             "enablement": "Estimate", "integration": "Estimate", "value": "Projection"}
LINE_LABEL = {"token_expenditure": "Token expenditure", "hosting": "Infrastructure / hosting",
              "enablement": "Workforce enablement", "integration": "Integration", "value": "Business outcomes (value)"}

SENSITIVITY_INPUTS = ("employees", "adoption_target", "tokens_per_active_user_per_month",
                      "training_hours_per_new_user", "engineering_hours_build", "base_wages",
                      "realisation_rate", "time_saved_parameter")
SENSITIVITY_STEP = 0.20
SAMPLE_DRAWS = 500
FAN_PATHS = 30
