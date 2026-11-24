"""Optional challengers: Prophet and a small LSTM (syllabus Module 4, deep learning).

Prophet: additive trend + weekly seasonality only. BurstGPT has no calendar dates, so the
day index is mapped onto dates starting at config_phase2.PROPHET_START purely as an index.

LSTM: one layer (hidden 16) + one linear layer of size h, i.e. DIRECT multi-step prediction.
Inputs: the target scaled with the training window's mean and std, plus sin/cos of the cycle
position. Adam, lr 0.01, 30 epochs, batch 32, CPU, torch.manual_seed(42). Off by default.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

import config_phase2 as P2
from tsaf.models.base import Fit, cycle_position


def fit_prophet(train: pd.Series, h: int, ctx: dict) -> Fit:
    """Prophet on an arbitrary daily date index (no yearly or daily seasonality)."""
    for name in ("prophet", "cmdstanpy"):
        logging.getLogger(name).setLevel(logging.ERROR)
    from prophet import Prophet
    ds = pd.date_range(P2.PROPHET_START, periods=len(train) + h, freq="D")
    df = pd.DataFrame({"ds": ds[: len(train)], "y": np.asarray(train, dtype=float)})
    m = Prophet(growth="linear", weekly_seasonality=True, yearly_seasonality=False,
                daily_seasonality=False, interval_width=0.8, seasonality_mode="additive")
    m.fit(df)
    pred = m.predict(pd.DataFrame({"ds": ds}))["yhat"].to_numpy()
    return Fit(forecast=pred[len(train):], insample=pred[: len(train)],
               info={"start_date": P2.PROPHET_START, "date_note": "arbitrary start date, index only"})


def _calendar(index: pd.Index, grain: str) -> np.ndarray:
    pos, period = cycle_position(index, grain)
    return np.column_stack([np.sin(2 * np.pi * pos / period), np.cos(2 * np.pi * pos / period)])


def _windows(z: np.ndarray, cal: np.ndarray, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Sliding (input window, next h targets) pairs."""
    feats = np.column_stack([z, cal])
    n = len(z) - w - h + 1
    if n < 10:
        raise ValueError(f"only {max(n, 0)} LSTM training windows; too few")
    X = np.stack([feats[i:i + w] for i in range(n)])
    Y = np.stack([z[i + w:i + w + h] for i in range(n)])
    return X.astype(np.float32), Y.astype(np.float32)


def fit_lstm(train: pd.Series, h: int, ctx: dict) -> Fit:
    """Train the small LSTM on the training window and predict the next h values directly."""
    import torch
    from torch import nn

    torch.manual_seed(P2.SEED)
    np.random.seed(P2.SEED)
    cfg, grain = P2.LSTM, ctx["grain"]
    w = cfg["window"][grain]
    y = np.asarray(train, dtype=float)
    mu, sd = y.mean(), y.std() or 1.0
    z = (y - mu) / sd
    cal = _calendar(train.index, grain)
    X, Y = _windows(z, cal, w, h)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(input_size=X.shape[2], hidden_size=cfg["hidden"], batch_first=True)
            self.out = nn.Linear(cfg["hidden"], h)

        def forward(self, x):
            o, _ = self.lstm(x)
            return self.out(o[:, -1, :])

    net, loss_fn = Net(), nn.MSELoss()
    opt = torch.optim.Adam(net.parameters(), lr=cfg["lr"])
    Xt, Yt = torch.from_numpy(X), torch.from_numpy(Y)
    gen = torch.Generator().manual_seed(P2.SEED)
    for _ in range(cfg["epochs"]):
        for idx in torch.randperm(len(Xt), generator=gen).split(cfg["batch"]):
            opt.zero_grad()
            loss_fn(net(Xt[idx]), Yt[idx]).backward()
            opt.step()
    net.eval()
    last =np.column_stack([z[-w:], cal[-w:]])[None].astype(np.float32)
    with torch.no_grad():
        fc = net(torch.from_numpy(last)).numpy()[0] * sd + mu
        one_step = net(Xt).numpy()[:, 0] * sd + mu
    ins = np.full(len(y), np.nan)
    ins[w:w + len(one_step)] = one_step
    return Fit(forecast=fc, insample=ins, info={"window": w, "epochs": cfg["epochs"],
                                                "hidden": cfg["hidden"], "train_windows": len(X)})
