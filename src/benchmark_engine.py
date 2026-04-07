from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return "Benchmark engine computes peer averages, BIC gaps, and dollar impact."


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
    required_columns = {"vendor_id", "week_ending", "metric_code", "metric_value"}
    missing_columns = required_columns - set(performance_df.columns)
    if missing_columns:
        raise ValueError(
            "performance_df is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if performance_df.empty:
        return {}

    benchmark_config = config.get("benchmarks", {})
    bic_percentile = benchmark_config.get("bic_percentile", 90)
    conversion_factors = benchmark_config.get("conversion_factors", {})

    latest_df = performance_df.copy()
    latest_df["week_ending"] = pd.to_datetime(latest_df["week_ending"], errors="coerce")
    latest_df = latest_df.dropna(subset=["week_ending", "metric_value"])
    if latest_df.empty:
        return {}

    latest_df = latest_df.sort_values(["metric_code", "vendor_id", "week_ending"])
    latest_df = latest_df.groupby(["metric_code", "vendor_id"], as_index=False).tail(1)

    vendor_rows = latest_df[latest_df["vendor_id"] == vendor_id]
    if vendor_rows.empty:
        return {}

    results: dict[str, Any] = {}
    for vendor_row in vendor_rows.itertuples(index=False):
        metric_code = vendor_row.metric_code
        vendor_current = float(vendor_row.metric_value)
        peer_rows = latest_df[
            (latest_df["metric_code"] == metric_code)
            & (latest_df["vendor_id"] != vendor_id)
        ]

        if peer_rows.empty:
            continue

        peer_values = peer_rows["metric_value"].astype(float)
        peer_avg = float(peer_values.mean())
        best_in_class = float(
            peer_values.quantile(bic_percentile / 100, interpolation="linear")
        )
        gap_to_bic = round(vendor_current - best_in_class, 6)

        conversion_factor = conversion_factors.get(metric_code)
        dollar_impact = None
        if conversion_factor is not None:
            dollar_impact = round(gap_to_bic * float(conversion_factor), 2)

        results[metric_code] = {
            "peer_avg": peer_avg,
            "best_in_class": best_in_class,
            "gap_to_bic": gap_to_bic,
            "dollar_impact": dollar_impact,
        }

    return results
