from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

_VENDOR_CONTROLLABLE: frozenset[str] = frozenset(
    {"late_shipment", "short_fill", "cancelled_po"}
)
_DEMAND_DRIVEN: frozenset[str] = frozenset({"demand_spike", "forecast_error"})

# Tie-break priority when a SKU's events are split across categories
_CAUSE_PRIORITY: dict[str, int] = {
    "vendor_controllable": 0,
    "demand_driven": 1,
    "unattributed": 2,
}


def describe_scope() -> str:
    return (
        "OOS attribution engine: classifies out-of-stock events as "
        "vendor-controllable, demand-driven, or unattributed using "
        "root_cause_code with PO cancellation cross-reference fallback."
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


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


def _classify_cause(cause: str) -> str:
    """Map a normalized (lowercased, stripped) cause string to a category."""
    if cause in _VENDOR_CONTROLLABLE:
        return "vendor_controllable"
    if cause in _DEMAND_DRIVEN:
        return "demand_driven"
    return "unattributed"


def _get_cancelled_skus(po_df: pd.DataFrame) -> frozenset[str]:
    """Return the set of SKUs that have at least one cancelled PO line."""
    if po_df.empty or "po_status" not in po_df.columns or "sku" not in po_df.columns:
        return frozenset()
    statuses = (
        po_df["po_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )
    cancelled_mask = statuses == "cancelled"
    return frozenset(po_df.loc[cancelled_mask, "sku"].dropna().astype(str).unique())


def _get_recurring_skus(df: pd.DataFrame, threshold: int) -> list[str]:
    """Return a sorted list of SKUs with event count >= threshold."""
    counts = df["sku"].value_counts()
    return sorted(counts[counts >= threshold].index.tolist())


def _build_top_skus(
    df: pd.DataFrame,
    recurring_skus_set: frozenset[str],
    limit: int = 5,
) -> list[dict]:
    """Return top SKUs by event count with per-SKU primary cause and recurrence flag."""
    records = []
    for sku, group in df.groupby("sku"):
        cause_counts = group["_category"].value_counts()
        primary_cause = min(
            cause_counts.index,
            key=lambda c: _CAUSE_PRIORITY.get(c, 99),
        )
        records.append(
            {
                "sku": str(sku),
                "oos_count": int(len(group)),
                "primary_cause": primary_cause,
                "is_recurring": str(sku) in recurring_skus_set,
            }
        )
    records.sort(key=lambda r: r["oos_count"], reverse=True)
    return records[:limit]


def _empty_result() -> dict[str, Any]:
    return {
        "total_oos_events": 0,
        "vendor_controllable": 0,
        "demand_driven": 0,
        "unattributed": 0,
        "vendor_controllable_pct": None,
        "total_units_lost": None,
        "recurring_skus": [],
        "top_skus": [],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_oos_attribution(
    vendor_id: str,
    oos_df: pd.DataFrame,
    po_df: pd.DataFrame,
    config: dict[str, Any],
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Attribute out-of-stock events to root cause for a vendor.

    Events are classified as vendor-controllable (late shipments, short fills,
    cancelled POs) or demand-driven (demand spike with no supplier failure signal).
    When ``root_cause_code`` is null, PO cancellation status is used as a
    secondary signal.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        oos_df: ``oos_events`` DataFrame. Expected columns include
            ``[vendor_id, sku, oos_start_date, root_cause_code]``. Optional:
            ``oos_units_lost``.
        po_df: ``purchase_orders`` DataFrame for PO cancellation cross-reference.
        config: Full agent config dict; uses:
            - ``thresholds.oos_recurrence_lookback_count`` — SKU flagged as
              recurring when its event count >= this value (default ``2``).
        reference_date: Unused by current logic; reserved for future lookback
            filtering. Defaults to today.

    Returns:
        Dict with:

        - ``total_oos_events`` (int)
        - ``vendor_controllable`` (int)
        - ``demand_driven`` (int)
        - ``unattributed`` (int)
        - ``vendor_controllable_pct`` (float | None) — None when total is 0
        - ``total_units_lost`` (float | None) — None when all oos_units_lost are NaN
        - ``recurring_skus`` (list[str]) — sorted; count >= recurrence threshold
        - ``top_skus`` (list[dict]) — up to 5 top SKUs by event count, each:
          ``{sku, oos_count, primary_cause, is_recurring}``
    """
    thresholds = config.get("thresholds", {})
    recurrence_threshold = int(thresholds.get("oos_recurrence_lookback_count", 2))
    _ = reference_date or date.today()  # reserved for future lookback filtering

    # --- Empty guard (before column validation — no columns on empty DataFrame) --
    if oos_df.empty:
        return _empty_result()

    # --- Column validation ------------------------------------------------
    required_columns = {"vendor_id", "sku", "oos_start_date", "root_cause_code"}
    missing = required_columns - set(oos_df.columns)
    if missing:
        raise ValueError(
            "oos_df is missing required columns: " + ", ".join(sorted(missing))
        )

    # --- Working copy + date parsing --------------------------------------
    df = oos_df.copy()
    df["_oos_start"] = df["oos_start_date"].apply(_parse_date)
    # Drop rows where date is unparseable to avoid silent bad data
    bad_dates = df["_oos_start"].isna()
    if bad_dates.any():
        logger.debug(
            "compute_oos_attribution: vendor='%s' dropping %d rows with unparseable oos_start_date",
            vendor_id,
            int(bad_dates.sum()),
        )
        df = df[~bad_dates].copy()

    if df.empty:
        return _empty_result()

    # --- Normalize root_cause_code ----------------------------------------
    df["_cause"] = (
        df["root_cause_code"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # --- Primary classification -------------------------------------------
    df["_category"] = df["_cause"].apply(_classify_cause)

    # --- Secondary PO cross-reference (unattributed rows only) -----------
    cancelled_skus = _get_cancelled_skus(po_df)
    if cancelled_skus:
        mask_unattributed = df["_category"] == "unattributed"
        reclassify_mask = mask_unattributed & df["sku"].astype(str).isin(cancelled_skus)
        df.loc[reclassify_mask, "_category"] = "vendor_controllable"

    # --- Bucket counts ----------------------------------------------------
    category_counts = df["_category"].value_counts()
    vendor_controllable = int(category_counts.get("vendor_controllable", 0))
    demand_driven = int(category_counts.get("demand_driven", 0))
    unattributed = int(category_counts.get("unattributed", 0))
    total_oos_events = len(df)

    # --- vendor_controllable_pct ------------------------------------------
    vendor_controllable_pct: float | None = (
        round(vendor_controllable / total_oos_events, 4)
        if total_oos_events > 0
        else None
    )

    # --- total_units_lost -------------------------------------------------
    total_units_lost: float | None = None
    if "oos_units_lost" in df.columns:
        units_col = pd.to_numeric(df["oos_units_lost"], errors="coerce")
        if units_col.notna().any():
            total_units_lost = float(units_col.sum(skipna=True))

    # --- Recurring SKUs ---------------------------------------------------
    recurring_skus = _get_recurring_skus(df, recurrence_threshold)

    # --- Top SKUs ---------------------------------------------------------
    top_skus = _build_top_skus(df, frozenset(recurring_skus), limit=5)

    logger.debug(
        "compute_oos_attribution: vendor='%s' total=%d vendor_controllable=%d "
        "demand_driven=%d unattributed=%d recurring_skus=%d",
        vendor_id,
        total_oos_events,
        vendor_controllable,
        demand_driven,
        unattributed,
        len(recurring_skus),
    )

    return {
        "total_oos_events": total_oos_events,
        "vendor_controllable": vendor_controllable,
        "demand_driven": demand_driven,
        "unattributed": unattributed,
        "vendor_controllable_pct": vendor_controllable_pct,
        "total_units_lost": total_units_lost,
        "recurring_skus": recurring_skus,
        "top_skus": top_skus,
    }
