"""Tests for scorecard_engine.compute_scorecard.

Data contract under test:
  - Returns a dict keyed by metric_code.
  - Each value has: current_value, trend_4w, trend_13w, trend_direction.
  - trend_direction is one of: 'improving', 'declining', 'stable', 'insufficient_data'.
  - trend_4w / trend_13w are None when insufficient history exists.
"""
from __future__ import annotations

import unittest

import pandas as pd

from src.scorecard_engine import compute_scorecard


def _make_df(vendor_id: str, metric_code: str, weeks: list[tuple[str, float]]) -> pd.DataFrame:
    """Build a minimal vendor_performance DataFrame for one metric."""
    return pd.DataFrame(
        [
            {"vendor_id": vendor_id, "week_ending": w, "metric_code": metric_code, "metric_value": v, "metric_uom": "pct"}
            for w, v in weeks
        ]
    )


DECLINING_FILL_RATE = [
    ("2026-01-03", 0.962),
    ("2026-01-10", 0.958),
    ("2026-01-17", 0.960),
    ("2026-01-24", 0.955),
    ("2026-01-31", 0.950),
    ("2026-02-07", 0.948),
    ("2026-02-14", 0.942),
    ("2026-02-21", 0.940),
    ("2026-02-28", 0.935),
    ("2026-03-07", 0.930),
    ("2026-03-14", 0.925),
    ("2026-03-21", 0.920),
    ("2026-03-28", 0.918),
]

STABLE_COMPLIANCE = [
    ("2026-01-03", 0.880),
    ("2026-01-10", 0.880),
    ("2026-01-17", 0.880),
    ("2026-01-24", 0.880),
    ("2026-01-31", 0.880),
    ("2026-02-07", 0.880),
    ("2026-02-14", 0.880),
    ("2026-02-21", 0.880),
    ("2026-02-28", 0.880),
    ("2026-03-07", 0.880),
    ("2026-03-14", 0.880),
    ("2026-03-21", 0.880),
    ("2026-03-28", 0.880),
]

IMPROVING_OTIF = [
    ("2026-01-03", 0.800),
    ("2026-01-10", 0.810),
    ("2026-01-17", 0.820),
    ("2026-01-24", 0.830),
    ("2026-01-31", 0.840),
    ("2026-02-07", 0.850),
    ("2026-02-14", 0.860),
    ("2026-02-21", 0.870),
    ("2026-02-28", 0.880),
    ("2026-03-07", 0.890),
    ("2026-03-14", 0.900),
    ("2026-03-21", 0.910),
    ("2026-03-28", 0.920),
]


class TestComputeScorecardCurrentValue(unittest.TestCase):
    def test_current_value_is_most_recent_week(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertAlmostEqual(result["FILL_RATE"]["current_value"], 0.918)

    def test_current_value_correct_when_data_unsorted(self):
        weeks_reversed = list(reversed(DECLINING_FILL_RATE))
        df = _make_df("V1001", "FILL_RATE", weeks_reversed)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertAlmostEqual(result["FILL_RATE"]["current_value"], 0.918)


class TestComputeScorecardTrends(unittest.TestCase):
    def test_trend_4w_is_delta_vs_four_weeks_ago(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        # current (2026-03-28) = 0.918, four weeks prior (2026-02-28) = 0.935
        expected = round(0.918 - 0.935, 6)
        self.assertAlmostEqual(result["FILL_RATE"]["trend_4w"], expected, places=5)

    def test_trend_13w_is_delta_vs_thirteen_weeks_ago(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        # current (2026-03-28) = 0.918, 13 weeks prior (2026-01-03) = 0.962
        expected = round(0.918 - 0.962, 6)
        self.assertAlmostEqual(result["FILL_RATE"]["trend_13w"], expected, places=5)

    def test_trend_4w_is_none_when_fewer_than_4_weeks(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE[:3])
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertIsNone(result["FILL_RATE"]["trend_4w"])

    def test_trend_13w_is_none_when_fewer_than_13_weeks(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE[:12])
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertIsNone(result["FILL_RATE"]["trend_13w"])


class TestComputeScorecardTrendDirection(unittest.TestCase):
    def test_declining_metric_is_classified_declining(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertEqual(result["FILL_RATE"]["trend_direction"], "declining")

    def test_stable_metric_is_classified_stable(self):
        df = _make_df("V1001", "LEAD_TIME_COMPLIANCE", STABLE_COMPLIANCE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertEqual(result["LEAD_TIME_COMPLIANCE"]["trend_direction"], "stable")

    def test_improving_metric_is_classified_improving(self):
        df = _make_df("V1001", "OTIF", IMPROVING_OTIF)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertEqual(result["OTIF"]["trend_direction"], "improving")

    def test_insufficient_data_when_only_one_week(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE[:1])
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertEqual(result["FILL_RATE"]["trend_direction"], "insufficient_data")


class TestComputeScorecardMultipleMetrics(unittest.TestCase):
    def test_returns_all_metric_codes_present_in_df(self):
        df = pd.concat([
            _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE),
            _make_df("V1001", "LEAD_TIME_COMPLIANCE", STABLE_COMPLIANCE),
            _make_df("V1001", "OTIF", IMPROVING_OTIF),
        ], ignore_index=True)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        self.assertIn("FILL_RATE", result)
        self.assertIn("LEAD_TIME_COMPLIANCE", result)
        self.assertIn("OTIF", result)

    def test_each_metric_entry_has_required_keys(self):
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=13, config={})
        entry = result["FILL_RATE"]
        for key in ("current_value", "trend_4w", "trend_13w", "trend_direction"):
            self.assertIn(key, entry, f"Missing key: {key}")


class TestComputeScorecardLookback(unittest.TestCase):
    def test_lookback_weeks_limits_history_used(self):
        # With lookback_weeks=4, only last 4 weeks are considered.
        # trend_13w should be None since we don't have 13 weeks in the window.
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=4, config={})
        self.assertIsNone(result["FILL_RATE"]["trend_13w"])

    def test_lookback_weeks_4_trend_4w_is_none(self):
        # A 4-row window only covers 3 calendar weeks of delta; trend_4w requires 5 rows.
        df = _make_df("V1001", "FILL_RATE", DECLINING_FILL_RATE)
        result = compute_scorecard("V1001", df, lookback_weeks=4, config={})
        self.assertIsNone(result["FILL_RATE"]["trend_4w"])


if __name__ == "__main__":
    unittest.main()
