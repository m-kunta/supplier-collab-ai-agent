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
        "chargeback_count": 0,
        "total_chargeback_amount": 0.0,
        "open_chargeback_amount": 0.0,
        "disputed_chargeback_amount": 0.0,
        "most_recent_issue_date": None,
        "top_chargeback_types": [],
        "recent_open_chargebacks": [],
    }


def compute_chargeback_insights(
    vendor_id: str,
    chargeback_df: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    _ = vendor_id
    _ = reference_date
    if chargeback_df.empty:
        return _empty_result()

    df = chargeback_df.copy()
    df["issue_date_parsed"] = df.get(
        "issue_date", pd.Series([None] * len(df), index=df.index)
    ).apply(_parse_date)
    df["chargeback_amount_num"] = pd.to_numeric(df.get("chargeback_amount"), errors="coerce").fillna(0.0)
    statuses = (
        df.get("dispute_status", pd.Series([""] * len(df), index=df.index))
        .fillna("")
        .astype(str)
        .str.lower()
    )

    type_rollup = (
        df.groupby("chargeback_type", dropna=True)["chargeback_amount_num"]
        .agg(["count", "sum"])
        .sort_values(["sum", "count"], ascending=[False, False])
        .reset_index()
    )
    top_chargeback_types = [
        {
            "chargeback_type": str(row["chargeback_type"]),
            "count": int(row["count"]),
            "amount": float(row["sum"]),
        }
        for _, row in type_rollup.head(5).iterrows()
    ]

    unresolved = df.loc[statuses.isin(["open", "disputed"])].copy()
    unresolved = unresolved.sort_values("issue_date_parsed", ascending=False)
    recent_open_chargebacks = [
        {
            "chargeback_id": str(row["chargeback_id"]),
            "chargeback_type": str(row["chargeback_type"]),
            "chargeback_amount": float(row["chargeback_amount_num"]),
            "dispute_status": str(row.get("dispute_status", "")),
            "issue_date": row["issue_date_parsed"].isoformat() if row["issue_date_parsed"] else None,
        }
        for _, row in unresolved.head(5).iterrows()
    ]

    most_recent = df["issue_date_parsed"].dropna()
    return {
        "chargeback_count": int(len(df)),
        "total_chargeback_amount": float(df["chargeback_amount_num"].sum()),
        "open_chargeback_amount": float(df.loc[statuses.eq("open"), "chargeback_amount_num"].sum()),
        "disputed_chargeback_amount": float(df.loc[statuses.eq("disputed"), "chargeback_amount_num"].sum()),
        "most_recent_issue_date": most_recent.max().isoformat() if not most_recent.empty else None,
        "top_chargeback_types": top_chargeback_types,
        "recent_open_chargebacks": recent_open_chargebacks,
    }
