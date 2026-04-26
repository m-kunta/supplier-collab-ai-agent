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
import shutil
from unittest.mock import patch

import pandas as pd
import yaml

from src.agent import AgentPipelineError, summarize_request
from src.config import load_config
from src.data_loader import (
    load_dataset,
    load_manifest,
    load_vendor_data,
    resolve_vendor_id,
)
from src.data_validator import (
    REQUIRED_FILES,
    ValidationResult,
    load_dataset_schema,
    validate_dataset_frame,
    validate_manifest_shape,
)


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


class DatasetSchemaValidationTests(unittest.TestCase):
    def test_load_dataset_schema_returns_yaml_mapping(self):
        schema = load_dataset_schema("vendor_master")
        self.assertEqual(schema["name"], "vendor_master")
        self.assertIn("required_columns", schema)
        self.assertIn("column_types", schema)

    def test_load_dataset_schema_raises_for_unknown_dataset(self):
        with self.assertRaises(FileNotFoundError):
            load_dataset_schema("ghost_dataset")

    def test_load_dataset_schema_rejects_invalid_schema_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp)
            (schema_dir / "bad.schema.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

            with patch("src.data_validator.SCHEMA_DIR", schema_dir):
                with self.assertRaisesRegex(ValueError, "YAML mapping"):
                    load_dataset_schema("bad")

    def test_validate_dataset_frame_accepts_valid_vendor_master_fixture(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        vendor_master_df = load_dataset(manifest, "vendor_master")

        result = validate_dataset_frame("vendor_master", vendor_master_df)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])

    def test_validate_dataset_frame_reports_missing_required_column(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        vendor_master_df = load_dataset(manifest, "vendor_master").drop(
            columns=["vendor_name"]
        )

        result = validate_dataset_frame("vendor_master", vendor_master_df)

        self.assertTrue(result.has_errors)
        self.assertIn("Missing required column: vendor_name", result.errors)

    def test_validate_dataset_frame_reports_invalid_enum_value(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        vendor_master_df = load_dataset(manifest, "vendor_master").copy()
        vendor_master_df.loc[0, "vendor_status"] = "paused"

        result = validate_dataset_frame("vendor_master", vendor_master_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any("vendor_status" in error and "paused" in error for error in result.errors)
        )

    def test_validate_dataset_frame_reports_invalid_date_value(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        purchase_orders_df = load_dataset(manifest, "purchase_orders").copy()
        purchase_orders_df.loc[0, "requested_delivery_date"] = "not-a-date"

        result = validate_dataset_frame("purchase_orders", purchase_orders_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any(
                "requested_delivery_date" in error and "not-a-date" in error
                for error in result.errors
            )
        )

    def test_validate_dataset_frame_reports_pct_metric_above_one(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        performance_df = load_dataset(manifest, "vendor_performance").copy()
        performance_df.loc[0, "metric_uom"] = "pct"
        performance_df.loc[0, "metric_value"] = 1.25

        result = validate_dataset_frame("vendor_performance", performance_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any("metric_value" in error and "between 0 and 1" in error for error in result.errors)
        )

    def test_validate_dataset_frame_reports_negative_numeric_value(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        purchase_orders_df = load_dataset(manifest, "purchase_orders").copy()
        purchase_orders_df.loc[0, "qty_ordered"] = -1

        result = validate_dataset_frame("purchase_orders", purchase_orders_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any("qty_ordered" in error and "below minimum" in error for error in result.errors)
        )

    def test_validate_dataset_frame_reports_non_integer_value(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        purchase_orders_df = load_dataset(manifest, "purchase_orders").copy()
        # Cast to object dtype before injecting a float so pandas doesn't warn
        # about incompatible dtype assignment (FutureWarning → error in pandas 3).
        purchase_orders_df["po_line"] = purchase_orders_df["po_line"].astype(object)
        purchase_orders_df.loc[0, "po_line"] = 1.5

        result = validate_dataset_frame("purchase_orders", purchase_orders_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any("po_line" in error and "invalid integer" in error for error in result.errors)
        )

    def test_validate_dataset_frame_allows_nullable_optional_columns(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        purchase_orders_df = load_dataset(manifest, "purchase_orders").copy()
        purchase_orders_df.loc[0, "ship_to_dc"] = None

        result = validate_dataset_frame("purchase_orders", purchase_orders_df)

        self.assertTrue(result.is_valid)

    def test_validate_dataset_frame_rejects_null_in_non_nullable_column(self):
        manifest = load_manifest(MOCK_DATA_DIR)
        purchase_orders_df = load_dataset(manifest, "purchase_orders").copy()
        purchase_orders_df.loc[0, "qty_ordered"] = None

        result = validate_dataset_frame("purchase_orders", purchase_orders_df)

        self.assertTrue(result.has_errors)
        self.assertTrue(
            any("qty_ordered" in error and "null" in error.lower() for error in result.errors)
        )


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
                {"vendor_id": "V1001", "vendor_name": "Northstar Foods Co"},
                {"vendor_id": "V1002", "vendor_name": "Blue Harbor Pantry"},
                {"vendor_id": "V1003", "vendor_name": "Cedar Peak Provisions"},
            ]
        )

    def test_resolves_canonical_vendor_id_directly(self):
        self.assertEqual(resolve_vendor_id("V1001", self.vendor_master_df), "V1001")

    def test_resolves_vendor_name_case_insensitive(self):
        self.assertEqual(resolve_vendor_id("northstar foods co", self.vendor_master_df), "V1001")
        self.assertEqual(resolve_vendor_id("NORTHSTAR FOODS CO", self.vendor_master_df), "V1001")
        self.assertEqual(resolve_vendor_id("Northstar Foods Co", self.vendor_master_df), "V1001")

    def test_resolves_vendor_name_with_whitespace(self):
        self.assertEqual(resolve_vendor_id("  Northstar Foods Co  ", self.vendor_master_df), "V1001")

    def test_resolves_multi_word_vendor_name(self):
        self.assertEqual(
            resolve_vendor_id("Blue Harbor Pantry", self.vendor_master_df), "V1002"
        )

    def test_raises_value_error_for_unknown_vendor(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_vendor_id("UnknownCo", self.vendor_master_df)
        self.assertIn("UnknownCo", str(ctx.exception))
        self.assertIn("Northstar Foods Co", str(ctx.exception))

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

    def test_mock_vendor_master_resolves_named_vendor(self):
        """Integration check: resolves against the actual mock CSV fixture."""
        manifest = load_manifest(MOCK_DATA_DIR)
        vendor_master_df = load_dataset(manifest, "vendor_master")
        resolved = resolve_vendor_id("Northstar Foods Co", vendor_master_df)
        self.assertEqual(resolved, "V1001")


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class PipelineIntegrationTests(unittest.TestCase):
    """Pipeline integration tests — LLM and file I/O are mocked."""

    _STUB_TEXT = "# Briefing\n\nStub narrative."

    def _run_pipeline(self, **kwargs):
        """Run summarize_request with generate_text and write_output mocked."""
        from unittest.mock import patch
        defaults = dict(
            vendor="Northstar Foods Co",
            meeting_date="2026-04-03",
            data_dir=MOCK_DATA_DIR,
            lookback_weeks=13,
            persona_emphasis="both",
            include_benchmarks=True,
            output_format="md",
            category_filter=None,
        )
        defaults.update(kwargs)
        with patch("src.agent.generate_text", return_value=self._STUB_TEXT):
            with patch("src.agent.write_output", return_value={"md_path": Path("output/stub.md")}):
                return summarize_request(**defaults)

    def _copy_mock_data_dir(self, tmp_path: Path) -> Path:
        target = tmp_path / "landing_zone"
        shutil.copytree(MOCK_DATA_DIR, target)
        return target

    def test_summarize_request_resolves_vendor_name_and_loads_vendor_data(self):
        summary = self._run_pipeline()
        self.assertEqual(summary["vendor_id"], "V1001")
        self.assertEqual(
            sorted(summary["loaded_datasets"]),
            ["oos_events", "promo_calendar", "purchase_orders", "vendor_master", "vendor_performance"],
        )
        self.assertEqual(summary["validation_warnings"], [])
        self.assertTrue(
            any("Loaded 5 dataset(s) for vendor_id 'V1001'." in note for note in summary["pipeline_notes"])
        )
        self.assertIsNotNone(summary["scorecard"])
        self.assertGreater(len(summary["scorecard"]), 0)
        self.assertIn("benchmarks", summary)
        self.assertIsNotNone(summary["po_risk"])
        self.assertIsNotNone(summary["oos_attribution"])
        self.assertIsNotNone(summary["promo_readiness"])
        self.assertIn("validation_report", summary)
        self.assertEqual(summary["validation_report"]["overall_status"], "passed")
        self.assertEqual(summary["validation_report"]["error_count"], 0)
        self.assertEqual(summary["validation_report"]["warning_count"], 0)
        self.assertEqual(
            summary["validation_report"]["datasets"]["vendor_master"]["status"],
            "passed",
        )

    def test_summarize_request_rejects_unknown_vendor(self):
        with self.assertRaisesRegex(AgentPipelineError, "Vendor 'UnknownCo' not found"):
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
        # Create a bad manifest that omits vendor_master completely
        bad_manifest = {"version": "1.0", "environment": "test", "files": {}}
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bad_data_dir = tmp_path / "bad_manifest_dir"
            bad_data_dir.mkdir()
            with open(bad_data_dir / "manifest.yaml", "w") as f:
                yaml.dump(bad_manifest, f)

            # The pipeline should fail entirely before creating any brief
            with self.assertRaisesRegex(AgentPipelineError, "Manifest validation failed"):
                summarize_request(
                    vendor="Northstar Foods Co",
                    meeting_date="2026-04-03",
                    data_dir=bad_data_dir,
                    lookback_weeks=13,
                    persona_emphasis="both",
                    include_benchmarks=True,
                    output_format="md",
                    category_filter=None,
                )

    def test_summarize_request_fails_when_required_dataset_breaks_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self._copy_mock_data_dir(Path(tmp))
            vendor_master_path = data_dir / "vendor_master.csv"
            broken_contents = vendor_master_path.read_text(encoding="utf-8").replace(
                "vendor_status", "vendor_state", 1
            )
            vendor_master_path.write_text(broken_contents, encoding="utf-8")

            with self.assertRaisesRegex(AgentPipelineError, "vendor_master"):
                self._run_pipeline(data_dir=data_dir)

    def test_summarize_request_skips_optional_dataset_with_validation_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self._copy_mock_data_dir(Path(tmp))
            oos_path = data_dir / "oos_events.csv"
            broken_contents = oos_path.read_text(encoding="utf-8").replace(
                "root_cause_code", "root_cause", 1
            )
            oos_path.write_text(broken_contents, encoding="utf-8")

            summary = self._run_pipeline(data_dir=data_dir)

        self.assertTrue(
            any("oos_events" in warning for warning in summary["validation_warnings"])
        )
        self.assertNotIn("oos_events", summary["loaded_datasets"])
        self.assertIsNone(summary["oos_attribution"])
        self.assertEqual(summary["validation_report"]["overall_status"], "warning")
        self.assertEqual(
            summary["validation_report"]["datasets"]["oos_events"]["status"],
            "warning",
        )
        self.assertGreater(
            len(summary["validation_report"]["datasets"]["oos_events"]["warnings"]), 0
        )

    def test_summarize_request_fails_cleanly_when_required_schema_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_data, tempfile.TemporaryDirectory() as tmp_schema:
            data_dir = self._copy_mock_data_dir(Path(tmp_data))
            schema_dir = Path(tmp_schema)
            shutil.copytree(PROJECT_ROOT / "data" / "schemas", schema_dir, dirs_exist_ok=True)
            (schema_dir / "vendor_master.schema.yaml").unlink()

            with patch("src.data_validator.SCHEMA_DIR", schema_dir):
                with self.assertRaisesRegex(AgentPipelineError, "vendor_master"):
                    self._run_pipeline(data_dir=data_dir)

    def test_summarize_request_skips_optional_dataset_when_schema_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_data, tempfile.TemporaryDirectory() as tmp_schema:
            data_dir = self._copy_mock_data_dir(Path(tmp_data))
            schema_dir = Path(tmp_schema)
            shutil.copytree(PROJECT_ROOT / "data" / "schemas", schema_dir, dirs_exist_ok=True)
            (schema_dir / "oos_events.schema.yaml").unlink()

            with patch("src.data_validator.SCHEMA_DIR", schema_dir):
                summary = self._run_pipeline(data_dir=data_dir)

        self.assertTrue(
            any("oos_events" in warning and "Schema file not found" in warning for warning in summary["validation_warnings"])
        )
        self.assertNotIn("oos_events", summary["loaded_datasets"])
        self.assertIsNone(summary["oos_attribution"])


# ---------------------------------------------------------------------------
# Phase 4 end-to-end integration — LLM output mocked
# ---------------------------------------------------------------------------

class Phase4EndToEndTests(unittest.TestCase):
    """Verify the full pipeline with a mocked LLM call.

    The Anthropic API is not called — ``generate_text`` is monkeypatched to
    return a fixed stub string so we can verify:
      - status flips to ``"complete"``
      - briefing_text is populated
      - the markdown output file is written to disk
    """

    _STUB_BRIEFING = (
        "# Supplier Collaboration Briefing — V1001 | 2026-04-03\n\n"
        "## 1. Executive Summary\n\nFill rate is 94 %. All good.\n"
    )

    def test_summarize_request_returns_complete_status_and_briefing_text(self):
        """With generate_text mocked, status==complete and briefing_text is set."""
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp_output:
            with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
                with patch("src.agent.write_output") as mock_write:
                    mock_write.return_value = {"md_path": Path(tmp_output) / "V1001_2026-04-03.md"}
                    summary = summarize_request(
                        vendor="Northstar Foods Co",
                        meeting_date="2026-04-03",
                        data_dir=MOCK_DATA_DIR,
                        lookback_weeks=13,
                        persona_emphasis="both",
                        include_benchmarks=True,
                        output_format="md",
                        category_filter=None,
                    )

        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["briefing_text"], self._STUB_BRIEFING)
        self.assertIsNotNone(summary["scorecard"])

    def test_write_output_called_with_correct_format(self):
        """write_output is invoked once with output_format='md'."""
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp_output:
            with patch("src.agent.generate_text", return_value=self._STUB_BRIEFING):
                with patch("src.agent.write_output") as mock_write:
                    mock_write.return_value = {"md_path": Path(tmp_output) / "V1001_2026-04-03.md"}
                    summarize_request(
                        vendor="Northstar Foods Co",
                        meeting_date="2026-04-03",
                        data_dir=MOCK_DATA_DIR,
                        lookback_weeks=13,
                        persona_emphasis="both",
                        include_benchmarks=True,
                        output_format="md",
                        category_filter=None,
                    )

        mock_write.assert_called_once()
        _, kwargs = mock_write.call_args
        self.assertEqual(kwargs["output_format"], "md")


if __name__ == "__main__":
    unittest.main()
