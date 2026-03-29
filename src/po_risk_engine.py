from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "PO risk engine scaffold."


def compute_po_risk(
    vendor_id: str,
    po_df: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute PO risk tiering for a vendor's open purchase orders.

    Each open PO line is tiered as ``red``, ``yellow``, or ``green`` based on
    days until the requested delivery date relative to today, and whether the
    PO covers a promotional event.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        po_df: ``purchase_orders`` DataFrame filtered to ``vendor_id`` and
            open statuses. Expected columns include
            ``[po_number, po_line, sku, requested_delivery_date, po_status]``.
        config: Full agent config dict; uses:

            - ``thresholds.po_risk_days_late_red`` — days overdue to assign red
            - ``thresholds.po_risk_days_late_yellow`` — days overdue to assign yellow

    Returns:
        Dict with:

        - ``summary`` (dict) — counts per tier:
          ``{red: int, yellow: int, green: int, total: int}``
        - ``line_items`` (list[dict]) — one entry per PO line, each containing:
          ``{po_number, po_line, sku, days_until_need: int, risk_tier: str}``
    """
    raise NotImplementedError(
        "PO risk computation is not yet implemented. "
        "See docs/implementation_plan.md Phase 3."
    )
