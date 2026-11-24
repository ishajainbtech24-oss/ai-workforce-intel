"""ARIMA family (syllabus Module 3): ARIMA, SARIMA and SARIMAX with statsmodels' SARIMAX.

The order is chosen ONCE, on the first training window, by AICc over a small explicit grid
(p, q in {0,1,2}; P, Q in {0,1} for seasonal models), with d and D from the Phase 1 handoff.
The grid is capped (24 candidates, 8 with --fast), every fit uses maxiter=50, and a per-driver
time budget (shared by the three order searches) stops the grid early, keeping the best so far.
Only converged fits count; if none converges the order falls back to ARIMA(1, d, 0).

Exogenous variables (SARIMAX):
  daily  - is_weekend (BurstGPT: day_of_cycle 4-5, INFERRED; dated series: Sat/Sun). It is a
           period-7 dummy, so with D=1 at season 7 the seasonal difference would wipe it out;
           SARIMAX then uses D=0 and lets the dummy carry the weekly level shift.
  hourly - Fourier terms (K=3 for period 24 and K=3 for 168) instead of a seasonal order of
           168; they replace seasonal differencing, so D=0.
"""
from __future__ import annotations

import itertools
import logging
import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

import config_phase2 as P2
from tsaf.models.base import Fit, fourier, future_index, is_weekend

log = logging.getLogger(__name__)
EXPLOSIVE = 5.0


def exog_kind(ctx: dict) -> str | None:
    """Which exogenous variable SARIMAX uses for this driver (None = SARIMAX not defined)."""
    return {"daily": "weekend", "hourly": "fourier"}.get(ctx["grain"])


def spec(kind: str, ctx: dict) -> dict:
    """Structure of each ARIMA-family model for this driver (seasonal part, D used, exog)."""
    m, D, d = int(ctx["season"] or 1), int(ctx["D"]), int(ctx["d"])
    if kind == "arima":
        return {"seasonal": False, "m": m, "d": d, "D": 0, "exog": None}
    if kind == "sarima":
        return {"seasonal": True, "m": m, "d": d, "D": D, "exog": None}
    ex = exog_kind(ctx)
    if ex == "fourier":
        return {"seasonal": False, "m": m, "d": d, "D": 0, "exog": ex}
    return {"seasonal": m > 1, "m": m, "d": d, "D": 0 if (ex == "weekend" and m == 7) else D,
            "exog": ex}


def trend_term(d: int, D: int) -> str:
    """Constant when nothing is differenced, drift when only d=1, otherwise none."""
    if d + D == 0:
        return "c"
    return "t" if d == 1 and D == 0 else "n"


def exog(index: pd.Index, ctx: dict, kind: str | None) -> np.ndarray | None:
    """Exogenous matrix for `index` (rows) or None."""
    if kind == "weekend":
        return is_weekend(index, ctx["grain"]).reshape(-1, 1)
    if kind == "fourier":
        return fourier(index, P2.FOURIER).to_numpy()
    return None


def grid(sp: dict, max_candidates: int) -> list[tuple[int, int, int, int]]:
    """(p, q, P, Q) candidates, simplest first, capped."""
    sp_vals = (P2.ARIMA_SP, P2.ARIMA_SQ) if sp["seasonal"] else ((0,), (0,))
    cands = list(itertools.product(P2.ARIMA_P, P2.ARIMA_Q, *sp_vals))
    cands.sort(key=lambda c: (sum(c), c))
    return cands[:max_candidates]


def _orders(sp: dict, c: tuple[int, int, int, int]) -> tuple[tuple, tuple]:
    p, q, P, Q = c
    sorder = (P, sp["D"], Q, sp["m"]) if sp["seasonal"] else (0, 0, 0, 0)
    return (p, sp["d"], q), sorder


