import csv
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import generate_mock_csvs as gm


class GenerateMockCsvsTests(unittest.TestCase):
    def test_build_vendor_master_rows_returns_multiple_fictional_vendors(self):
        rows = gm.build_vendor_master_rows(vendor_count=6)

        self.assertEqual(len(rows), 6)
        self.assertEqual(len({row['vendor_id'] for row in rows}), 6)
        names = {row['vendor_name'] for row in rows}
        self.assertNotIn('Kelloggs', names)
        self.assertNotIn('General Mills', names)

    def test_generate_mock_data_writes_consistent_manifest_for_multiple_vendors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            counts = gm.generate_mock_data(output_dir=Path(tmpdir), vendor_count=5)

            manifest_path = Path(tmpdir) / 'manifest.yaml'
            self.assertTrue(manifest_path.exists())

            with manifest_path.open('r', encoding='utf-8') as f:
                manifest = yaml.safe_load(f)

            self.assertEqual(manifest['files']['vendor_master']['row_count'], 5)
            self.assertEqual(manifest['files']['purchase_orders']['row_count'], counts['purchase_orders'])
            self.assertEqual(manifest['files']['vendor_performance']['row_count'], counts['vendor_performance'])

            with (Path(tmpdir) / 'vendor_master.csv').open('r', encoding='utf-8', newline='') as f:
                vm_rows = list(csv.DictReader(f))
            with (Path(tmpdir) / 'purchase_orders.csv').open('r', encoding='utf-8', newline='') as f:
                po_rows = list(csv.DictReader(f))

            vendor_ids = {row['vendor_id'] for row in vm_rows}
            self.assertEqual(len(vendor_ids), 5)
            self.assertTrue(all(row['vendor_id'] in vendor_ids for row in po_rows))


if __name__ == '__main__':
    unittest.main()
