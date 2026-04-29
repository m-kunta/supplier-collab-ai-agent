from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


def _parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _empty_result() -> dict[str, Any]:
    return {
        "shipment_count": 0,
        "received_shipment_count": 0,
        "overdue_shipment_count": 0,
        "avg_receipt_lag_days": None,
        "on_time_receipt_pct": None,
        "fill_in_accuracy_pct": None,
        "top_overdue_asns": [],
    }


def compute_asn_insights(
    vendor_id: str,
    asn_df: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    _ = vendor_id
    ref_date = reference_date or date.today()
    if asn_df.empty:
        return _empty_result()

    df = asn_df.copy()
    df["expected_receipt_date_parsed"] = df.get(
        "expected_receipt_date", pd.Series([None] * len(df), index=df.index)
    ).apply(_parse_date)
    df["actual_receipt_date_parsed"] = df.get(
        "actual_receipt_date", pd.Series([None] * len(df), index=df.index)
    ).apply(_parse_date)
    df["qty_shipped_num"] = pd.to_numeric(df.get("qty_shipped"), errors="coerce")
    df["qty_received_num"] = pd.to_numeric(df.get("qty_received"), errors="coerce")

    received_mask = df["actual_receipt_date_parsed"].notna()
    overdue_mask = (
        df.get("receipt_status", pd.Series([""] * len(df), index=df.index))
        .fillna("")
        .astype(str)
        .str.lower()
        .eq("overdue")
    ) | (
        df["actual_receipt_date_parsed"].isna()
        & df["expected_receipt_date_parsed"].notna()
        & (df["expected_receipt_date_parsed"] < ref_date)
    )

    received = df.loc[received_mask].copy()
    if not received.empty:
        received["receipt_lag_days"] = received.apply(
            lambda row: (row["actual_receipt_date_parsed"] - row["expected_receipt_date_parsed"]).days,
            axis=1,
        )
        avg_receipt_lag_days = float(received["receipt_lag_days"].mean())
        on_time_receipt_pct = float((received["receipt_lag_days"] <= 0).mean())
    else:
        avg_receipt_lag_days = None
        on_time_receipt_pct = None

    qty_mask = df["qty_shipped_num"].notna() & (df["qty_shipped_num"] > 0) & df["qty_received_num"].notna()
    if qty_mask.any():
        fill_in_accuracy_pct = float(
            (df.loc[qty_mask, "qty_received_num"] / df.loc[qty_mask, "qty_shipped_num"]).mean()
        )
    else:
        fill_in_accuracy_pct = None

    overdue_rows = df.loc[overdue_mask].copy()
    if not overdue_rows.empty:
        overdue_rows["days_overdue"] = overdue_rows["expected_receipt_date_parsed"].apply(
            lambda expected: (ref_date - expected).days if expected is not None else 0
        )
        overdue_rows = overdue_rows.sort_values("days_overdue", ascending=False)
        top_overdue_asns = [
            {
                "asn_number": str(row["asn_number"]),
                "po_number": str(row["po_number"]),
                "days_overdue": int(row["days_overdue"]),
            }
            for _, row in overdue_rows.head(5).iterrows()
        ]
    else:
        top_overdue_asns = []

    return {
        "shipment_count": int(len(df)),
        "received_shipment_count": int(received_mask.sum()),
        "overdue_shipment_count": int(overdue_mask.sum()),
        "avg_receipt_lag_days": round(avg_receipt_lag_days, 4) if avg_receipt_lag_days is not None else None,
        "on_time_receipt_pct": round(on_time_receipt_pct, 4) if on_time_receipt_pct is not None else None,
        "fill_in_accuracy_pct": round(fill_in_accuracy_pct, 4) if fill_in_accuracy_pct is not None else None,
        "top_overdue_asns": top_overdue_asns,
    }
