from __future__ import annotations

import unittest

import pandas as pd

from src.data_loader import resolve_vendor_id


class ResolveVendorIdCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vendor_master_df = pd.DataFrame(
            [
                {
                    "vendor_id": "V1001",
                    "vendor_name": "Northstar Foods Co",
                    "primary_category": "Cereal",
                    "secondary_categories": "Breakfast|Pantry",
                },
                {
                    "vendor_id": "V1002",
                    "vendor_name": "Northstar Foods Co",
                    "primary_category": "Snacks",
                    "secondary_categories": None,
                },
            ]
        )

    def test_direct_vendor_id_match_allows_matching_primary_category(self) -> None:
        resolved = resolve_vendor_id("V1001", self.vendor_master_df, category_filter="Cereal")
        self.assertEqual(resolved, "V1001")

    def test_direct_vendor_id_match_allows_matching_secondary_category(self) -> None:
        resolved = resolve_vendor_id("V1001", self.vendor_master_df, category_filter="Pantry")
        self.assertEqual(resolved, "V1001")

    def test_direct_vendor_id_match_rejects_non_matching_category(self) -> None:
        with self.assertRaisesRegex(ValueError, "category_filter 'Frozen'"):
            resolve_vendor_id("V1001", self.vendor_master_df, category_filter="Frozen")

    def test_ambiguous_name_still_raises_before_category_match_shortcuts(self) -> None:
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve_vendor_id("Northstar Foods Co", self.vendor_master_df, category_filter="Cereal")
