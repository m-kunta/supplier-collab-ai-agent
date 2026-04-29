"""Tests for inventory_insights.compute_inventory_insights."""
from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.inventory_insights import compute_inventory_insights


def _inventory_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _promo_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputeInventoryInsights(unittest.TestCase):
    def test_returns_summary_and_low_cover_skus(self):
        inventory = _inventory_df(
            [
                {
                    "sku": "SKU1",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "qty_on_hand": 10,
                    "qty_allocated": 2,
                    "qty_in_transit": 5,
                    "qty_on_order": 8,
                    "days_of_supply": 3,
                    "snapshot_date": "2026-04-20",
                },
                {
                    "sku": "SKU2",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "qty_on_hand": 20,
                    "qty_allocated": 1,
                    "qty_in_transit": 0,
                    "qty_on_order": 10,
                    "days_of_supply": 12,
                    "snapshot_date": "2026-04-20",
                },
                {
                    "sku": "SKU3",
                    "location_id": "DC2",
                    "vendor_id": "V1001",
                    "qty_on_hand": 4,
                    "qty_allocated": 0,
                    "qty_in_transit": 2,
                    "qty_on_order": 1,
                    "days_of_supply": 1.5,
                    "snapshot_date": "2026-04-20",
                },
            ]
        )

        result = compute_inventory_insights(
            "V1001",
            inventory,
            pd.DataFrame(),
            reference_date=date(2026, 4, 21),
        )

        self.assertEqual(result["snapshot_date"], "2026-04-20")
        self.assertEqual(result["sku_count"], 3)
        self.assertEqual(result["location_count"], 2)
        self.assertEqual(result["total_on_hand_qty"], 34.0)
        self.assertEqual(result["low_days_of_supply_sku_count"], 2)
        self.assertEqual(
            [row["sku"] for row in result["low_days_of_supply_skus"]],
            ["SKU3", "SKU1"],
        )
        self.assertEqual(result["promo_at_risk_count"], 0)
        self.assertEqual(result["promo_at_risk_events"], [])

    def test_flags_promo_events_with_low_cover_or_insufficient_supply(self):
        inventory = _inventory_df(
            [
                {
                    "sku": "SKU1",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "qty_on_hand": 30,
                    "qty_allocated": 0,
                    "qty_in_transit": 10,
                    "qty_on_order": 5,
                    "days_of_supply": 4,
                    "snapshot_date": "2026-04-20",
                },
                {
                    "sku": "SKU2",
                    "location_id": "DC1",
                    "vendor_id": "V1001",
                    "qty_on_hand": 20,
                    "qty_allocated": 0,
                    "qty_in_transit": 5,
                    "qty_on_order": 0,
                    "days_of_supply": 14,
                    "snapshot_date": "2026-04-20",
                },
            ]
        )
        promo = _promo_df(
            [
                {
                    "promo_event_id": "P1",
                    "promo_name": "Spring Ad",
                    "sku": "SKU1",
                    "inventory_need_date": "2026-04-25",
                    "committed_qty": 60,
                },
                {
                    "promo_event_id": "P2",
                    "promo_name": "Weekend Push",
                    "sku": "SKU2",
                    "inventory_need_date": "2026-04-24",
                    "committed_qty": 40,
                },
                {
                    "promo_event_id": "P3",
                    "promo_name": "Past Event",
                    "sku": "SKU2",
                    "inventory_need_date": "2026-04-01",
                    "committed_qty": 100,
                },
            ]
        )

        result = compute_inventory_insights(
            "V1001",
            inventory,
            promo,
            reference_date=date(2026, 4, 21),
        )

        self.assertEqual(result["promo_at_risk_count"], 2)
        self.assertEqual(
            [row["promo_event_id"] for row in result["promo_at_risk_events"]],
            ["P1", "P2"],
        )
        self.assertEqual(result["promo_at_risk_events"][0]["risk_reasons"], ["low_days_of_supply", "insufficient_total_supply"])
        self.assertEqual(result["promo_at_risk_events"][1]["risk_reasons"], ["insufficient_total_supply"])

    def test_empty_inventory_returns_valid_empty_summary(self):
        result = compute_inventory_insights(
            "V1001",
            pd.DataFrame(),
            pd.DataFrame(),
            reference_date=date(2026, 4, 21),
        )

        self.assertIsNone(result["snapshot_date"])
        self.assertEqual(result["sku_count"], 0)
        self.assertEqual(result["location_count"], 0)
        self.assertEqual(result["low_days_of_supply_sku_count"], 0)
        self.assertEqual(result["low_days_of_supply_skus"], [])
        self.assertEqual(result["promo_at_risk_count"], 0)


if __name__ == "__main__":
    unittest.main()
