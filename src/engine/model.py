"""Cost and value model: one function per line item, vectorised over draws (rows) and months (columns).

Months are 1..T. A(m) is the adoption share, U(m) = employees x A(m) the active users,
N(m) = max(U(m) - U(m-1), 0) the new users with U(0) = employees x adoption_start.
Value uses adoption cohorts: a cohort adopted in month c contributes ramp(m - c) =
min((m - c) / benefit_lag_months, 1) of its full saving in month m (computed with a convolution,
no loop over draws). Break-even is the first month whose cumulative net is at or above 0.
"""
from __future__ import annotations

import numpy as np


def adoption(inputs: dict, T: int) -> tuple[np.ndarray, np.ndarray, float]:
    """(U, N, U0): active users and new users for months 1..T, and users at month 0."""
    s, t, r = inputs["adoption_start"], inputs["adoption_target"], inputs["ramp_months"]
    m = np.arange(1, T + 1, dtype=float)
    if inputs["ramp_shape"] == "logistic":
        k = 10.0 / r
        L = lambda x: 1.0 / (1.0 + np.exp(-k * (x - r / 2.0)))  # noqa: E731
        prog = np.clip((L(m) - L(0.0)) / (L(float(r)) - L(0.0)), 0.0, 1.0)
        prog[m >= r] = 1.0
    else:
        prog = np.minimum(m / r, 1.0)
    A = s + (t - s) * prog
    U0 = inputs["employees"] * s
    U = inputs["employees"] * A
    N = np.maximum(np.diff(np.r_[U0, U]), 0.0)
    return U, N, float(U0)


def benefit_ramp(lag: int, T: int) -> np.ndarray:
    """ramp(age) for ages 0..T: min(age / lag, 1); lag 0 gives full value immediately."""
    age = np.arange(0, T + 1, dtype=float)
    return np.ones(T + 1) if lag <= 0 else np.minimum(age / lag, 1.0)


def effective_users(U0: float, N: np.ndarray, lag: int) -> np.ndarray:
    """Users weighted by their benefit ramp, months 1..T (cohort convolution)."""
    T = len(N)
    cohorts = np.r_[U0, N]                       # adopted in month 0 (pilot) and months 1..T
    full = np.convolve(cohorts, benefit_ramp(lag, T))[: T + 1]
    return full[1:]


def effective_users_loop(U0: float, N: np.ndarray, lag: int) -> np.ndarray:
    """Slow reference version of effective_users (used in the tests)."""
    T, ramp = len(N), benefit_ramp(lag, len(N))
    cohorts = [(0, U0)] + [(c + 1, n) for c, n in enumerate(N)]
    out = np.zeros(T)
    for m in range(1, T + 1):
        out[m - 1] = sum(n * ramp[m - c] for c, n in cohorts if c <= m)
    return out


def token_expenditure(U: np.ndarray, tokens_per_user: float, demand: np.ndarray, price: np.ndarray) -> np.ndarray:
    """Active users x tokens per user x demand factor / 1e6 x price per million tokens."""
    return U[None, :] * tokens_per_user * demand / 1e6 * price


def hosting(base_cost: float, ppi_ratio: np.ndarray) -> np.ndarray:
    """Base monthly hosting cost moved with the PPI hosting index."""
    return base_cost * ppi_ratio


def enablement(inputs: dict, U: np.ndarray, N: np.ndarray, staff_wage: np.ndarray) -> np.ndarray:
    """(new users x training hours + users x refresher hours / 12) x staff wage + fixed monthly cost."""
    hours = N * inputs["training_hours_per_new_user"] + U * inputs["refresher_hours_per_user_per_year"] / 12.0
    return hours[None, :] * staff_wage + inputs["fixed_enablement_cost_per_month"]


def integration_hours(inputs: dict, T: int) -> np.ndarray:
    """Engineering hours per month: build spread over build_months, then maintenance."""
    m = np.arange(1, T + 1)
    build = inputs["engineering_hours_build"]
    in_build = m <= inputs["build_months"]
    hours = np.where(in_build, build / inputs["build_months"], 0.0)
    maint = inputs["maintenance_share_per_month"] * build
    paying = ~in_build | bool(inputs.get("maintenance_during_build", False))
    return hours + np.where(paying, maint, 0.0)


def integration(inputs: dict, T: int, engineer_wage: np.ndarray) -> np.ndarray:
    return integration_hours(inputs, T)[None, :] * engineer_wage


def value(inputs: dict, E: np.ndarray, time_saved_fraction: float, staff_wage: np.ndarray) -> np.ndarray:
    """Effective users x work hours x time saved x realisation rate x staff wage (a projection)."""
    per_user = inputs["work_hours_per_user_per_month"] * time_saved_fraction * inputs["realisation_rate"]
    return E[None, :] * per_user * staff_wage


def break_even(cum_net: np.ndarray) -> np.ndarray:
    """First month (1-based) with cumulative net >= 0, per draw; NaN if none within T."""
    hit = cum_net >= 0
    first = np.argmax(hit, axis=1).astype(float) + 1.0
    first[~hit.any(axis=1)] = np.nan
    return first
