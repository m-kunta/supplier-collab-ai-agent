from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "Scorecard engine scaffold."


def compute_scorecard(
    vendor_id: str,
    performance_df: pd.DataFrame,
    lookback_weeks: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute scorecard metrics for a vendor.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        performance_df: ``vendor_performance`` DataFrame filtered to ``vendor_id``,
            with columns ``[vendor_id, week_ending, metric_code, metric_value, metric_uom]``.
        lookback_weeks: Number of trailing weeks to include (typically 13).
        config: Full agent config dict; uses ``thresholds`` section for
            ``trend_improvement_consecutive_weeks`` and ``trend_improvement_min_delta``.

    Returns:
        Dict keyed by ``metric_code``, each value containing:

        - ``current_value`` (float) — most recent week's value
        - ``trend_4w`` (float | None) — delta vs. 4-week prior value
        - ``trend_13w`` (float | None) — delta vs. 13-week prior value
        - ``trend_direction`` (str) — one of ``'improving'``, ``'declining'``,
          ``'stable'``, or ``'insufficient_data'``
    """
    raise NotImplementedError(
        "Scorecard computation is not yet implemented. "
        "See docs/implementation_plan.md Phase 3."
    )
