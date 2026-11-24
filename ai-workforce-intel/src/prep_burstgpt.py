"""BurstGPT: per-request Azure OpenAI trace -> hourly and daily token series.

Key facts handled here (checked on the real file):
- `Timestamp` is SECONDS SINCE THE START OF THE TRACE, not a calendar date.
  We therefore index time as hour_index / day_index and expose
  `day_of_cycle` (0-6). Which index is Monday is inferred from the weekly
  pattern and reported, never assumed.
- Failed requests have Response tokens == 0. They are kept, flagged, and
  counted separately (failure rate is an anomaly-detection target).

Outputs (data/processed/):
  burstgpt_requests_clean   one row per request (compact dtypes)
  burstgpt_hourly           hour x model x log_type (long format)
  burstgpt_daily            day x model x log_type (long format)
  burstgpt_daily_wide       one row per day, one column per segment (modelling-ready)
  burstgpt_hourly_total     one row per hour, totals + peak requests/minute
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, FIGURES, save, log_quality, adf_summary  # noqa: E402

COLS = {"Timestamp": "t_sec", "Model": "model", "Request tokens": "request_tokens",
        "Response tokens": "response_tokens", "Total tokens": "total_tokens", "Log Type": "log_type"}


def load() -> pd.DataFrame:
    files = sorted((RAW / "burstgpt").glob("BurstGPT_[0-9].csv"))
    if not files:
        raise FileNotFoundError("No BurstGPT_*.csv in data/raw/burstgpt - run download.py first")
    parts, offset = [], 0
    for f in files:
        d = pd.read_csv(f).rename(columns=COLS)
        # If a later file restarts its clock, shift it to follow the previous one.
        if parts and d["t_sec"].min() < offset:
            d["t_sec"] += offset
            log_quality("BurstGPT", **{f"{f.name} clock": f"restarted; shifted by {offset} s"})
        offset = int(d["t_sec"].max()) + 1
        d["source_file"] = f.name
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def clean(d: pd.DataFrame) -> pd.DataFrame:
    n0 = len(d)
    d = d.dropna(subset=["t_sec", "model", "log_type"])
    d = d[(d["request_tokens"] >= 0) & (d["response_tokens"] >= 0)]
    d["log_type"] = d["log_type"].str.replace(" log", "", regex=False).str.lower()  # api / conversation
    d["model"] = d["model"].str.strip()
    d["failed"] = (d["response_tokens"] == 0).astype("int8")
    # Total tokens should equal request + response; keep the recomputed value.
    mismatch = int((d["total_tokens"] != d["request_tokens"] + d["response_tokens"]).sum())
    d["total_tokens"] = d["request_tokens"] + d["response_tokens"]
    # Exact duplicate rows are NOT removed: in a request log, identical requests in the
    # same second are real traffic (e.g. batched API calls). We only report the count.
    dup_rows = int(d.duplicated().sum())
    d = d.sort_values("t_sec", kind="stable")
    d["minute_index"] = (d["t_sec"] // 60).astype("int64")
    d["hour_index"] = (d["t_sec"] // 3600).astype("int64")
    d["day_index"] = (d["t_sec"] // 86400).astype("int64")
    for c in ("model", "log_type"):
        d[c] = d[c].astype("category")
    log_quality("BurstGPT",
                files=sorted(d["source_file"].unique().tolist()),
                rows_raw=n0, rows_clean=len(d),
                span_days=round(d["t_sec"].max() / 86400, 1),
                time_axis="relative seconds from trace start (no calendar dates)",
                models=d["model"].value_counts().to_dict(),
                log_types=d["log_type"].value_counts().to_dict(),
                failure_rate=f"{d['failed'].mean():.2%}",
                total_token_mismatches_fixed=mismatch,
                exact_duplicate_rows_kept=dup_rows)
    return d


def aggregate(d: pd.DataFrame, key: str) -> pd.DataFrame:
    g = d.groupby([key, "model", "log_type"], observed=True)
    out = g.agg(requests=("t_sec", "size"),
                request_tokens=("request_tokens", "sum"),
                response_tokens=("response_tokens", "sum"),
                total_tokens=("total_tokens", "sum"),
                failures=("failed", "sum")).reset_index()
    # Fill a complete grid so quiet periods are 0, not missing.
    full = pd.MultiIndex.from_product(
        [range(int(d[key].min()), int(d[key].max()) + 1),
         d["model"].cat.categories, d["log_type"].cat.categories],
        names=[key, "model", "log_type"])
    out = (out.set_index([key, "model", "log_type"]).reindex(full, fill_value=0).reset_index())
    out["segment"] = out["model"].astype(str) + "_" + out["log_type"].astype(str)
    return out


def hourly_totals(d: pd.DataFrame) -> pd.DataFrame:
    per_min = d.groupby("minute_index").size()
    per_min = per_min.reindex(range(per_min.index.min(), per_min.index.max() + 1), fill_value=0)
    peak = per_min.groupby(per_min.index // 60).max().rename("peak_requests_per_min")
    h = d.groupby("hour_index").agg(requests=("t_sec", "size"),
                                     total_tokens=("total_tokens", "sum"),
                                     failures=("failed", "sum"))
    h = h.reindex(range(h.index.min(), h.index.max() + 1), fill_value=0)
    h = h.join(peak).fillna({"peak_requests_per_min": 0}).reset_index()
    h["hour_of_day"] = h["hour_index"] % 24
    h["day_index"] = h["hour_index"] // 24
    h["day_of_cycle"] = h["day_index"] % 7
    h["failure_rate"] = np.where(h["requests"] > 0, h["failures"] / h["requests"], 0.0)
    return h


def infer_weekend(daily_wide: pd.DataFrame) -> dict:
    """Weekend = the two consecutive day_of_cycle values with the lowest mean volume."""
    m = daily_wide.groupby("day_of_cycle")["total_tokens"].mean()
    pairs = {(i, (i + 1) % 7): m[i] + m[(i + 1) % 7] for i in range(7)}
    (a, b), _ = min(pairs.items(), key=lambda kv: kv[1])
    ratio = (m[a] + m[b]) / 2 / m.drop([a, b]).mean()
    return {"likely_weekend_day_of_cycle": [int(a), int(b)],
            "weekend_to_weekday_volume_ratio": round(float(ratio), 2),
            "note": "if the ratio is not clearly < 1, treat weekday alignment as unknown"}


def plots(daily_wide: pd.DataFrame, hourly: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 4))
    for c in [c for c in daily_wide.columns if c.endswith("_tokens") and c != "total_tokens"]:
        ax.plot(daily_wide["day_index"], daily_wide[c] / 1e6, label=c.replace("_total_tokens", ""))
    ax.set(title="BurstGPT daily tokens by model and usage type", xlabel="Day since trace start",
           ylabel="Million tokens")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIGURES / "burstgpt_daily_tokens.png", dpi=150); plt.close(fig)

    heat = hourly.pivot_table(index="day_of_cycle", columns="hour_of_day", values="requests", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(11, 3.5))
    im = ax.imshow(heat, aspect="auto", cmap="Blues")
    ax.set(title="BurstGPT mean requests per hour (day of 7-day cycle x hour)",
           xlabel="Hour of day (trace clock)", ylabel="Day of cycle")
    fig.colorbar(im, ax=ax, label="Requests"); fig.tight_layout()
    fig.savefig(FIGURES / "burstgpt_hour_day_heatmap.png", dpi=150); plt.close(fig)


def run():
    print("BurstGPT")
    d = clean(load())
    save(d.drop(columns=["source_file"]), "burstgpt_requests_clean")

    hourly = aggregate(d, "hour_index"); save(hourly, "burstgpt_hourly")
    daily = aggregate(d, "day_index"); save(daily, "burstgpt_daily")

    wide = daily.pivot_table(index="day_index", columns="segment",
                             values=["total_tokens", "requests"], aggfunc="sum")
    wide.columns = [f"{seg}_{metric}" for metric, seg in wide.columns]
    wide = wide.reset_index()
    tot = d.groupby("day_index").agg(total_tokens=("total_tokens", "sum"), requests=("t_sec", "size"),
                                      failures=("failed", "sum"))
    wide = wide.merge(tot, on="day_index")
    wide["day_of_cycle"] = wide["day_index"] % 7
    # The last day is usually partial - flag it so models can drop it.
    last_sec = d["t_sec"].max() % 86400
    wide["partial_day"] = (wide["day_index"] == wide["day_index"].max()) & (last_sec < 86000)
    save(wide, "burstgpt_daily_wide")

    ht = hourly_totals(d); save(ht, "burstgpt_hourly_total")

    log_quality("BurstGPT", weekly_pattern=infer_weekend(wide[~wide["partial_day"]]),
                adf_daily_total_tokens=adf_summary(wide.loc[~wide["partial_day"], "total_tokens"]),
                adf_hourly_requests=adf_summary(ht["requests"]),
                empty_hours=int((ht["requests"] == 0).sum()))
    plots(wide[~wide["partial_day"]], ht)


if __name__ == "__main__":
    run()
