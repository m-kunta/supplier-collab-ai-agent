"""Tests for oos_attribution.compute_oos_attribution.

Data contract under test:
  - Returns a dict with total_oos_events, vendor_controllable, demand_driven,
    unattributed, vendor_controllable_pct, total_units_lost, recurring_skus,
    top_skus.
  - root_cause_code is the primary classification signal.
  - Null root_cause_code + cancelled PO for the same SKU → vendor_controllable.
  - Null root_cause_code without cancelled PO → unattributed.
  - A SKU is recurring when its event count >= oos_recurrence_lookback_count.
"""

import unittest

import pandas as pd

from src.oos_attribution import compute_oos_attribution

# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

VENDOR = "V1001"


def _oos_row(
    sku: str = "SKU-001",
    cause: object = "short_fill",
    units: object = 100.0,
    start: str = "2026-03-01",
) -> dict:
    return {
        "vendor_id": VENDOR,
        "sku": sku,
        "oos_start_date": start,
        "oos_end_date": None,
        "oos_units_lost": units,
        "root_cause_code": cause,
    }


def _oos_df(rows: list) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _po_row(sku: str = "SKU-001", status: str = "open") -> dict:
    return {
        "po_number": "PO-001",
        "po_line": 1,
        "vendor_id": VENDOR,
        "sku": sku,
        "qty_ordered": 100,
        "requested_delivery_date": "2026-04-01",
        "po_status": status,
    }


def _po_df(rows: list) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _cfg(threshold: int = 2) -> dict:
    return {"thresholds": {"oos_recurrence_lookback_count": threshold}}


EMPTY_PO = _po_df([])


# ---------------------------------------------------------------------------
# TestPrimaryClassification
# ---------------------------------------------------------------------------


class TestPrimaryClassification(unittest.TestCase):
    """root_cause_code drives classification directly when present."""

    def _run(self, cause: str) -> dict:
        return compute_oos_attribution(
            VENDOR, _oos_df([_oos_row(cause=cause)]), EMPTY_PO, _cfg()
        )

    def test_short_fill_is_vendor_controllable(self):
        result = self._run("short_fill")
        self.assertEqual(result["vendor_controllable"], 1)
        self.assertEqual(result["demand_driven"], 0)
        self.assertEqual(result["unattributed"], 0)

    def test_late_shipment_is_vendor_controllable(self):
        result = self._run("late_shipment")
        self.assertEqual(result["vendor_controllable"], 1)

    def test_cancelled_po_code_is_vendor_controllable(self):
        result = self._run("cancelled_po")
        self.assertEqual(result["vendor_controllable"], 1)

    def test_demand_spike_is_demand_driven(self):
        result = self._run("demand_spike")
        self.assertEqual(result["demand_driven"], 1)
        self.assertEqual(result["vendor_controllable"], 0)

    def test_forecast_error_is_demand_driven(self):
        result = self._run("forecast_error")
        self.assertEqual(result["demand_driven"], 1)

    def test_unattributed_code_stays_unattributed(self):
        result = self._run("unattributed")
        self.assertEqual(result["unattributed"], 1)
        self.assertEqual(result["vendor_controllable"], 0)
        self.assertEqual(result["demand_driven"], 0)


# ---------------------------------------------------------------------------
# TestNullCauseCrossReference
# ---------------------------------------------------------------------------


class TestNullCauseCrossReference(unittest.TestCase):
    """Secondary PO cross-reference path for null root_cause_code."""

    def test_null_cause_with_cancelled_po_becomes_vendor_controllable(self):
        oos = _oos_df([_oos_row(sku="SKU-001", cause=None)])
        po = _po_df([_po_row(sku="SKU-001", status="cancelled")])
        result = compute_oos_attribution(VENDOR, oos, po, _cfg())
        self.assertEqual(result["vendor_controllable"], 1)
        self.assertEqual(result["unattributed"], 0)

    def test_null_cause_without_cancelled_po_stays_unattributed(self):
        oos = _oos_df([_oos_row(sku="SKU-001", cause=None)])
        po = _po_df([_po_row(sku="SKU-001", status="open")])
        result = compute_oos_attribution(VENDOR, oos, po, _cfg())
        self.assertEqual(result["unattributed"], 1)
        self.assertEqual(result["vendor_controllable"], 0)

    def test_null_cause_empty_po_df_stays_unattributed(self):
        oos = _oos_df([_oos_row(sku="SKU-001", cause=None)])
        result = compute_oos_attribution(VENDOR, oos, EMPTY_PO, _cfg())
        self.assertEqual(result["unattributed"], 1)

    def test_nan_cause_treated_same_as_null(self):
        oos = _oos_df([_oos_row(sku="SKU-001", cause=float("nan"))])
        po = _po_df([_po_row(sku="SKU-001", status="cancelled")])
        result = compute_oos_attribution(VENDOR, oos, po, _cfg())
        self.assertEqual(result["vendor_controllable"], 1)

    def test_primary_code_wins_over_cancelled_po(self):
        """A row with root_cause_code='late_shipment' should NOT be reclassified
        just because the same SKU also has a cancelled PO."""
        oos = _oos_df([_oos_row(sku="SKU-001", cause="late_shipment")])
        po = _po_df([_po_row(sku="SKU-001", status="cancelled")])
        result = compute_oos_attribution(VENDOR, oos, po, _cfg())
        # Still vendor_controllable (via code), not double-counted
        self.assertEqual(result["vendor_controllable"], 1)
        self.assertEqual(result["total_oos_events"], 1)


