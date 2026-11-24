"""Serial and cross dependence (syllabus Module 3: ACF, PACF and cross-correlation).

Sample ACF/PACF with approximate 95% bands (+-1.96/sqrt(n)) for the original and the
differenced series, and the cross-correlation between two series over lags -L..L.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, pacf


def n_lags(n: int) -> int:
    """Lags shown: min(40, n // 3)."""
    return max(1, min(40, n // 3))


def acf_pacf(x: pd.Series) -> dict:
    """ACF and PACF (lag 0 included) plus the 95% band half-width."""
    x = x.dropna().astype(float)
    k = n_lags(len(x))
    return {"lags": np.arange(k + 1), "acf": acf(x, nlags=k, fft=True),
            "pacf": pacf(x, nlags=k, method="ywm"), "band": 1.96 / np.sqrt(len(x)), "n": len(x)}


def cross_correlation(x: pd.Series, y: pd.Series, max_lag: int = 10) -> pd.DataFrame:
    """corr(x_t, y_{t+k}) for k in -max_lag..max_lag (positive k: x leads y)."""
    x, y = x.astype(float), y.astype(float)
    rows = []
    for k in range(-max_lag, max_lag + 1):
        pair = pd.concat([x, y.shift(-k)], axis=1).dropna()
        r = float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1]) if len(pair) > 2 else np.nan
        rows.append({"lag": k, "ccf": r, "n_pairs": len(pair)})
    out = pd.DataFrame(rows)
    out["band"] = 1.96 / np.sqrt(len(x))
    return out
