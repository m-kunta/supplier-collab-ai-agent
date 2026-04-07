"""Tests for benchmark_engine.compute_benchmarks.

Data contract under test:
  - Returns a dict keyed by metric_code.
  - Each value has: peer_avg, best_in_class, gap_to_bic, dollar_impact.
  - peer_avg is the category average (all non-target vendors).
  - best_in_class is the value at `bic_percentile` across all peers.
  - gap_to_bic is vendor_current minus best_in_class (negative means below BIC).
  - dollar_impact is None when no conversion factor is available.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.benchmark_engine import compute_benchmarks


def _make_peer_df(
    target_vendor: str,
    metric_code: str,
    peer_data: list[tuple[str, str, float]],
    metric_uom: str = "pct",
) -> pd.DataFrame:
    """Build a minimal vendor_performance DataFrame for one metric across multiple vendors.

    peer_data is a list of (vendor_id, week_ending, metric_value) tuples.
    """
    return pd.DataFrame(
        [
            {"vendor_id": vid, "week_ending": week, "metric_code": metric_code, "metric_value": val, "metric_uom": metric_uom}
            for vid, week, val in peer_data
        ]
    )


# Scenario: 5 vendors, 13 weeks of data for FILL_RATE
# Target vendor V1001 has declining performance; peers are mixed
VENDORS = ["V1001", "V1002", "V1003", "V1004", "V1005"]

# Target vendor data (13 weeks, declining from 0.962 to 0.918)
TARGET_FILL_RATE = [
    ("V1001", "2026-01-03", 0.962),
    ("V1001", "2026-01-10", 0.958),
    ("V1001", "2026-01-17", 0.960),
    ("V1001", "2026-01-24", 0.955),
    ("V1001", "2026-01-31", 0.950),
    ("V1001", "2026-02-07", 0.948),
    ("V1001", "2026-02-14", 0.942),
    ("V1001", "2026-02-21", 0.940),
    ("V1001", "2026-02-28", 0.935),
    ("V1001", "2026-03-07", 0.930),
    ("V1001", "2026-03-14", 0.925),
    ("V1001", "2026-03-21", 0.920),
    ("V1001", "2026-03-28", 0.918),
]

# Peer vendors with varying latest-week values
# V1002: stable at 0.95
# V1003: improving, latest 0.97
# V1004: poor performer at 0.88
# V1005: excellent at 0.99
PEERS_FILL_RATE = [
    ("V1002", "2026-03-28", 0.950),
    ("V1003", "2026-03-28", 0.970),
    ("V1004", "2026-03-28", 0.880),
    ("V1005", "2026-03-28", 0.990),
]


class TestComputeBenchmarksPeerAverage(unittest.TestCase):
    """Verify peer_avg excludes target vendor and computes category average."""

    def test_peer_avg_excludes_target_vendor(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        # Peer avg should be computed from V1002-V1005 latest values: 0.95, 0.97, 0.88, 0.99
        expected = (0.95 + 0.97 + 0.88 + 0.99) / 4
        self.assertAlmostEqual(result["FILL_RATE"]["peer_avg"], expected, places=4)

    def test_peer_avg_uses_latest_week_per_vendor(self):
        # Add multiple weeks per peer to ensure only latest is used
        extended_peers = PEERS_FILL_RATE + [
            ("V1002", "2026-03-21", 0.940),
            ("V1003", "2026-03-21", 0.960),
            ("V1004", "2026-03-21", 0.870),
            ("V1005", "2026-03-21", 0.980),
        ]
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + extended_peers)
        result = compute_benchmarks("V1001", df, config={})
        # Still should use latest week (2026-03-28)
        expected = (0.95 + 0.97 + 0.88 + 0.99) / 4
        self.assertAlmostEqual(result["FILL_RATE"]["peer_avg"], expected, places=4)


class TestComputeBenchmarksBestInClass(unittest.TestCase):
    """Verify best_in_class percentile calculation."""

    def test_bic_at_default_90th_percentile(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        # 90th percentile of [0.88, 0.95, 0.97, 0.99]
        peer_values = [0.88, 0.95, 0.97, 0.99]  # V1004, V1002, V1003, V1005 latest-week values
        expected = float(np.percentile(peer_values, 90))
        self.assertAlmostEqual(result["FILL_RATE"]["best_in_class"], expected, places=4)

    def test_bic_respects_configured_percentile(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        config = {"benchmarks": {"bic_percentile": 75}}
        result = compute_benchmarks("V1001", df, config=config)
        # 75th percentile of [0.88, 0.95, 0.97, 0.99]
        self.assertAlmostEqual(
            result["FILL_RATE"]["best_in_class"],
            0.975,  # np.percentile([0.88, 0.95, 0.97, 0.99], 75) = 0.975
            places=3,
        )


class TestComputeBenchmarksGap(unittest.TestCase):
    """Verify gap_to_bic computation (vendor_current minus best_in_class)."""

    def test_gap_is_negative_when_vendor_below_bic(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        # Vendor current (0.918) should be below BIC (≈0.988)
        self.assertLess(result["FILL_RATE"]["gap_to_bic"], 0)

    def test_gap_matches_vendor_current_minus_bic(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        expected_gap = round(0.918 - result["FILL_RATE"]["best_in_class"], 6)
        self.assertAlmostEqual(result["FILL_RATE"]["gap_to_bic"], expected_gap, places=5)


class TestComputeBenchmarksDollarImpact(unittest.TestCase):
    """Verify dollar_impact is None without conversion factors, computed when provided."""

    def test_dollar_impact_is_none_without_conversion(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        self.assertIsNone(result["FILL_RATE"]["dollar_impact"])

    def test_dollar_impact_computed_with_conversion_factor(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        config = {
            "benchmarks": {
                "bic_percentile": 90,
                "conversion_factors": {"FILL_RATE": 1000000},  # $1M per 1.0 pct point
            }
        }
        result = compute_benchmarks("V1001", df, config=config)
        # gap is 0.918 - ~0.988 = ~-0.07
        # dollar impact = gap * conversion = ~-0.07 * 1M = ~-$70,000
        impact = result["FILL_RATE"]["dollar_impact"]
        self.assertIsNotNone(impact)
        self.assertAlmostEqual(impact, round((0.918 - result["FILL_RATE"]["best_in_class"]) * 1000000, 2), places=1)


class TestComputeBenchmarksMultipleMetrics(unittest.TestCase):
    """Verify handling when multiple metric codes are present."""

    def test_returns_all_metrics_present_in_data(self):
        fill_rate = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        otf_data = [
            ("V1001", "2026-03-28", 0.850),
            ("V1002", "2026-03-28", 0.920),
            ("V1003", "2026-03-28", 0.940),
            ("V1004", "2026-03-28", 0.800),
            ("V1005", "2026-03-28", 0.960),
        ]
        otf_data_target = [
            ("V1001", w, v) for w, v in [("2026-03-21", 0.870), ("2026-03-14", 0.860)]
        ]
        otf_df = _make_peer_df("V1001", "OTIF", otf_data_target + otf_data)
        df = pd.concat([fill_rate, otf_df], ignore_index=True)
        result = compute_benchmarks("V1001", df, config={})
        self.assertIn("FILL_RATE", result)
        self.assertIn("OTIF", result)

    def test_each_metric_has_required_keys(self):
        df = _make_peer_df("V1001", "FILL_RATE", TARGET_FILL_RATE + PEERS_FILL_RATE)
        result = compute_benchmarks("V1001", df, config={})
        entry = result["FILL_RATE"]
        for key in ("peer_avg", "best_in_class", "gap_to_bic", "dollar_impact"):
            self.assertIn(key, entry, f"Missing key: {key}")


class TestComputeBenchmarksEdgeCases(unittest.TestCase):
    """Corner cases: single peer, no peers, insufficient data."""

    def test_single_peer_uses_that_peer_for_avg_and_bic(self):
        data = [
            ("V1001", "2026-03-28", 0.90),
            ("V1002", "2026-03-28", 0.95),
        ]
        df = _make_peer_df("V1001", "FILL_RATE", data)
        result = compute_benchmarks("V1001", df, config={})
        self.assertAlmostEqual(result["FILL_RATE"]["peer_avg"], 0.95, places=4)
        # With 1 peer, BIC is just that peer's value
        self.assertAlmostEqual(result["FILL_RATE"]["best_in_class"], 0.95, places=4)

    def test_no_peers_returns_empty_result(self):
        data = [
            ("V1001", "2026-03-28", 0.90),
        ]
        df = _make_peer_df("V1001", "FILL_RATE", data)
        result = compute_benchmarks("V1001", df, config={})
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