# ---------------------------------------------------------------------------
# TestCounts
# ---------------------------------------------------------------------------


class TestCounts(unittest.TestCase):
    """Aggregate count correctness across mixed inputs."""

    def test_mixed_causes_counted_correctly(self):
        rows = [
            _oos_row(sku="A", cause="short_fill"),
            _oos_row(sku="A", cause="short_fill"),
            _oos_row(sku="B", cause="demand_spike"),
            _oos_row(sku="C", cause=None),  # no cancelled PO → unattributed
        ]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertEqual(result["vendor_controllable"], 2)
        self.assertEqual(result["demand_driven"], 1)
        self.assertEqual(result["unattributed"], 1)
        self.assertEqual(result["total_oos_events"], 4)

    def test_total_oos_events_matches_row_count(self):
        rows = [_oos_row() for _ in range(5)]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertEqual(result["total_oos_events"], 5)

    def test_unknown_cause_code_is_unattributed(self):
        result = compute_oos_attribution(
            VENDOR,
            _oos_df([_oos_row(cause="alien_abduction")]),
            EMPTY_PO,
            _cfg(),
        )
        self.assertEqual(result["unattributed"], 1)


# ---------------------------------------------------------------------------
# TestVendorControllablePct
# ---------------------------------------------------------------------------


class TestVendorControllablePct(unittest.TestCase):
    def test_pct_computed_correctly(self):
        rows = [
            _oos_row(cause="short_fill"),
            _oos_row(cause="short_fill"),
            _oos_row(cause="short_fill"),
            _oos_row(cause="demand_spike"),
        ]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertAlmostEqual(result["vendor_controllable_pct"], 0.75, places=4)

    def test_pct_is_none_when_empty_df(self):
        result = compute_oos_attribution(VENDOR, _oos_df([]), EMPTY_PO, _cfg())
        self.assertIsNone(result["vendor_controllable_pct"])

    def test_pct_is_zero_when_no_vendor_controllable_events(self):
        rows = [_oos_row(cause="demand_spike"), _oos_row(cause="forecast_error")]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertEqual(result["vendor_controllable_pct"], 0.0)


# ---------------------------------------------------------------------------
# TestUnitsLost
# ---------------------------------------------------------------------------


class TestUnitsLost(unittest.TestCase):
    def test_total_units_lost_sums_non_null_rows(self):
        rows = [
            _oos_row(units=100.0),
            _oos_row(units=50.0),
            _oos_row(units=None),
        ]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertAlmostEqual(result["total_units_lost"], 150.0)

    def test_total_units_lost_is_none_when_all_null(self):
        rows = [_oos_row(units=None), _oos_row(units=None)]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertIsNone(result["total_units_lost"])


# ---------------------------------------------------------------------------
# TestRecurringSkus
# ---------------------------------------------------------------------------


class TestRecurringSkus(unittest.TestCase):
    def test_sku_in_recurring_when_count_gte_threshold(self):
        rows = [_oos_row(sku="SKU-001") for _ in range(3)]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg(threshold=2))
        self.assertIn("SKU-001", result["recurring_skus"])

    def test_sku_not_in_recurring_when_below_threshold(self):
        rows = [_oos_row(sku="SKU-001")]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg(threshold=2))
        self.assertNotIn("SKU-001", result["recurring_skus"])

    def test_recurring_skus_list_is_sorted(self):
        rows = (
            [_oos_row(sku="SKU-C")] * 3
            + [_oos_row(sku="SKU-A")] * 3
            + [_oos_row(sku="SKU-B")] * 3
        )
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg(threshold=2))
        self.assertEqual(result["recurring_skus"], sorted(result["recurring_skus"]))

    def test_config_threshold_respected(self):
        rows = [_oos_row(sku="SKU-001")] * 2
        # threshold=3 means 2 events is NOT enough
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg(threshold=3))
        self.assertNotIn("SKU-001", result["recurring_skus"])


# ---------------------------------------------------------------------------
# TestTopSkus
# ---------------------------------------------------------------------------