def fit_sarimax(y: np.ndarray, x, order, sorder, trend: str):
    """One statsmodels SARIMAX fit with the fixed Phase 2 settings, warnings silenced."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = SARIMAX(y, exog=x, order=order, seasonal_order=sorder, trend=trend,
                      enforce_stationarity=False, enforce_invertibility=False)
        return mod.fit(disp=False, maxiter=P2.ARIMA_MAXITER)


def make_selector(kind: str):
    """`select(train0, ctx) -> params` choosing the order by AICc on the first window."""

    def select(train0: pd.Series, ctx: dict) -> dict:
        sp = spec(kind, ctx)
        y, x = np.asarray(train0, dtype=float), exog(train0.index, ctx, sp["exog"])
        trend = trend_term(sp["d"], sp["D"])
        budget = ctx["arima_budget"]
        best, tried, conv, stopped = None, 0, 0, False
        for c in grid(sp, ctx["arima_max_candidates"]):
            if budget["used"] >= budget["seconds"]:
                stopped = True
                break
            order, sorder = _orders(sp, c)
            t0 = time.time()
            tried += 1
            try:
                res = fit_sarimax(y, x, order, sorder, trend)
                ok = bool(res.mle_retvals.get("converged", False)) and np.isfinite(res.aicc)
            except Exception:  # noqa: BLE001 - a failing candidate is just skipped
                ok = False
            budget["used"] += time.time() - t0
            if ok:
                conv += 1
                if best is None or res.aicc < best[0]:
                    best = (float(res.aicc), order, sorder)
        how = "AICc on first training window"
        if best is None:
            order, sorder = (1, sp["d"], 0), (0, sp["D"], 0, sp["m"]) if sp["seasonal"] else (0, 0, 0, 0)
            best, how = (float("nan"), order, sorder), f"fallback ARIMA(1,{sp['d']},0): no candidate converged"
        out = {"order": list(best[1]), "seasonal_order": list(best[2]), "trend": trend,
               "aicc": best[0], "exog": sp["exog"] or "none", "D_used": sp["D"],
               "candidates_tried": tried, "candidates_converged": conv,
               "grid_stopped_early": stopped, "selection": how}
        if sp["exog"] == "fourier":
            out["fourier_K"] = {str(k): v for k, v in P2.FOURIER.items()}
        if sp["exog"] == "weekend":
            out["is_weekend"] = ("inferred: day_of_cycle 4-5" if not isinstance(train0.index, pd.DatetimeIndex)
                                 else "calendar Saturday/Sunday")
        return out

    select.__name__ = f"select_{kind}"
    return select


def _table(res) -> pd.DataFrame:
    names = list(res.model.param_names)
    return pd.DataFrame({"param": names, "estimate": np.asarray(res.params, dtype=float),
                         "std_err": np.asarray(res.bse, dtype=float),
                         "p_value": np.asarray(res.pvalues, dtype=float)})


def _check_sane(fc: np.ndarray, y: np.ndarray) -> None:
    """Reject non-finite or explosive forecasts (beyond EXPLOSIVE x the training range).

    With enforce_stationarity=False an unconstrained fit can produce an explosive AR part;
    that fold then falls back to ARIMA(1, d, 0) and the fallback is recorded.
    """
    if not np.all(np.isfinite(fc)):
        raise ValueError("non-finite forecast")
    span = float(np.max(y) - np.min(y)) or 1.0
    if np.max(np.abs(fc - y[-1])) > EXPLOSIVE * span:
        raise ValueError(f"explosive forecast (moves more than {EXPLOSIVE}x the training range)")


def fit_arima_family(train: pd.Series, h: int, ctx: dict) -> Fit:
    """Refit with the fixed order from ctx['params']; forecast h steps with future exog."""
    p = ctx["params"]
    kind = None if p["exog"] == "none" else p["exog"]
    y = np.asarray(train, dtype=float)
    x, xf = exog(train.index, ctx, kind), exog(future_index(train.index, h, ctx["grain"]), ctx, kind)
    order, sorder, info = tuple(p["order"]), tuple(p["seasonal_order"]), {}
    try:
        res = fit_sarimax(y, x, order, sorder, p["trend"])
        fc = np.asarray(res.forecast(h, exog=xf), dtype=float)
        _check_sane(fc, y)
    except Exception as exc:  # noqa: BLE001 - one fold falls back, the model keeps going
        order = (1, order[1], 0)
        res = fit_sarimax(y, x, order, sorder, p["trend"])
        fc = np.asarray(res.forecast(h, exog=xf), dtype=float)
        info["fallback"] = f"ARIMA(1,{order[1]},0) ({exc})"
    fitted = np.asarray(res.fittedvalues, dtype=float).copy()
    burn = order[1] + sorder[1] * sorder[3]
    fitted[: max(1, burn + (1 if burn else 0))] = np.nan  # diffuse start: not a real one-step fit
    info["converged"] = bool(res.mle_retvals.get("converged", False))
    return Fit(forecast=fc, insample=fitted, info=info, table=_table(res))
