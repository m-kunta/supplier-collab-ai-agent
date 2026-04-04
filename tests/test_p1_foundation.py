"""Phase 1 foundation tests.

Covers:
- config.py error paths (empty config, non-mapping config)
- data_validator.py: ValidationResult behaviour and validate_manifest_shape edge cases
- data_loader.py: load_dataset, load_vendor_data, resolve_vendor_id
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.agent import summarize_request
from src.config import load_config
from src.data_loader import (
    load_dataset,
    load_manifest,
    load_vendor_data,
    resolve_vendor_id,
)
from src.data_validator import REQUIRED_FILES, ValidationResult, validate_manifest_shape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_DIR = PROJECT_ROOT / "data" / "inbound" / "mock"


# ---------------------------------------------------------------------------
# config.py error paths
# ---------------------------------------------------------------------------

class ConfigErrorPathTests(unittest.TestCase):
    def _write_config(self, tmp_dir: str, content: str) -> Path:
        path = Path(tmp_dir) / "agent_config.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_config_empty_file_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_config(tmp, "")
            with self.assertRaisesRegex(ValueError, "empty or invalid"):
                load_config(path)

    def test_load_config_comment_only_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_config(tmp, "# only comments\n")
            with self.assertRaisesRegex(ValueError, "empty or invalid"):
                load_config(path)

    def test_load_config_list_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_config(tmp, "- item1\n- item2\n")
            with self.assertRaisesRegex(ValueError, "must be a YAML mapping"):
                load_config(path)

    def test_load_config_plain_string_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_config(tmp, "just a string")
            with self.assertRaisesRegex(ValueError, "must be a YAML mapping"):
                load_config(path)

    def test_load_config_returns_dict_for_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_config(
                tmp,
                "defaults:\n  lookback_weeks: 4\nllm:\n  default_provider: openai\n",
            )
            config = load_config(path)
            self.assertIsInstance(config, dict)
            self.assertEqual(config["defaults"]["lookback_weeks"], 4)


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------

class ValidationResultTests(unittest.TestCase):
    def test_empty_result_is_valid(self):
        result = ValidationResult()
        self.assertTrue(result.is_valid)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_result_with_errors_is_not_valid(self):
        result = ValidationResult(errors=["Missing key: files"])
        self.assertFalse(result.is_valid)
        self.assertTrue(result.has_errors)

    def test_result_with_warnings_only_is_still_valid(self):
        result = ValidationResult(warnings=["Data is 3 days stale"])
        self.assertTrue(result.is_valid)
        self.assertFalse(result.has_errors)

    def test_result_with_both_is_not_valid(self):
        result = ValidationResult(
            errors=["Missing key: files"],
            warnings=["Data is stale"],
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(result.has_errors)

    def test_repr_includes_counts_and_validity(self):
        result = ValidationResult(errors=["e1", "e2"], warnings=["w1"])
        r = repr(result)
        self.assertIn("errors=2", r)
        self.assertIn("warnings=1", r)
        self.assertIn("is_valid=False", r)


# ---------------------------------------------------------------------------
# validate_manifest_shape
# ---------------------------------------------------------------------------

class ValidateManifestShapeTests(unittest.TestCase):
    def _full_manifest(self) -> dict:
        return {
            "version": "1.0",
            "environment": "test",
            "files": {
                "vendor_master": {"filename": "vendor_master.csv"},
                "purchase_orders": {"filename": "purchase_orders.csv"},
                "vendor_performance": {"filename": "vendor_performance.csv"},
            },
        }

    def test_valid_manifest_returns_no_errors(self):
        result = validate_manifest_shape(self._full_manifest())
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])

    def test_missing_files_key_is_reported_as_error(self):
        manifest = {"version": "1.0", "environment": "test"}
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertIn("Missing manifest key: files", result.errors)

    def test_missing_version_key_is_reported_as_error(self):
        manifest = {"environment": "test", "files": {}}
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertIn("Missing manifest key: version", result.errors)

    def test_missing_environment_key_is_reported_as_error(self):
        manifest = {"version": "1.0", "files": {}}
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertIn("Missing manifest key: environment", result.errors)

    def test_multiple_missing_keys_all_reported(self):
        result = validate_manifest_shape({})
        self.assertEqual(len(result.errors), 3)

    def test_private_keys_do_not_interfere_with_validation(self):
        """load_manifest() injects _resolved_data_dir and _manifest_path."""
        manifest = self._full_manifest()
        manifest["_resolved_data_dir"] = "/some/path"
        manifest["_manifest_path"] = "/some/path/manifest.yaml"
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.is_valid)

    def test_extra_public_keys_are_tolerated(self):
        manifest = self._full_manifest()
        manifest["benchmarks"] = {"bic_percentile": 90}
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.is_valid)

    def test_missing_required_file_in_manifest_is_reported_as_error(self):
        manifest = self._full_manifest()
        del manifest["files"]["vendor_master"]
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertIn("Missing required file in manifest: vendor_master", result.errors)

    def test_all_three_required_files_missing_produces_three_errors(self):
        manifest = {"version": "1.0", "environment": "test", "files": {}}
        result = validate_manifest_shape(manifest)
        self.assertEqual(len(result.errors), 3)
        for name in REQUIRED_FILES:
            self.assertIn(f"Missing required file in manifest: {name}", result.errors)

    def test_optional_files_alone_do_not_satisfy_required_file_check(self):
        manifest = {
            "version": "1.0",
            "environment": "test",
            "files": {"oos_events": {"filename": "oos_events.csv"}},
        }
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.errors), 3)

    def test_required_files_check_skipped_when_files_key_is_absent(self):
        """Shape errors take precedence; no KeyError when 'files' key is missing."""
        manifest = {"version": "1.0", "environment": "test"}
        result = validate_manifest_shape(manifest)
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.errors), 1)  # only the missing 'files' key error


# ---------------------------------------------------------------------------
# load_dataset and load_vendor_data
# ---------------------------------------------------------------------------

class LoadDatasetTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MOCK_DATA_DIR)

    def test_load_dataset_returns_dataframe_for_vendor_master(self):
        df = load_dataset(self.manifest, "vendor_master")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("vendor_id", df.columns)

    def test_load_dataset_raises_key_error_for_unknown_dataset(self):
        with self.assertRaises(KeyError) as ctx:
            load_dataset(self.manifest, "nonexistent_dataset")
        self.assertIn("nonexistent_dataset", str(ctx.exception))

    def test_load_dataset_raises_file_not_found_for_missing_csv(self):
        import copy
        manifest_copy = copy.deepcopy(self.manifest)
        manifest_copy["files"]["ghost"] = {"filename": "does_not_exist.csv"}
        with self.assertRaises(FileNotFoundError):
            load_dataset(manifest_copy, "ghost")

    def test_load_vendor_data_returns_all_three_required_datasets(self):
        data = load_vendor_data(self.manifest, "V1001")
        self.assertIn("vendor_master", data)
        self.assertIn("purchase_orders", data)
        self.assertIn("vendor_performance", data)

    def test_load_vendor_data_filters_to_vendor_id(self):
        data = load_vendor_data(self.manifest, "V1001")
        for dataset_name, df in data.items():
            if "vendor_id" in df.columns:
                unique_ids = df["vendor_id"].unique().tolist()
                self.assertEqual(
                    unique_ids,
                    ["V1001"],
                    f"Dataset '{dataset_name}' contains unexpected vendor IDs: {unique_ids}",
                )

    def test_load_vendor_data_unknown_vendor_returns_empty_dfs(self):
        data = load_vendor_data(self.manifest, "UNKNOWN_VENDOR")
        for dataset_name, df in data.items():
            if "vendor_id" in df.columns:
                self.assertEqual(
                    len(df),
                    0,
                    f"Expected empty DataFrame for '{dataset_name}' with unknown vendor",
                )


# ---------------------------------------------------------------------------
# resolve_vendor_id
# ---------------------------------------------------------------------------

class ResolveVendorIdTests(unittest.TestCase):
    def setUp(self):
        self.vendor_master_df = pd.DataFrame(
            [
                {"vendor_id": "V1001", "vendor_name": "Kelloggs"},
                {"vendor_id": "V1002", "vendor_name": "General Mills"},
                {"vendor_id": "V1003", "vendor_name": "Quaker Oats"},
            ]
        )

    def test_resolves_canonical_vendor_id_directly(self):
        self.assertEqual(resolve_vendor_id("V1001", self.vendor_master_df), "V1001")

    def test_resolves_vendor_name_case_insensitive(self):
        self.assertEqual(resolve_vendor_id("kelloggs", self.vendor_master_df), "V1001")
        self.assertEqual(resolve_vendor_id("KELLOGGS", self.vendor_master_df), "V1001")
        self.assertEqual(resolve_vendor_id("Kelloggs", self.vendor_master_df), "V1001")

    def test_resolves_vendor_name_with_whitespace(self):
        self.assertEqual(resolve_vendor_id("  Kelloggs  ", self.vendor_master_df), "V1001")

    def test_resolves_multi_word_vendor_name(self):
        self.assertEqual(
            resolve_vendor_id("General Mills", self.vendor_master_df), "V1002"
        )

    def test_raises_value_error_for_unknown_vendor(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_vendor_id("UnknownCo", self.vendor_master_df)
        self.assertIn("UnknownCo", str(ctx.exception))
        self.assertIn("Kelloggs", str(ctx.exception))

    def test_raises_value_error_for_ambiguous_name(self):
        ambiguous_df = pd.DataFrame(
            [
                {"vendor_id": "V9001", "vendor_name": "Duplicate"},
                {"vendor_id": "V9002", "vendor_name": "Duplicate"},
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            resolve_vendor_id("Duplicate", ambiguous_df)
        self.assertIn("ambiguous", str(ctx.exception))

    def test_mock_vendor_master_resolves_kelloggs(self):
        """Integration check: resolves against the actual mock CSV fixture."""
        manifest = load_manifest(MOCK_DATA_DIR)
        vendor_master_df = load_dataset(manifest, "vendor_master")
        resolved = resolve_vendor_id("Kelloggs", vendor_master_df)
        self.assertEqual(resolved, "V1001")


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class PipelineIntegrationTests(unittest.TestCase):
    def test_summarize_request_resolves_vendor_name_and_loads_vendor_data(self):
        summary = summarize_request(
            vendor="Kelloggs",
            meeting_date="2026-04-03",
            data_dir=MOCK_DATA_DIR,
            lookback_weeks=13,
            persona_emphasis="both",
            include_benchmarks=True,
            output_format="md",
            category_filter=None,
        )
        self.assertEqual(summary["vendor_id"], "V1001")
        self.assertEqual(
            sorted(summary["loaded_datasets"]),
            ["oos_events", "promo_calendar", "purchase_orders", "vendor_master", "vendor_performance"],
        )
        self.assertEqual(summary["validation_warnings"], [])
        self.assertTrue(
            any("Loaded 5 dataset(s) for vendor_id 'V1001'." in note for note in summary["pipeline_notes"])
        )

    def test_summarize_request_rejects_unknown_vendor(self):
        with self.assertRaisesRegex(ValueError, "Vendor 'UnknownCo' not found"):
            summarize_request(
                vendor="UnknownCo",
                meeting_date="2026-04-03",
                data_dir=MOCK_DATA_DIR,
                lookback_weeks=13,
                persona_emphasis="both",
                include_benchmarks=True,
                output_format="md",
                category_filter=None,
            )

    def test_summarize_request_fails_when_vendor_master_missing_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "manifest.yaml").write_text(
                "version: '1.0'\n"
                "environment: test\n"
                "files:\n"
                "  purchase_orders:\n"
                "    filename: purchase_orders.csv\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "vendor_master"):
                summarize_request(
                    vendor="Kelloggs",
                    meeting_date="2026-04-03",
                    data_dir=tmp_path,
                    lookback_weeks=13,
                    persona_emphasis="both",
                    include_benchmarks=True,
                    output_format="md",
                    category_filter=None,
                )


if __name__ == "__main__":
    unittest.main()
