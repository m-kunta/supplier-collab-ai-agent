from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "OOS attribution scaffold."


def compute_oos_attribution(
    vendor_id: str,
    oos_df: pd.DataFrame,
    po_df: pd.DataFrame,
) -> dict[str, Any]:
    """Attribute out-of-stock events to root cause for a vendor.

    Events are classified as vendor-controllable (late shipments, short fills,
    cancelled POs) or demand-driven (demand spike with no supplier failure signal).

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        oos_df: ``oos_events`` DataFrame filtered to ``vendor_id``.
            Expected columns include
            ``[sku, oos_start_date, oos_end_date, oos_units_lost]``.
        po_df: ``purchase_orders`` DataFrame filtered to ``vendor_id``,
            used for cross-referencing whether a PO was late or short at
            the time of the OOS event.

    Returns:
        Dict with:

        - ``total_oos_events`` (int)
        - ``vendor_controllable`` (int) — events attributable to vendor failure
        - ``demand_driven`` (int) — events attributable to demand spikes
        - ``unattributed`` (int) — events without sufficient signal
        - ``top_skus`` (list[dict]) — top offending SKUs, each:
          ``{sku: str, oos_count: int, primary_cause: str}``
    """
    raise NotImplementedError(
        "OOS attribution is not yet implemented. "
        "See docs/implementation_plan.md Phase 3."
    )
