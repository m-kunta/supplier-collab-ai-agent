"""Tests for trade_fund_insights.compute_trade_fund_insights."""
from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.trade_fund_insights import compute_trade_fund_insights


def _fund_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestComputeTradeFundInsights(unittest.TestCase):
    def test_summarizes_compliance_expiry_and_at_risk_funds(self):
        funds = _fund_df(
            [
                {
                    "fund_id": "F1",
                    "vendor_id": "V1001",
                    "fund_type": "scan_allowance",
                    "fund_period_start": "2026-04-01",
                    "fund_period_end": "2026-04-25",
                    "committed_amount": 1000.0,
                    "actual_spend": 300.0,
                    "remaining_balance": 700.0,
                    "promo_id": "P1",
                },
                {
                    "fund_id": "F2",
                    "vendor_id": "V1001",
                    "fund_type": "off_invoice",
                    "fund_period_start": "2026-03-01",
                    "fund_period_end": "2026-06-01",
                    "committed_amount": 500.0,
                    "actual_spend": 450.0,
                    "remaining_balance": 50.0,
                    "promo_id": None,
                },
            ]
        )

        result = compute_trade_fund_insights(
            "V1001",
            funds,
            pd.DataFrame(),
            reference_date=date(2026, 4, 10),
        )

        self.assertEqual(result["fund_count"], 2)
        self.assertEqual(result["total_committed_amount"], 1500.0)
        self.assertEqual(result["total_actual_spend"], 750.0)
        self.assertEqual(result["total_remaining_balance"], 750.0)
        self.assertAlmostEqual(result["spend_compliance_pct"], 0.5, places=4)
        self.assertEqual(result["expiring_soon_count"], 1)
        self.assertEqual(result["underutilized_fund_count"], 1)
        self.assertEqual(result["promo_linked_fund_count"], 1)
        self.assertEqual(result["at_risk_funds"][0]["fund_id"], "F1")

    def test_empty_input_returns_valid_empty_summary(self):
        result = compute_trade_fund_insights(
            "V1001", pd.DataFrame(), pd.DataFrame(), reference_date=date(2026, 4, 10)
        )
        self.assertEqual(result["fund_count"], 0)
        self.assertIsNone(result["spend_compliance_pct"])
        self.assertEqual(result["at_risk_funds"], [])


if __name__ == "__main__":
    unittest.main()
