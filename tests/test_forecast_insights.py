"""Tests for forecast_insights.compute_forecast_insights."""
from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.forecast_insights import compute_forecast_insights


def _forecast_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputeForecastInsights(unittest.TestCase):
    def test_rolls_up_accuracy_bias_and_underforecast_skus(self):
        forecast = _forecast_df(
            [
                {
                    "sku": "SKU1",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "week_ending": "2026-04-05",
                    "forecast_qty": 100,
                    "actual_qty": 120,
                    "is_promo_period": True,
                },
                {
                    "sku": "SKU2",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "week_ending": "2026-04-12",
                    "forecast_qty": 90,
                    "actual_qty": 81,
                    "is_promo_period": False,
                },
                {
                    "sku": "SKU1",
                    "location_id": "DC2",
                    "vendor_id": "V1001",
                    "week_ending": "2026-04-19",
                    "forecast_qty": 50,
                    "actual_qty": 75,
                    "is_promo_period": True,
                },
                {
                    "sku": "SKU3",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "week_ending": "2026-05-03",
                    "forecast_qty": 60,
                    "actual_qty": 50,
                    "is_promo_period": False,
                },
            ]
        )

        result = compute_forecast_insights(
            "V1001",
            forecast,
            reference_date=date(2026, 4, 21),
        )

        self.assertEqual(result["week_count"], 3)
        self.assertEqual(result["sku_count"], 2)
        self.assertEqual(result["location_count"], 2)
        self.assertAlmostEqual(result["avg_forecast_accuracy_pct"], 0.7963, places=4)
        self.assertAlmostEqual(result["avg_forecast_bias"], -0.1296, places=4)
        self.assertEqual(result["underforecasted_week_count"], 2)
        self.assertEqual(result["overforecasted_week_count"], 1)
        self.assertAlmostEqual(result["promo_period_accuracy_pct"], 0.75, places=4)
        self.assertAlmostEqual(result["non_promo_period_accuracy_pct"], 0.8889, places=4)
        self.assertEqual(result["largest_underforecast_skus"][0]["sku"], "SKU1")
        self.assertEqual(result["largest_underforecast_skus"][0]["shortfall_qty"], 45.0)

    def test_uses_precomputed_accuracy_and_bias_when_present(self):
        forecast = _forecast_df(
            [
                {
                    "sku": "SKU1",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "week_ending": "2026-04-05",
                    "forecast_qty": 100,
                    "actual_qty": 120,
                    "forecast_accuracy_pct": 0.5,
                    "forecast_bias": -0.25,
                    "is_promo_period": False,
                }
            ]
        )

        result = compute_forecast_insights(
            "V1001",
            forecast,
            reference_date=date(2026, 4, 21),
        )

        self.assertEqual(result["avg_forecast_accuracy_pct"], 0.5)
        self.assertEqual(result["avg_forecast_bias"], -0.25)

    def test_empty_or_future_only_data_returns_null_aggregates(self):
        forecast = _forecast_df(
            [
                {
                    "sku": "SKU1",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "week_ending": "2026-05-10",
                    "forecast_qty": 100,
                    "actual_qty": 120,
                    "is_promo_period": False,
                }
            ]
        )

        result = compute_forecast_insights(
            "V1001",
            forecast,
            reference_date=date(2026, 4, 21),
        )

        self.assertEqual(result["week_count"], 0)
        self.assertEqual(result["sku_count"], 0)
        self.assertIsNone(result["avg_forecast_accuracy_pct"])
        self.assertIsNone(result["avg_forecast_bias"])
        self.assertEqual(result["largest_underforecast_skus"], [])


if __name__ == "__main__":
    unittest.main()
