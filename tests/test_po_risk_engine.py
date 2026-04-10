"""Tests for po_risk_engine.compute_po_risk.

Data contract under test:
  - Returns a dict with 'summary' (red/yellow/green/total counts) and 'line_items'.
  - Each line_item has: po_number, po_line, sku, requested_delivery_date,
    po_status, days_late, risk_tier.
  - risk_tier is 'red' when days_late > red_threshold, 'yellow' when
    > yellow_threshold, else 'green'.
  - days_late is computed against today for open/shipped POs,
    against actual_receipt_date for received POs.
"""

from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.po_risk_engine import compute_po_risk


TODAY = date(2026, 4, 9)


def _po_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputePORiskTiers(unittest.TestCase):
    def test_open_po_4_days_late_is_red(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-001",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-001",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "red")

    def test_open_po_2_days_late_is_yellow(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-002",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-002",
                    "requested_delivery_date": "2026-04-07",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["yellow"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "yellow")

    def test_open_po_1_day_late_is_yellow(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-003",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-003",
                    "requested_delivery_date": "2026-04-08",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["yellow"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "yellow")

    def test_open_po_today_is_green(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-004",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-004",
                    "requested_delivery_date": "2026-04-09",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["green"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "green")

    def test_open_po_future_date_is_green(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-005",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-005",
                    "requested_delivery_date": "2026-04-15",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["green"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "green")

    def test_shipped_po_late_is_tiered(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-006",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-006",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "shipped",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "red")


class TestComputePORiskReceivedPOs(unittest.TestCase):
    def test_received_po_late_by_actual_receipt_date_is_red(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-007",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-007",
                    "requested_delivery_date": "2026-04-01",
                    "actual_receipt_date": "2026-04-06",
                    "po_status": "received",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["line_items"][0]["days_late"], 5.0)
        self.assertEqual(result["line_items"][0]["risk_tier"], "red")

    def test_received_po_early_is_green(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-008",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-008",
                    "requested_delivery_date": "2026-04-10",
                    "actual_receipt_date": "2026-04-07",
                    "po_status": "received",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["green"], 1)
        self.assertEqual(result["line_items"][0]["days_late"], -3.0)
        self.assertEqual(result["line_items"][0]["risk_tier"], "green")

    def test_received_po_no_actual_receipt_date_uses_today_for_open_behavior(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-009",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-009",
                    "requested_delivery_date": "2026-04-01",
                    "po_status": "received",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["line_items"][0]["days_late"], 8.0)


class TestComputePORiskThresholds(unittest.TestCase):
    def test_custom_thresholds_honored_for_red(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-010",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-010",
                    "requested_delivery_date": "2026-04-07",
                    "po_status": "open",
                }
            ]
        )
        config = {
            "thresholds": {"po_risk_days_late_red": 5, "po_risk_days_late_yellow": 2}
        }
        result = compute_po_risk("V1001", df, config=config, reference_date=TODAY)
        self.assertEqual(result["summary"]["yellow"], 1)
        self.assertEqual(result["line_items"][0]["risk_tier"], "yellow")

    def test_custom_thresholds_honored_for_yellow_boundary(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-011",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-011",
                    "requested_delivery_date": "2026-04-07",
                    "po_status": "open",
                }
            ]
        )
        config = {
            "thresholds": {"po_risk_days_late_red": 3, "po_risk_days_late_yellow": 1}
        }
        result = compute_po_risk("V1001", df, config=config, reference_date=TODAY)
        self.assertEqual(result["summary"]["yellow"], 1)
        self.assertEqual(result["line_items"][0]["days_late"], 2.0)

    def test_strict_thresholds_collapse_yellow_band(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-012",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-012",
                    "requested_delivery_date": "2026-04-09",
                    "po_status": "open",
                }
            ]
        )
        config = {
            "thresholds": {"po_risk_days_late_red": 1, "po_risk_days_late_yellow": 0}
        }
        result = compute_po_risk("V1001", df, config=config, reference_date=TODAY)
        self.assertEqual(result["summary"]["green"], 1)


class TestComputePORiskMultipleLines(unittest.TestCase):
    def test_mixed_tiers_counted_correctly(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-A",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-A",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "open",
                },
                {
                    "po_number": "PO-B",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-B",
                    "requested_delivery_date": "2026-04-07",
                    "po_status": "open",
                },
                {
                    "po_number": "PO-C",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-C",
                    "requested_delivery_date": "2026-04-11",
                    "po_status": "open",
                },
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["summary"]["yellow"], 1)
        self.assertEqual(result["summary"]["green"], 1)
        self.assertEqual(result["summary"]["total"], 3)

    def test_multiple_lines_same_po_are_all_returned(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-M",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-1",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "open",
                },
                {
                    "po_number": "PO-M",
                    "po_line": 2,
                    "vendor_id": "V1001",
                    "sku": "SKU-2",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "open",
                },
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(len(result["line_items"]), 2)
        self.assertEqual(result["line_items"][0]["po_line"], 1)
        self.assertEqual(result["line_items"][1]["po_line"], 2)


class TestComputePORiskEdgeCases(unittest.TestCase):
    def test_empty_dataframe_returns_zeros(self):
        df = _po_df([])
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 0)
        self.assertEqual(result["summary"]["yellow"], 0)
        self.assertEqual(result["summary"]["green"], 0)
        self.assertEqual(result["summary"]["total"], 0)
        self.assertEqual(result["line_items"], [])

    def test_missing_po_status_defaults_to_open(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-E1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-E1",
                    "requested_delivery_date": "2026-04-05",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)
        self.assertEqual(result["line_items"][0]["po_status"], "open")

    def test_missing_requested_delivery_date_handled_gracefully(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-E2",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-E2",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["line_items"][0]["days_late"], 0.0)

    def test_status_case_insensitive(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-E3",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-E3",
                    "requested_delivery_date": "2026-04-05",
                    "po_status": "OPEN",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        self.assertEqual(result["summary"]["red"], 1)


class TestComputePORiskLineItemFields(unittest.TestCase):
    def test_line_item_contains_all_required_fields(self):
        df = _po_df(
            [
                {
                    "po_number": "PO-F1",
                    "po_line": 3,
                    "vendor_id": "V1001",
                    "sku": "SKU-F1",
                    "requested_delivery_date": "2026-04-07",
                    "po_status": "open",
                }
            ]
        )
        result = compute_po_risk("V1001", df, config={}, reference_date=TODAY)
        item = result["line_items"][0]
        for key in (
            "po_number",
            "po_line",
            "sku",
            "requested_delivery_date",
            "po_status",
            "days_late",
            "risk_tier",
        ):
            self.assertIn(key, item, f"Missing field: {key}")
        self.assertEqual(item["po_number"], "PO-F1")
        self.assertEqual(item["po_line"], 3)
        self.assertEqual(item["sku"], "SKU-F1")
        self.assertEqual(item["days_late"], 2.0)
        self.assertEqual(item["risk_tier"], "yellow")


if __name__ == "__main__":
    unittest.main()
