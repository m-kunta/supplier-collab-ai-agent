"""Tests for chargeback_insights.compute_chargeback_insights."""
from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.chargeback_insights import compute_chargeback_insights


def _chargeback_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputeChargebackInsights(unittest.TestCase):
    def test_summarizes_amounts_types_and_recent_open_items(self):
        chargebacks = _chargeback_df(
            [
                {
                    "chargeback_id": "C1",
                    "vendor_id": "V1001",
                    "issue_date": "2026-04-01",
                    "chargeback_type": "compliance",
                    "chargeback_amount": 120.0,
                    "dispute_status": "open",
                    "po_number": "PO1",
                },
                {
                    "chargeback_id": "C2",
                    "vendor_id": "V1001",
                    "issue_date": "2026-04-03",
                    "chargeback_type": "damage",
                    "chargeback_amount": 80.0,
                    "dispute_status": "disputed",
                    "po_number": "PO2",
                },
                {
                    "chargeback_id": "C3",
                    "vendor_id": "V1001",
                    "issue_date": "2026-04-05",
                    "chargeback_type": "compliance",
                    "chargeback_amount": 60.0,
                    "dispute_status": "resolved",
                    "po_number": "PO3",
                },
            ]
        )

        result = compute_chargeback_insights(
            "V1001", chargebacks, reference_date=date(2026, 4, 10)
        )

        self.assertEqual(result["chargeback_count"], 3)
        self.assertEqual(result["total_chargeback_amount"], 260.0)
        self.assertEqual(result["open_chargeback_amount"], 120.0)
        self.assertEqual(result["disputed_chargeback_amount"], 80.0)
        self.assertEqual(result["most_recent_issue_date"], "2026-04-05")
        self.assertEqual(result["top_chargeback_types"][0]["chargeback_type"], "compliance")
        self.assertEqual(result["top_chargeback_types"][0]["count"], 2)
        self.assertEqual(len(result["recent_open_chargebacks"]), 2)

    def test_empty_input_returns_valid_empty_summary(self):
        result = compute_chargeback_insights(
            "V1001", pd.DataFrame(), reference_date=date(2026, 4, 10)
        )
        self.assertEqual(result["chargeback_count"], 0)
        self.assertIsNone(result["most_recent_issue_date"])
        self.assertEqual(result["recent_open_chargebacks"], [])


if __name__ == "__main__":
    unittest.main()