class TestTopSkus(unittest.TestCase):
    def test_top_skus_sorted_by_count_descending(self):
        rows = (
            [_oos_row(sku="SKU-A")] * 3
            + [_oos_row(sku="SKU-B")]
        )
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        top = result["top_skus"]
        self.assertEqual(top[0]["sku"], "SKU-A")
        self.assertEqual(top[0]["oos_count"], 3)
        self.assertEqual(top[1]["sku"], "SKU-B")
        self.assertEqual(top[1]["oos_count"], 1)

    def test_top_skus_primary_cause_is_mode(self):
        rows = [
            _oos_row(sku="SKU-A", cause="short_fill"),
            _oos_row(sku="SKU-A", cause="short_fill"),
            _oos_row(sku="SKU-A", cause="demand_spike"),
        ]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        top_entry = result["top_skus"][0]
        self.assertEqual(top_entry["primary_cause"], "vendor_controllable")

    def test_top_skus_is_recurring_flag_set(self):
        rows = [_oos_row(sku="SKU-A")] * 3 + [_oos_row(sku="SKU-B")]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg(threshold=2))
        by_sku = {e["sku"]: e for e in result["top_skus"]}
        self.assertTrue(by_sku["SKU-A"]["is_recurring"])
        self.assertFalse(by_sku["SKU-B"]["is_recurring"])

    def test_top_skus_limited_to_five(self):
        # 7 distinct SKUs, 1 event each
        rows = [_oos_row(sku=f"SKU-{i:03d}") for i in range(7)]
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, _cfg())
        self.assertLessEqual(len(result["top_skus"]), 5)

    def test_top_skus_empty_when_no_events(self):
        result = compute_oos_attribution(VENDOR, _oos_df([]), EMPTY_PO, _cfg())
        self.assertEqual(result["top_skus"], [])


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases(unittest.TestCase):
    def test_empty_oos_df_returns_zero_shape(self):
        result = compute_oos_attribution(VENDOR, _oos_df([]), EMPTY_PO, _cfg())
        self.assertEqual(result["total_oos_events"], 0)
        self.assertEqual(result["vendor_controllable"], 0)
        self.assertEqual(result["demand_driven"], 0)
        self.assertEqual(result["unattributed"], 0)
        self.assertEqual(result["recurring_skus"], [])
        self.assertEqual(result["top_skus"], [])
        self.assertIsNone(result["vendor_controllable_pct"])
        self.assertIsNone(result["total_units_lost"])

    def test_missing_required_column_raises_value_error(self):
        bad_df = pd.DataFrame([{"vendor_id": VENDOR, "sku": "SKU-001"}])
        with self.assertRaises(ValueError):
            compute_oos_attribution(VENDOR, bad_df, EMPTY_PO, _cfg())

    def test_po_df_missing_sku_column_does_not_crash(self):
        oos = _oos_df([_oos_row(cause=None)])
        bad_po = pd.DataFrame([{"vendor_id": VENDOR, "po_status": "cancelled"}])
        result = compute_oos_attribution(VENDOR, oos, bad_po, _cfg())
        # Can't cross-reference SKU → stays unattributed
        self.assertEqual(result["unattributed"], 1)

    def test_cause_with_whitespace_and_mixed_case_normalized(self):
        oos = _oos_df([_oos_row(cause="  Short_Fill  ")])
        result = compute_oos_attribution(VENDOR, oos, EMPTY_PO, _cfg())
        self.assertEqual(result["vendor_controllable"], 1)

    def test_empty_config_uses_defaults(self):
        rows = [_oos_row(sku="SKU-001")] * 2
        # Should default to recurrence_threshold=2 → SKU-001 is recurring
        result = compute_oos_attribution(VENDOR, _oos_df(rows), EMPTY_PO, {})
        self.assertIn("SKU-001", result["recurring_skus"])


# ---------------------------------------------------------------------------
# TestReturnShape
# ---------------------------------------------------------------------------


class TestReturnShape(unittest.TestCase):
    REQUIRED_KEYS = {
        "total_oos_events",
        "vendor_controllable",
        "demand_driven",
        "unattributed",
        "vendor_controllable_pct",
        "total_units_lost",
        "recurring_skus",
        "top_skus",
    }

    def test_all_required_keys_present(self):
        result = compute_oos_attribution(
            VENDOR,
            _oos_df([_oos_row()]),
            EMPTY_PO,
            _cfg(),
        )
        self.assertEqual(self.REQUIRED_KEYS, self.REQUIRED_KEYS & result.keys())

    def test_top_skus_entry_has_required_fields(self):
        result = compute_oos_attribution(
            VENDOR,
            _oos_df([_oos_row()]),
            EMPTY_PO,
            _cfg(),
        )
        entry = result["top_skus"][0]
        for field in ("sku", "oos_count", "primary_cause", "is_recurring"):
            self.assertIn(field, entry)


if __name__ == "__main__":
    unittest.main()
