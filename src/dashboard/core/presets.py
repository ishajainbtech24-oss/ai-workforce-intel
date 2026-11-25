"""Company presets. The mid-size preset is the example company (config/example_company.json); small and enterprise
scale its people- and size-driven figures. All three are made-up illustrations, labelled as such on screen.
Money is in US dollars here (the engine's unit) and shown in rupees."""
from __future__ import annotations

# overrides applied to the example company's inputs
PRESET_INPUTS = {
    "example": {},
    "small": {"employees": 50, "engineering_hours_build": 250.0, "base_monthly_hosting_cost": 500.0,
              "fixed_enablement_cost_per_month": 800.0, "ramp_months": 4},
    "enterprise": {"employees": 5000, "engineering_hours_build": 4000.0, "base_monthly_hosting_cost": 12000.0,
                   "fixed_enablement_cost_per_month": 15000.0, "ramp_months": 9},
}


def inputs_for(preset: str, base: dict) -> dict:
    """The engine inputs of a preset, built on the example company's (`base`)."""
    return {**base, **PRESET_INPUTS.get(preset, {})}
