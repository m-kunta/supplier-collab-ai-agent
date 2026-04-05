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
    stable_threshold = (
        config.get("thresholds", {}).get("trend_stable_max_delta", 0.005)
    )

    result: dict[str, Any] = {}

    for metric_code, group in performance_df.groupby("metric_code"):
        sorted_weeks = (
            group.sort_values("week_ending")
            .tail(lookback_weeks)
            .reset_index(drop=True)
        )
        n = len(sorted_weeks)

        current_value = float(sorted_weeks.iloc[-1]["metric_value"])

        trend_4w: float | None = None
        if n >= 5:
            prior_4w = float(sorted_weeks.iloc[-5]["metric_value"])
            trend_4w = round(current_value - prior_4w, 6)

        trend_13w: float | None = None
        if n >= 13:
            prior_13w = float(sorted_weeks.iloc[-13]["metric_value"])
            trend_13w = round(current_value - prior_13w, 6)

        if n < 2:
            trend_direction = "insufficient_data"
        elif trend_4w is not None and abs(trend_4w) <= stable_threshold:
            trend_direction = "stable"
        elif trend_4w is not None and trend_4w > stable_threshold:
            trend_direction = "improving"
        elif trend_4w is not None and trend_4w < -stable_threshold:
            trend_direction = "declining"
        else:
            # Fewer than 4 weeks but at least 2 — use 2-point delta
            delta = current_value - float(sorted_weeks.iloc[0]["metric_value"])
            if abs(delta) <= stable_threshold:
                trend_direction = "stable"
            elif delta > 0:
                trend_direction = "improving"
            else:
                trend_direction = "declining"

        result[metric_code] = {
            "current_value": current_value,
            "trend_4w": trend_4w,
            "trend_13w": trend_13w,
            "trend_direction": trend_direction,
        }

    logger.debug("compute_scorecard: %d metrics computed for vendor '%s'.", len(result), vendor_id)
    return result
