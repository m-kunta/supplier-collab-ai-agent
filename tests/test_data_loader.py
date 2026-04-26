from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from src.data_loader import load_manifest


class DataLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_manifest(self, content: str):
        manifest_path = self.data_dir / "manifest.yaml"
        manifest_path.write_text(content, encoding="utf-8")

    def test_load_manifest_valid_yaml_mapping(self):
        self._write_manifest(
            "version: '1.0'\n"
            "environment: test\n"
            "files:\n"
            "  vendor_master:\n"
            "    filename: vendor_master.csv\n"
        )
        manifest = load_manifest(self.data_dir)
        self.assertEqual(manifest["version"], "1.0")
        self.assertEqual(manifest["environment"], "test")
        self.assertEqual(manifest["files"]["vendor_master"]["filename"], "vendor_master.csv")
        self.assertTrue(manifest["_manifest_path"].endswith("manifest.yaml"))
        self.assertEqual(manifest["_resolved_data_dir"], str(self.data_dir.resolve()))

    def test_load_manifest_supports_native_yaml_features(self):
        self._write_manifest(
            "# Real YAML, not JSON-in-YAML\n"
            "defaults: &defaults\n"
            "  refresh_frequency: weekly\n"
            "version: '1.0'\n"
            "environment: test\n"
            "files:\n"
            "  vendor_master:\n"
            "    <<: *defaults\n"
            "    filename: vendor_master.csv\n"
            "    required: true\n"
        )
        manifest = load_manifest(self.data_dir)
        self.assertEqual(manifest["files"]["vendor_master"]["refresh_frequency"], "weekly")
        self.assertIs(manifest["files"]["vendor_master"]["required"], True)

    def test_load_manifest_empty_file_raises_error(self):
        self._write_manifest("")
        with self.assertRaisesRegex(ValueError, "is empty or invalid"):
            load_manifest(self.data_dir)

    def test_load_manifest_comment_only_file_raises_error(self):
        self._write_manifest("# no content\n# just comments\n")
        with self.assertRaisesRegex(ValueError, "is empty or invalid"):
            load_manifest(self.data_dir)

    def test_load_manifest_list_raises_error(self):
        self._write_manifest("- item1\n- item2\n")
        with self.assertRaisesRegex(ValueError, "must be a YAML mapping"):
            load_manifest(self.data_dir)

    def test_load_manifest_string_raises_error(self):
        self._write_manifest("just a random string")
        with self.assertRaisesRegex(ValueError, "must be a YAML mapping"):
            load_manifest(self.data_dir)

    def test_load_manifest_invalid_yaml_bubbles_parser_error(self):
        self._write_manifest("version: [unterminated\n")
        with self.assertRaises(yaml.YAMLError):
            load_manifest(self.data_dir)

    def test_load_dataset_parquet(self):
        from src.data_loader import load_dataset
        import pandas as pd
        from unittest.mock import patch
        
        self._write_manifest(
            "version: '1.0'\n"
            "files:\n"
            "  vendor_master:\n"
            "    filename: vendor_master.parquet\n"
        )
        manifest = load_manifest(self.data_dir)
        
        with patch("pandas.read_parquet", return_value=pd.DataFrame({"col": [1, 2, 3]})):
            loaded = load_dataset(manifest, "vendor_master")
            
        self.assertEqual(len(loaded), 3)

    def test_load_dataset_empty_csv(self):
        from src.data_loader import load_dataset
        
        self._write_manifest(
            "version: '1.0'\n"
            "files:\n"
            "  vendor_master:\n"
            "    filename: vendor_master.csv\n"
        )
        manifest = load_manifest(self.data_dir)
        (self.data_dir / "vendor_master.csv").write_text("", encoding="utf-8")
        
        loaded = load_dataset(manifest, "vendor_master")
        self.assertTrue(loaded.empty)

    def test_load_dataset_row_count_warning(self):
        from src.data_loader import load_dataset
        import pandas as pd
        import logging
        
        self._write_manifest(
            "version: '1.0'\n"
            "files:\n"
            "  vendor_master:\n"
            "    filename: vendor_master.csv\n"
            "    row_count: 5\n"
        )
        manifest = load_manifest(self.data_dir)
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_csv(self.data_dir / "vendor_master.csv", index=False)
        
        with self.assertLogs("src.data_loader", level=logging.WARNING) as log:
            loaded = load_dataset(manifest, "vendor_master")
            
        self.assertEqual(len(loaded), 3)
        self.assertTrue(any("row count mismatch" in record.getMessage() for record in log.records))

if __name__ == "__main__":
    unittest.main()
