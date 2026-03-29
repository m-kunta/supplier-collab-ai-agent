from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "Promo readiness scaffold."


def compute_promo_readiness(
    vendor_id: str,
    promo_df: pd.DataFrame,
    po_df: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score promotional readiness for a vendor's upcoming promotions.

    Each upcoming promo event is evaluated for PO coverage and fill-rate
    history to produce a per-event readiness score and an overall tier.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        promo_df: ``promo_calendar`` DataFrame filtered to ``vendor_id``.
            Expected columns include
            ``[promo_id, event_name, start_date, end_date, sku, promoted_volume]``.
        po_df: ``purchase_orders`` DataFrame filtered to ``vendor_id``,
            used for PO × promo cross-reference to determine coverage.
        config: Full agent config dict; uses:

            - ``thresholds.promo_readiness_red_threshold`` — score below this → red
            - ``thresholds.promo_readiness_yellow_threshold`` — score below this → yellow

    Returns:
        Dict with:

        - ``overall_score`` (float) — composite readiness score from 0.0 to 1.0
        - ``risk_tier`` (str) — ``'red'``, ``'yellow'``, or ``'green'``
        - ``events`` (list[dict]) — one entry per promo event, each:
          ``{promo_id: str, event_name: str, start_date: str,
          score: float, covered_by_po: bool}``
    """
    raise NotImplementedError(
        "Promo readiness computation is not yet implemented. "
        "See docs/implementation_plan.md Phase 3."
    )
