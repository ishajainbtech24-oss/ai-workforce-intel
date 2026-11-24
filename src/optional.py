"""Optional packages for Phase 2 (xgboost, prophet, torch), detected once and cached.

A missing optional package never stops the run: xgboost falls back to scikit-learn's
HistGradientBoostingRegressor, and Prophet / LSTM are recorded as "skipped (not installed)".
"""
from __future__ import annotations

import importlib
from functools import lru_cache


@lru_cache(maxsize=None)
def _has(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:  # noqa: BLE001 - ImportError, or a broken install raising something else
        return False


def has_xgboost() -> bool:
    """True when `import xgboost` works."""
    return _has("xgboost")


def has_prophet() -> bool:
    """True when `import prophet` works."""
    return _has("prophet")


def has_torch() -> bool:
    """True when `import torch` works."""
    return _has("torch")
