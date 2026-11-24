"""Epoch AI LLM price data -> monthly price-per-token series.

Epoch's export columns change between releases, so this script detects the
date and price columns by name and prints what it chose. If detection fails,
pass the column names explicitly:

    python src/prep_epoch.py --date-col "Release date" \
        --input-col "Input price ($/1M tokens)" --output-col "Output price ($/1M tokens)"

Outputs (data/processed/):
  epoch_prices_models    one row per model with a usable price
  epoch_prices_monthly   monthly cheapest and median blended price per 1M tokens

Blended price = 0.83 x input + 0.17 x output. The 0.83 is measured: input
(request) tokens are 83% of all tokens in BurstGPT_1. Re-check it if you add
more BurstGPT months or switch to WildChat's ratio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, save, log_quality  # noqa: E402

INPUT_WEIGHT = 0.83  # share of input tokens measured in BurstGPT_1


def pick(cols, *must, avoid=()):
    for c in cols:
        lc = c.lower()
        if all(m in lc for m in must) and not any(a in lc for a in avoid):
            return c
    return None


def run(date_col=None, input_col=None, output_col=None, name_col=None):
    print("Epoch AI prices")
    files = sorted((RAW / "epoch").glob("*.csv"))
    if not files:
        log_quality("Epoch AI", status="SKIPPED - put the CSV export in data/raw/epoch/ (see README)")
        raise FileNotFoundError("no CSV in data/raw/epoch (manual download, see README)")
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    cols = list(d.columns)
    date_col = date_col or pick(cols, "release") or pick(cols, "date")
    input_col = input_col or pick(cols, "input", "price") or pick(cols, "input", "$")
    output_col = output_col or pick(cols, "output", "price") or pick(cols, "output", "$")
    name_col = name_col or pick(cols, "model") or pick(cols, "name") or cols[0]
    chosen = dict(date=date_col, input=input_col, output=output_col, name=name_col)
    print(f"  columns used: {chosen}")
    if not (date_col and input_col and output_col):
        raise ValueError(f"Could not detect columns, pass them explicitly. Available: {cols}")

    m = pd.DataFrame({
        "model": d[name_col].astype(str),
        "date": pd.to_datetime(d[date_col], errors="coerce"),
        "input_usd_per_mtok": pd.to_numeric(d[input_col].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"),
        "output_usd_per_mtok": pd.to_numeric(d[output_col].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"),
    })
    n0 = len(m)
    m = m.dropna().query("input_usd_per_mtok > 0 and output_usd_per_mtok > 0").drop_duplicates()
    m["blended_usd_per_mtok"] = INPUT_WEIGHT * m["input_usd_per_mtok"] + (1 - INPUT_WEIGHT) * m["output_usd_per_mtok"]
    m["log_blended"] = np.log(m["blended_usd_per_mtok"])
    save(m.sort_values("date"), "epoch_prices_models")

    m["month"] = m["date"].dt.to_period("M").dt.to_timestamp()
    monthly = m.groupby("month").agg(models_released=("model", "size"),
                                     min_blended=("blended_usd_per_mtok", "min"),
                                     median_blended=("blended_usd_per_mtok", "median")).reset_index()
    # Running cheapest price available so far (a price frontier, irregular -> monthly).
    full = pd.DataFrame({"month": pd.date_range(monthly.month.min(), monthly.month.max(), freq="MS")})
    monthly = full.merge(monthly, on="month", how="left")
    monthly["models_released"] = monthly["models_released"].fillna(0).astype(int)
    monthly["cheapest_available"] = monthly["min_blended"].cummin().ffill()
    save(monthly, "epoch_prices_monthly")
    log_quality("Epoch AI", columns_used=chosen, rows_raw=n0, models_with_price=len(m),
                period=f"{m.date.min().date()} to {m.date.max().date()}",
                months_without_new_model=int((monthly.models_released == 0).sum()),
                caveat="irregular release dates; fit a log-linear trend, not SARIMA")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-col"); ap.add_argument("--input-col"); ap.add_argument("--output-col")
    ap.add_argument("--name-col")
    a = ap.parse_args()
    run(a.date_col, a.input_col, a.output_col, a.name_col)
