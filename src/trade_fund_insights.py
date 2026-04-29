from __future__ import annotations

from datetime import date, datetime, timedelta
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
        "fund_count": 0,
        "total_committed_amount": 0.0,
        "total_actual_spend": 0.0,
        "total_remaining_balance": 0.0,
        "spend_compliance_pct": None,
        "expiring_soon_count": 0,
        "underutilized_fund_count": 0,
        "promo_linked_fund_count": 0,
        "at_risk_funds": [],
    }


def compute_trade_fund_insights(
    vendor_id: str,
    trade_fund_df: pd.DataFrame,
    promo_df: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    _ = vendor_id
    _ = promo_df
    ref_date = reference_date or date.today()
    if trade_fund_df.empty:
        return _empty_result()

    df = trade_fund_df.copy()
    df["fund_period_end_parsed"] = df.get(
        "fund_period_end", pd.Series([None] * len(df), index=df.index)
    ).apply(_parse_date)
    df["committed_amount_num"] = pd.to_numeric(df.get("committed_amount"), errors="coerce").fillna(0.0)
    df["actual_spend_num"] = pd.to_numeric(df.get("actual_spend"), errors="coerce").fillna(0.0)
    df["remaining_balance_num"] = pd.to_numeric(df.get("remaining_balance"), errors="coerce").fillna(0.0)
    df["spend_ratio"] = df["actual_spend_num"] / df["committed_amount_num"].replace(0, pd.NA)

    expiring_mask = df["fund_period_end_parsed"].notna() & (
        (df["fund_period_end_parsed"] >= ref_date)
        & (df["fund_period_end_parsed"] <= ref_date + timedelta(days=30))
    )
    underutilized_mask = df["spend_ratio"].fillna(0.0) < 0.5
    promo_linked_mask = df.get(
        "promo_id", pd.Series([None] * len(df), index=df.index)
    ).notna()

    at_risk = df.loc[expiring_mask | underutilized_mask].copy()
    at_risk = at_risk.sort_values(["fund_period_end_parsed", "spend_ratio"], ascending=[True, True])
    at_risk_funds = [
        {
            "fund_id": str(row["fund_id"]),
            "fund_type": str(row["fund_type"]),
            "fund_period_end": row["fund_period_end_parsed"].isoformat() if row["fund_period_end_parsed"] else None,
            "committed_amount": float(row["committed_amount_num"]),
            "actual_spend": float(row["actual_spend_num"]),
            "remaining_balance": float(row["remaining_balance_num"]),
        }
        for _, row in at_risk.head(5).iterrows()
    ]

    committed_total = float(df["committed_amount_num"].sum())
    actual_spend_total = float(df["actual_spend_num"].sum())
    return {
        "fund_count": int(len(df)),
        "total_committed_amount": committed_total,
        "total_actual_spend": actual_spend_total,
        "total_remaining_balance": float(df["remaining_balance_num"].sum()),
        "spend_compliance_pct": round(actual_spend_total / committed_total, 4) if committed_total > 0 else None,
        "expiring_soon_count": int(expiring_mask.sum()),
        "underutilized_fund_count": int(underutilized_mask.sum()),
        "promo_linked_fund_count": int(promo_linked_mask.sum()),
        "at_risk_funds": at_risk_funds,
    }
