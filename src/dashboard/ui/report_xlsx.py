"""Excel download of the decision summary: the three outlooks side by side, the shown run month by month and the
figures used. Money in rupees (converted here, as on screen). Built in memory; nothing is written to the server."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from dashboard.core import currency as CUR
from dashboard.core import data as D
from dashboard.ui import copy as C


def _inr(x) -> float:
    return float(np.round(CUR.to_inr(x), 0)) if np.isfinite(x) else float("nan")


def summary_frame(rows: list[dict]) -> pd.DataFrame:
    X = C.XLSX_COLS
    return pd.DataFrame([{X["outlook"]: C.OUTLOOK[r["scenario"]], X["chance"]: round(r["chance"], 3),
                          X["month"]: r["month"], X["cost"]: _inr(r["cost"]), X["benefit"]: _inr(r["benefit"]),
                          X["balance"]: _inr(r["balance"]), X["low"]: _inr(r["balance_low"]),
                          X["high"]: _inr(r["balance_high"]), X["npv"]: _inr(r["npv"]), X["roi"]: round(r["roi"], 3),
                          X["per_user"]: _inr(r["cost_per_user_month"])} for r in rows])


def build(rows: list[dict], res, inputs: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        summary_frame(rows).to_excel(xw, sheet_name=C.XLSX_SHEETS["summary"], index=False)
        D.monthly_result_table(res).to_excel(xw, sheet_name=C.XLSX_SHEETS["monthly"], index=False)
        pd.DataFrame({"Figure": list(inputs), "Value (engine units, money in US dollars)": [str(v) for v in inputs.values()]}
                     ).to_excel(xw, sheet_name=C.XLSX_SHEETS["inputs"], index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(48, max(12, max(len(str(c.value or "")) for c in col) + 2))
    return buf.getvalue()
