from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "PO risk tiering engine."


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _tier(days_late: float, red_threshold: float, yellow_threshold: float) -> str:
    if days_late > red_threshold:
        return "red"
    elif days_late >= yellow_threshold and not (
        yellow_threshold == 0 and days_late == 0
    ):
        return "yellow"
    else:
        return "green"


def compute_po_risk(
    vendor_id: str,
    po_df: pd.DataFrame,
    config: dict[str, Any],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Compute PO risk tiering for a vendor's purchase orders.

    Each PO line is tiered as ``red``, ``yellow``, or ``green`` based on
    days overdue relative to the requested delivery date. Open/shipped POs
    are assessed against today; received POs are assessed against the actual
    receipt date.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        po_df: ``purchase_orders`` DataFrame. Expected columns include
            ``[po_number, po_line, vendor_id, sku, requested_delivery_date, po_status]``.
        config: Full agent config dict; uses:
            - ``thresholds.po_risk_days_late_red`` — days overdue to assign red (default 3)
            - ``thresholds.po_risk_days_late_yellow`` — days overdue to assign yellow (default 1)
        reference_date: Date used for open/shipped POs. Defaults to today.

    Returns:
        Dict with:
        - ``summary`` (dict) — counts per tier: ``{red: int, yellow: int, green: int, total: int}``
        - ``line_items`` (list[dict]) — one entry per PO line with:
          ``{po_number, po_line, sku, requested_delivery_date, po_status, days_late, risk_tier}``
    """
    thresholds = config.get("thresholds", {})
    red_threshold = float(thresholds.get("po_risk_days_late_red", 3))
    yellow_threshold = float(thresholds.get("po_risk_days_late_yellow", 1))

    today = reference_date or date.today()

    if po_df.empty:
        return {
            "summary": {"red": 0, "yellow": 0, "green": 0, "total": 0},
            "line_items": [],
        }

    df = po_df.copy()

    req_col = df.get(
        "requested_delivery_date", pd.Series([None] * len(df), index=df.index)
    )
    df["_req_date"] = req_col.apply(_parse_date)

    open_statuses = {"open", "confirmed", "shipped", "in_transit"}
    df["po_status"] = (
        df.get("po_status", pd.Series(["open"] * len(df), index=df.index))
        .fillna("open")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    is_open = df["po_status"].isin(open_statuses)

    if "actual_receipt_date" in df.columns:
        df["_rec_date"] = df["actual_receipt_date"].apply(_parse_date)
        has_valid_receipt = df["_rec_date"].notna()
    else:
        df["_rec_date"] = pd.NaT
        has_valid_receipt = pd.Series([False] * len(df), index=df.index)

    def _days_late(req_date, ref_date):
        if req_date is None or ref_date is None or (ref_date != ref_date):
            return 0.0
        return (ref_date - req_date).days

    ref_dates = pd.Series(index=df.index, dtype=object)
    ref_dates.loc[is_open] = today
    has_rec_and_not_open = has_valid_receipt & ~is_open
    ref_dates.loc[has_rec_and_not_open] = df.loc[has_rec_and_not_open, "_rec_date"]
    ref_dates = ref_dates.fillna(today)

    df["days_late"] = [
        _days_late(req, ref) for req, ref in zip(df["_req_date"], ref_dates)
    ]
    df["risk_tier"] = df["days_late"].apply(
        lambda d: _tier(d, red_threshold, yellow_threshold)
    )

    line_items = []
    for _, row in df.iterrows():
        line_items.append(
            {
                "po_number": str(row.get("po_number", "")),
                "po_line": int(row.get("po_line", 0)),
                "sku": str(row.get("sku", "")),
                "requested_delivery_date": str(row.get("requested_delivery_date", "")),
                "po_status": str(row.get("po_status", "")),
                "days_late": round(float(row["days_late"]), 1),
                "risk_tier": str(row["risk_tier"]),
            }
        )

    tier_counts = df["risk_tier"].value_counts().to_dict()
    summary = {
        "red": int(tier_counts.get("red", 0)),
        "yellow": int(tier_counts.get("yellow", 0)),
        "green": int(tier_counts.get("green", 0)),
        "total": int(len(df)),
    }

    logger.debug(
        "compute_po_risk: vendor='%s' red=%d yellow=%d green=%d total=%d",
        vendor_id,
        summary["red"],
        summary["yellow"],
        summary["green"],
        summary["total"],
    )
    return {"summary": summary, "line_items": line_items}
