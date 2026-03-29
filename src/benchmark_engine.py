from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "Benchmark engine scaffold."


def compute_benchmarks(
    vendor_id: str,
    performance_df: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute benchmark comparisons for a vendor against category peers.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        performance_df: Full (all-vendor) ``vendor_performance`` DataFrame.
            Must contain ``[vendor_id, week_ending, metric_code, metric_value]``.
        config: Full agent config dict; uses ``benchmarks.bic_percentile``
            (default 90) to determine best-in-class threshold.

    Returns:
        Dict keyed by ``metric_code``, each value containing:

        - ``peer_avg`` (float) — category average for the metric
        - ``best_in_class`` (float) — value at ``bic_percentile`` across all peers
        - ``gap_to_bic`` (float) — vendor current value minus ``best_in_class``
          (negative means below BIC)
        - ``dollar_impact`` (float | None) — estimated revenue/cost impact of
          closing the gap; ``None`` when a conversion factor is unavailable
    """
    raise NotImplementedError(
        "Benchmark computation is not yet implemented. "
        "See docs/implementation_plan.md Phase 3."
    )
