"""Machine-learning forecasters (syllabus Module 4): Ridge, Random Forest, XGBoost.

Features are built from PAST values only (every one goes through `shift`): lags, rolling
mean/std of the shifted series, sin/cos of the day of week (daily) or hour of day (hourly),
is_weekend (daily; INFERRED for BurstGPT), a trend index, and optionally an extra series
(requests) lagged by at least the longest horizon. Multi-step forecasts are RECURSIVE: predict
one step, append it to the history, rebuild the features, repeat h times.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import config_phase2 as P2
from optional import has_xgboost
from tsaf.models.base import Fit, cycle_position, future_index, is_weekend


@dataclass(frozen=True)
class FeatureSpec:
    """Which features to build."""
    grain: str
    lags: tuple[int, ...]
    roll: int
    weekend: bool
    extra_lag: int | None = None  # lag of the extra series (None = not used)

    @property
    def tail(self) -> int:
        """History length needed to build the features of one new row."""
        return max(max(self.lags), self.roll, self.extra_lag or 0) + 2


def feature_spec(ctx: dict, with_extra: bool = False) -> FeatureSpec:
    g = ctx["grain"]
    extra = ctx.get("extra")
    return FeatureSpec(grain=g, lags=P2.ML_LAGS[g], roll=P2.ML_ROLL[g], weekend=(g == "daily"),
                       extra_lag=extra["lag"] if (with_extra and extra) else None)


def build_features(y: pd.Series, spec: FeatureSpec, offset: int = 0,
                   extra: pd.Series | None = None) -> pd.DataFrame:
    """Feature rows for every label of `y`; row t uses only y[<t] (and extra[<= t - lag]).

    `offset` is the position of y's first value in the full series (for the trend index).
    """
    v = pd.Series(np.asarray(y, dtype=float), index=y.index)
    X = pd.DataFrame(index=y.index)
    for k in spec.lags:
        X[f"lag_{k}"] = v.shift(k)
    past = v.shift(1)
    X[f"roll_mean_{spec.roll}"] = past.rolling(spec.roll).mean()
    X[f"roll_std_{spec.roll}"] = past.rolling(spec.roll).std()
    pos, period = cycle_position(y.index, spec.grain)
    X["cycle_sin"], X["cycle_cos"] = np.sin(2 * np.pi * pos / period), np.cos(2 * np.pi * pos / period)
    if spec.weekend:
        X["is_weekend"] = is_weekend(y.index, spec.grain)
    X["trend"] = np.arange(len(y), dtype=float) + offset
    if spec.extra_lag is not None:
        if extra is None:
            raise ValueError("extra series required by the feature spec")
        X[f"extra_lag_{spec.extra_lag}"] = extra.reindex(y.index).shift(spec.extra_lag).to_numpy()
    return X


def make_estimator(kind: str, params: dict, n_trees: int):
    """A fresh scikit-learn / xgboost regressor with the fixed Phase 2 settings (seed 42)."""
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=params.get("alpha", 1.0)))
    if kind == "random_forest":
        return RandomForestRegressor(n_estimators=n_trees, max_depth=P2.RF_MAX_DEPTH,
                                     random_state=P2.SEED, n_jobs=P2.TREE_JOBS)
    if kind == "xgboost" and has_xgboost():
        from xgboost import XGBRegressor
        return XGBRegressor(n_estimators=n_trees, max_depth=P2.XGB_MAX_DEPTH, learning_rate=P2.XGB_LR,
                            random_state=P2.SEED, n_jobs=P2.TREE_JOBS, verbosity=0)
    if kind in ("xgboost", "hist_gradient_boosting"):
        return HistGradientBoostingRegressor(max_iter=n_trees, max_depth=P2.XGB_MAX_DEPTH,
                                             learning_rate=P2.XGB_LR, random_state=P2.SEED)
    raise KeyError(kind)


def _extra_until(ctx: dict, train: pd.Series) -> pd.Series | None:
    """The extra series cut at the training end, so a future value can never be read."""
    ex = ctx.get("extra")
    return None if ex is None else ex["series"].loc[: train.index[-1]]


def recursive_forecast(model, train: pd.Series, h: int, spec: FeatureSpec, grain: str,
                       extra: pd.Series | None = None) -> np.ndarray:
    """Predict one step, append it to the history, rebuild the features; repeat h times."""
    hist = pd.Series(np.asarray(train, dtype=float), index=train.index)
    labels = future_index(train.index, h, grain)
    preds = np.empty(h)
    for k in range(h):
        ext = pd.concat([hist, pd.Series([np.nan], index=labels[k:k + 1])])
        tail = ext.iloc[-spec.tail:]
        row = build_features(tail, spec, offset=len(ext) - len(tail), extra=extra).iloc[[-1]]
        if row.isna().any(axis=None):
            raise ValueError(f"step {k + 1}: feature row has NaN ({list(row.columns[row.isna().iloc[0]])})")
        preds[k] = float(np.asarray(model.predict(row)).reshape(-1)[0])
        ext.iloc[-1] = preds[k]
        hist = ext
    return preds


def _xy(train: pd.Series, spec: FeatureSpec, extra) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    X = build_features(train, spec, extra=extra)
    ok = X.notna().all(axis=1).to_numpy()
    if ok.sum() < 10:
        raise ValueError(f"only {int(ok.sum())} complete feature rows; too few to train")
    return X[ok], pd.Series(np.asarray(train, dtype=float)[ok], index=X.index[ok]), X


def make_ml(kind: str, with_extra: bool = False):
    """`fit(train, h, ctx)` for one ML model (optionally with the extra series as a feature)."""

    def fit(train: pd.Series, h: int, ctx: dict) -> Fit:
        spec = feature_spec(ctx, with_extra)
        extra = _extra_until(ctx, train) if with_extra else None
        Xtr, ytr, Xall = _xy(train, spec, extra)
        model = make_estimator(kind, ctx.get("params", {}), ctx["n_trees"])
        model.fit(Xtr, ytr)
        if "n_jobs" in model.get_params():
            # Recursive forecasting predicts one row at a time: thread start-up would dominate.
            model.set_params(n_jobs=1)
        ins =np.full(len(train), np.nan)
        ok = Xall.notna().all(axis=1).to_numpy()
        ins[ok] = np.asarray(model.predict(Xall[ok])).reshape(-1)
        info = {"n_train_rows": int(len(Xtr)), "features": ",".join(Xtr.columns)}
        imp = getattr(model, "feature_importances_", None)
        table = (pd.DataFrame({"feature": Xtr.columns, "importance": np.asarray(imp, dtype=float)})
                 if imp is not None else None)
        fc = recursive_forecast(model, train, h, spec, ctx["grain"], extra)
        return Fit(forecast=fc, insample=ins, info=info, table=table)

    fit.__name__ = f"fit_{kind}{'_extra' if with_extra else ''}"
    return fit


def select_ridge_alpha(train0: pd.Series, ctx: dict, with_extra: bool = False) -> dict:
    """Ridge alpha from RIDGE_ALPHAS by one-step MAE on the last 20% of the first window."""
    spec = feature_spec(ctx, with_extra)
    Xtr, ytr, _ = _xy(train0, spec, _extra_until(ctx, train0) if with_extra else None)
    v = max(1, int(round(P2.VALIDATION_SHARE * len(Xtr))))
    scores = {}
    for a in P2.RIDGE_ALPHAS:
        m = make_estimator("ridge", {"alpha": a}, 0).fit(Xtr.iloc[:-v], ytr.iloc[:-v])
        scores[a] = float(np.mean(np.abs(ytr.iloc[-v:].to_numpy() - m.predict(Xtr.iloc[-v:]))))
    best = min(scores, key=lambda a: (scores[a], a))
    return {"alpha": best, "validation_mae": scores[best], "validation_rows": v}


def tree_params(kind: str, ctx: dict) -> dict:
    """The fixed tree settings, recorded in params.csv."""
    if kind == "random_forest":
        return {"n_estimators": ctx["n_trees"], "max_depth": P2.RF_MAX_DEPTH, "random_state": P2.SEED}
    backend = "xgboost" if has_xgboost() else "sklearn HistGradientBoostingRegressor (xgboost missing)"
    return {"n_estimators": ctx["n_trees"], "max_depth": P2.XGB_MAX_DEPTH, "learning_rate": P2.XGB_LR,
            "random_state": P2.SEED, "backend": backend}
