"""Tests for asn_insights.compute_asn_insights."""
from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.asn_insights import compute_asn_insights


def _asn_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputeAsnInsights(unittest.TestCase):
    def test_summarizes_timeliness_accuracy_and_overdue_asns(self):
        asn = _asn_df(
            [
                {
                    "asn_number": "A1",
                    "po_number": "PO1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "ship_date": "2026-04-01",
                    "expected_receipt_date": "2026-04-05",
                    "actual_receipt_date": "2026-04-04",
                    "qty_shipped": 100,
                    "qty_received": 95,
                    "receipt_status": "received",
                },
                {
                    "asn_number": "A2",
                    "po_number": "PO2",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "ship_date": "2026-04-02",
                    "expected_receipt_date": "2026-04-06",
                    "actual_receipt_date": "2026-04-08",
                    "qty_shipped": 200,
                    "qty_received": 180,
                    "receipt_status": "partial",
                },
                {
                    "asn_number": "A3",
                    "po_number": "PO3",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "ship_date": "2026-04-03",
                    "expected_receipt_date": "2026-04-07",
                    "actual_receipt_date": None,
                    "qty_shipped": 50,
                    "qty_received": None,
                    "receipt_status": "overdue",
                },
            ]
        )

        result = compute_asn_insights("V1001", asn, reference_date=date(2026, 4, 10))

        self.assertEqual(result["shipment_count"], 3)
        self.assertEqual(result["received_shipment_count"], 2)
        self.assertEqual(result["overdue_shipment_count"], 1)
        self.assertAlmostEqual(result["avg_receipt_lag_days"], 0.5, places=4)
        self.assertAlmostEqual(result["on_time_receipt_pct"], 0.5, places=4)
        self.assertAlmostEqual(result["fill_in_accuracy_pct"], 0.925, places=4)
        self.assertEqual(result["top_overdue_asns"][0]["asn_number"], "A3")
        self.assertEqual(result["top_overdue_asns"][0]["days_overdue"], 3)

    def test_empty_input_returns_valid_empty_summary(self):
        result = compute_asn_insights("V1001", pd.DataFrame(), reference_date=date(2026, 4, 10))
        self.assertEqual(result["shipment_count"], 0)
        self.assertIsNone(result["avg_receipt_lag_days"])
        self.assertEqual(result["top_overdue_asns"], [])


if __name__ == "__main__":
    unittest.main()
