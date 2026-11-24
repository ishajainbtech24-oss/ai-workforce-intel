"""FRED / BLS series: wages (ECI), cloud prices (PPI) and the GenAI Adoption Tracker.

Outputs (data/processed/):
  fred_long              every series, long format (series_id, date, value, frequency)
  eci_quarterly          ECI wages SA + NSA, quarterly (SARIMA s=4 input)
  eci_monthly            ECI interpolated to months (for the monthly cost engine only)
  ppi_hosting_monthly    PPI hosting series, monthly
  genai_tracker          national time-saved and hours-assisted shares, quarterly
  genai_timesaved_panel  occupation/industry time-saved panel (pooled outcome model)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, save, log_quality, adf_summary  # noqa: E402
from download import FRED_SERIES  # noqa: E402


def read_series(sid: str) -> pd.DataFrame | None:
    f = RAW / "fred" / f"{sid}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    date_col = d.columns[0]          # 'observation_date' (or 'DATE' in older exports)
    d = d.rename(columns={date_col: "date", d.columns[1]: "value"})
    d["date"] = pd.to_datetime(d["date"])
    d["value"] = pd.to_numeric(d["value"], errors="coerce")  # FRED marks gaps with '.'
    d["series_id"] = sid
    d["description"] = FRED_SERIES.get(sid, "")
    return d


def run():
    print("FRED / BLS")
    frames, missing = [], []
    for sid in FRED_SERIES:
        d = read_series(sid)
        (frames if d is not None else missing).append(d if d is not None else sid)
    if not frames:
        raise FileNotFoundError("No FRED CSVs in data/raw/fred - run download.py --only fred")
    long = pd.concat(frames, ignore_index=True)
    gaps = long.groupby("series_id")["value"].apply(lambda s: int(s.isna().sum()))
    long = long.dropna(subset=["value"])
    save(long, "fred_long")

    def wide(ids):
        sub = long[long["series_id"].isin(ids)]
        return sub.pivot_table(index="date", columns="series_id", values="value").reset_index()

    eci_ids = [s for s in ("CIS202540A000000I", "CIU202540A000000I") if s in set(long.series_id)]
    if eci_ids:
        eci = wide(eci_ids).rename(columns={"CIS202540A000000I": "eci_wages_sa",
                                           "CIU202540A000000I": "eci_wages_nsa"})
        eci["quarter"] = eci["date"].dt.quarter
        save(eci, "eci_quarterly")
        # Monthly view: place each quarterly index at the quarter's middle month, interpolate.
        m = eci.set_index(eci["date"] + pd.DateOffset(months=1))[["eci_wages_sa"]]
        m = m.resample("MS").mean().interpolate("linear").reset_index().rename(columns={"index": "date"})
        m["note"] = "interpolated from quarterly; use only in the cost engine, not for model fitting"
        save(m, "eci_monthly")
        if "eci_wages_sa" in eci:
            log_quality("BLS ECI", period=f"{eci.date.min().date()} to {eci.date.max().date()}",
                        n_quarters=len(eci), adf_sa_level=adf_summary(eci["eci_wages_sa"]),
                        adf_sa_diff=adf_summary(eci["eci_wages_sa"].diff()))

    ppi_ids = [s for s in ("PCU518210518210", "PCU5182105182105") if s in set(long.series_id)]
    if ppi_ids:
        ppi = wide(ppi_ids).rename(columns={"PCU518210518210": "ppi_hosting",
                                           "PCU5182105182105": "ppi_hosting_infra"})
        save(ppi, "ppi_hosting_monthly")
        log_quality("FRED PPI hosting", period=f"{ppi.date.min().date()} to {ppi.date.max().date()}",
                    n_months=len(ppi), adf_level=adf_summary(ppi["ppi_hosting"]),
                    adf_diff=adf_summary(ppi["ppi_hosting"].diff()))

    nat = [s for s in ("RPSGENAITSALL", "RPSGENAIASSISTWRKHRSALL") if s in set(long.series_id)]
    if nat:
        tr = wide(nat).rename(columns={"RPSGENAITSALL": "time_saved_pct_hours",
                                       "RPSGENAIASSISTWRKHRSALL": "hours_assisted_pct"})
        save(tr, "genai_tracker")
        log_quality("FRED GenAI Adoption Tracker", period=f"{tr.date.min().date()} to {tr.date.max().date()}",
                    n_quarters=len(tr),
                    caveat="too few points for ARIMA; use Holt trend / regression; self-reported")

    panel_ids = [s for s in FRED_SERIES if s.startswith("RPSGENAITS") and s != "RPSGENAITSALL"]
    panel = long[long["series_id"].isin(panel_ids)][["date", "series_id", "description", "value"]]
    if len(panel):
        panel = panel.rename(columns={"value": "time_saved_pct_hours"})
        panel["group_type"] = panel["series_id"].str.contains("OCC").map({True: "occupation", False: "industry"})
        save(panel, "genai_timesaved_panel")
        log_quality("FRED GenAI Adoption Tracker",
                    panel_series=int(panel.series_id.nunique()), panel_rows=len(panel),
                    panel_points_per_series=panel.groupby("series_id").size().to_dict())

    log_quality("FRED (all)", series_loaded=len(frames), series_missing=missing,
                missing_values_dropped=gaps[gaps > 0].to_dict())


if __name__ == "__main__":
    run()
