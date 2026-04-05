from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _has_consecutive_streak(
    deltas: pd.Series,
    consecutive_weeks: int,
    min_delta: float,
    improving: bool,
) -> bool:
    streak = 0
    for delta in deltas:
        qualifies = delta >= min_delta if improving else delta <= -min_delta
        if qualifies:
            streak += 1
            if streak >= consecutive_weeks:
                return True
        else:
            streak = 0
    return False


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
    thresholds = config.get("thresholds", {})
    consecutive_weeks = int(
        thresholds.get("trend_improvement_consecutive_weeks", 3)
    )
    min_delta = float(thresholds.get("trend_improvement_min_delta", 0.005))

    result: dict[str, Any] = {}

    for metric_code, group in performance_df.groupby("metric_code"):
        sorted_weeks = (
            group.sort_values("week_ending")
            .tail(lookback_weeks)
            .reset_index(drop=True)
        )
        n = len(sorted_weeks)

        current_window = sorted_weeks.tail(min(4, n))
        current_value = round(float(current_window["metric_value"].mean()), 6)

        trend_4w: float | None = None
        if n >= 5:
            prior_4w = float(sorted_weeks.iloc[-5]["metric_value"])
            trend_4w = round(current_value - prior_4w, 6)

        trend_13w: float | None = None
        if n >= 13:
            prior_13w = float(sorted_weeks.iloc[-13]["metric_value"])
            trend_13w = round(current_value - prior_13w, 6)

        deltas = sorted_weeks["metric_value"].diff().dropna()

        if n < 2:
            trend_direction = "insufficient_data"
        elif _has_consecutive_streak(deltas, consecutive_weeks, min_delta, improving=False):
            trend_direction = "declining"
        elif _has_consecutive_streak(deltas, consecutive_weeks, min_delta, improving=True):
            trend_direction = "improving"
        else:
            trend_direction = "stable"

        result[metric_code] = {
            "current_value": current_value,
            "trend_4w": trend_4w,
            "trend_13w": trend_13w,
            "trend_direction": trend_direction,
        }

    logger.debug("compute_scorecard: %d metrics computed for vendor '%s'.", len(result), vendor_id)
    return result
