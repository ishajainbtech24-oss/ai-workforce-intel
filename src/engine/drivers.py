"""Forecast paths of the engine's drivers, converted to monthly arrays (rows: point + 200 paths).

Every driver becomes `paths[row, month]` for months 1..T, where row 0 is the point forecast
(sample_id -1) and rows 1..200 are the simulated paths. Months beyond a driver's forecast horizon
are extrapolated FLAT from its last forecast value and counted.

- token_demand: the BurstGPT 30-day run-rate, used only as a unit-free demand factor
  f = run_rate / median(simulated run-rates); BurstGPT is one provider's trace, so only its
  relative variation is used. It covers month 1; months 2..T are flat.
- wages: ECI index ratio ECI(m) / ECI(0), ECI(0) = last observed value; month m sits m/3 quarters
  ahead and is linearly interpolated between quarterly forecast points (a cost-engine step).
- hosting: PPI index ratio PPI(m) / PPI(0), PPI(0) = last observed value.
- token_price: Epoch blended USD per million tokens (optional); without it a flat fixed price
  from the inputs is used and flagged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config
from tsaf.loaders import load_driver

log = logging.getLogger(__name__)


class MissingDriver(RuntimeError):
    """A required engine role has no forecast file."""


@dataclass
class Driver:
    """Monthly values of one driver: row 0 = point forecast, rows 1.. = simulated paths."""
    role: str
    name: str
    values: np.ndarray
    covered_months: int
    T: int
    used_fallback: bool = False
    note: str = ""

    @property
    def extrapolated_months(self) -> int:
        return max(self.T - self.covered_months, 0)

    @property
    def point(self) -> np.ndarray:
        return self.values[0]

    @property
    def paths(self) -> np.ndarray:
        return self.values[1:]


@dataclass
class DriverPaths:
    """All engine drivers for horizon T (load once, reuse for many engine runs)."""
    T: int
    drivers: dict[str, Driver] = field(default_factory=dict)

    def __getitem__(self, role: str) -> Driver:
        return self.drivers[role]


def _flat_extend(arr: np.ndarray, T: int) -> np.ndarray:
    """Columns 1..T: keep the first T columns, repeat the last column after that."""
    if arr.shape[1] >= T:
        return arr[:, :T]
    return np.hstack([arr, np.repeat(arr[:, -1:], T - arr.shape[1], axis=1)])


def _wide(path: Path) -> np.ndarray:
    """Standard Phase 3 table -> array (point + paths, periods), point first."""
    t = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    w = t.pivot(index="sample_id", columns="period_index", values="value").sort_index()
    return w.to_numpy(dtype=float)  # sample_id -1 sorts first


def last_observed(driver: str, data_dir: Path) -> float:
    """Last observed value of a driver's processed series (read, never assumed)."""
    return float(load_driver(config.driver_by_name(driver), data_dir).series.iloc[-1])


def token_demand(phase3: Path, spec: dict, T: int) -> Driver:
    rr = pd.read_csv(phase3 / spec["file"])
    rr = rr[rr["driver"] == spec["driver"]].sort_values("sample_id")
    v = rr["run_rate_30d"].to_numpy(dtype=float)
    f = v / np.median(v[1:])
    return Driver("token_demand", spec["driver"], np.repeat(f[:, None], T, axis=1), 1, T,
                  note="demand factor = 30-day run-rate / median simulated run-rate (relative variation only)")


def wages(phase3: Path, spec: dict, T: int, data_dir: Path) -> Driver:
    q = _wide(phase3 / spec["file"])
    e0 = last_observed(spec["driver"], data_dir)
    pos = np.arange(1, T + 1) / 3.0  # quarters ahead
    xs = np.arange(0, q.shape[1] + 1)
    vals = np.vstack([np.interp(pos, xs, np.r_[e0, row]) for row in q]) / e0
    return Driver("wages", spec["driver"], vals, min(3 * q.shape[1], T), T,
                  note=f"ECI(m)/ECI(0), ECI(0) = {e0:g} (last observed); monthly by linear interpolation")


def hosting(phase3: Path, spec: dict, T: int, data_dir: Path) -> Driver:
    m = _wide(phase3 / spec["file"])
    p0 = last_observed(spec["driver"], data_dir)
    return Driver("hosting", spec["driver"], _flat_extend(m, T) / p0, min(m.shape[1], T), T,
                  note=f"PPI(m)/PPI(0), PPI(0) = {p0:g} (last observed)")


def token_price(phase3: Path, spec: dict, T: int, n_rows: int) -> Driver:
    path = phase3 / spec["file"]
    if path.exists():
        m = _wide(path)
        return Driver("token_price", spec["driver"], _flat_extend(m, T), min(m.shape[1], T), T,
                      note="Epoch blended price forecast (USD per million tokens)")
    log.warning("token_price: %s not found; using the flat fixed_token_price_per_mtok input (fallback)", path.name)
    return Driver("token_price", "fixed_token_price_per_mtok", np.ones((n_rows, T)), T, T, used_fallback=True,
                  note="no Epoch price forecast: flat fixed_token_price_per_mtok from the inputs (an estimate)")


def load_drivers(T: int, phase3: Path, data_dir: Path, roles: dict | None = None) -> DriverPaths:
    """Load every engine role for horizon T; MissingDriver names any missing required file."""
    roles = roles or config.ENGINE_DRIVERS
    for role, spec in roles.items():
        if spec["required"] and not (phase3 / spec["file"]).exists():
            raise MissingDriver(f"required engine driver '{role}' is missing: {phase3 / spec['file']} not found")
    dp = DriverPaths(T=T)
    dp.drivers["token_demand"] = token_demand(phase3, roles["token_demand"], T)
    dp.drivers["wages"] = wages(phase3, roles["wages"], T, data_dir)
    dp.drivers["hosting"] = hosting(phase3, roles["hosting"], T, data_dir)
    n_rows = dp.drivers["wages"].values.shape[0]
    dp.drivers["token_price"] = token_price(phase3, roles["token_price"], T, n_rows)
    return dp
