"""Tests for promo_readiness.compute_promo_readiness.

Data contract:
  - Returns overall_score (0.0–1.0), risk_tier (red/yellow/green), events list.
  - Each event: promo_id, event_name, start_date (str), score, covered_by_po.
  - PO lines count toward coverage when not cancelled and on-time for promo start
    (requested_delivery_date <= start_date, or date missing).
"""

from __future__ import annotations

import unittest

import pandas as pd

from src.promo_readiness import compute_promo_readiness


def _cfg(
    red: float = 0.80,
    yellow: float = 0.95,
) -> dict:
    return {"thresholds": {"promo_readiness_red_threshold": red, "promo_readiness_yellow_threshold": yellow}}


class TestPromoReadinessEmpty(unittest.TestCase):
    def test_empty_promo_calendar_returns_green_with_no_events(self):
        result = compute_promo_readiness(
            "V1001",
            pd.DataFrame(),
            pd.DataFrame(),
            _cfg(),
        )
        self.assertEqual(result["overall_score"], 1.0)
        self.assertEqual(result["risk_tier"], "green")
        self.assertEqual(result["events"], [])


class TestPromoReadinessCoverage(unittest.TestCase):
    def test_full_on_time_coverage_is_green_and_covered(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "Easter",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-04-10",
                    "end_date": "2026-04-20",
                    "promoted_volume": 1000,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 1000,
                    "requested_delivery_date": "2026-04-08",
                    "po_status": "open",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 1.0)
        self.assertEqual(result["risk_tier"], "green")
        self.assertEqual(len(result["events"]), 1)
        self.assertAlmostEqual(result["events"][0]["score"], 1.0)
        self.assertTrue(result["events"][0]["covered_by_po"])

    def test_partial_coverage_mock_like_is_red(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "PRM-001",
                    "event_name": "Easter TPR",
                    "vendor_id": "V1001",
                    "sku": "SKU-001",
                    "start_date": "2026-04-04",
                    "end_date": "2026-04-11",
                    "promoted_volume": 1500,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-9991",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "SKU-001",
                    "qty_ordered": 500,
                    "requested_delivery_date": "2026-04-01",
                    "po_status": "shipped",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 500 / 1500)
        self.assertEqual(result["risk_tier"], "red")
        self.assertFalse(result["events"][0]["covered_by_po"])

    def test_no_pos_is_red_with_zero_score(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "X",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-07",
                    "promoted_volume": 100,
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, pd.DataFrame(), _cfg())
        self.assertAlmostEqual(result["overall_score"], 0.0)
        self.assertEqual(result["risk_tier"], "red")

    def test_cancelled_po_does_not_count(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "X",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-07",
                    "promoted_volume": 100,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 100,
                    "requested_delivery_date": "2026-04-28",
                    "po_status": "cancelled",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 0.0)

    def test_po_after_promo_start_excluded_from_on_time_coverage(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "X",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-07",
                    "promoted_volume": 100,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 100,
                    "requested_delivery_date": "2026-05-05",
                    "po_status": "open",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 0.0)


class TestPromoReadinessTiers(unittest.TestCase):
    def test_yellow_when_score_between_thresholds(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "X",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-07",
                    "promoted_volume": 1000,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 900,
                    "requested_delivery_date": "2026-04-28",
                    "po_status": "open",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 0.9)
        self.assertEqual(result["risk_tier"], "yellow")

    def test_red_strictly_below_red_threshold(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "X",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-07",
                    "promoted_volume": 1000,
                }
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 799,
                    "requested_delivery_date": "2026-04-28",
                    "po_status": "open",
                }
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 0.799)
        self.assertEqual(result["risk_tier"], "red")


class TestPromoReadinessMultiSku(unittest.TestCase):
    def test_two_skus_weighted_by_promoted_volume(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "Combo",
                    "vendor_id": "V1001",
                    "sku": "A",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-07",
                    "promoted_volume": 100,
                },
                {
                    "promo_id": "P1",
                    "event_name": "Combo",
                    "vendor_id": "V1001",
                    "sku": "B",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-07",
                    "promoted_volume": 900,
                },
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "A",
                    "qty_ordered": 100,
                    "requested_delivery_date": "2026-05-28",
                    "po_status": "open",
                },
                {
                    "po_number": "PO-2",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "B",
                    "qty_ordered": 450,
                    "requested_delivery_date": "2026-05-28",
                    "po_status": "open",
                },
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        # A: full, B: 450/900 = 0.5 → (1.0*100 + 0.5*900) / 1000 = 550/1000 = 0.55
        self.assertAlmostEqual(result["overall_score"], 0.55)
        self.assertEqual(result["risk_tier"], "red")
        ev = result["events"][0]
        self.assertEqual(ev["promo_id"], "P1")
        self.assertFalse(ev["covered_by_po"])

    def test_two_events_overall_weighted(self):
        promo = pd.DataFrame(
            [
                {
                    "promo_id": "P1",
                    "event_name": "A",
                    "vendor_id": "V1001",
                    "sku": "X",
                    "start_date": "2026-07-01",
                    "end_date": "2026-07-07",
                    "promoted_volume": 100,
                },
                {
                    "promo_id": "P2",
                    "event_name": "B",
                    "vendor_id": "V1001",
                    "sku": "Y",
                    "start_date": "2026-08-01",
                    "end_date": "2026-08-07",
                    "promoted_volume": 100,
                },
            ]
        )
        po = pd.DataFrame(
            [
                {
                    "po_number": "PO-1",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "X",
                    "qty_ordered": 100,
                    "requested_delivery_date": "2026-06-28",
                    "po_status": "open",
                },
                {
                    "po_number": "PO-2",
                    "po_line": 1,
                    "vendor_id": "V1001",
                    "sku": "Y",
                    "qty_ordered": 100,
                    "requested_delivery_date": "2026-07-28",
                    "po_status": "open",
                },
            ]
        )
        result = compute_promo_readiness("V1001", promo, po, _cfg())
        self.assertAlmostEqual(result["overall_score"], 1.0)
        self.assertEqual(len(result["events"]), 2)


if __name__ == "__main__":
    unittest.main()
