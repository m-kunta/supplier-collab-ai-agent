from __future__ import annotations

import csv
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import yaml

from cli import build_parser
from src.llm_providers import generate_text, resolve_provider


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_DIR = PROJECT_ROOT / "data" / "inbound" / "mock"
SCHEMA_DIR = PROJECT_ROOT / "data" / "schemas"


class CliContractTests(unittest.TestCase):
    def test_parser_defaults_match_scaffold_expectations(self):
        parser = build_parser()
        args = parser.parse_args(["--vendor", "Kelloggs", "--date", "2026-04-03"])
        self.assertEqual(args.data_dir, "data/inbound/mock")
        self.assertEqual(args.lookback_weeks, 13)
        self.assertEqual(args.persona_emphasis, "both")
        self.assertTrue(args.include_benchmarks)
        self.assertEqual(args.output_format, "md")
        self.assertIsNone(args.category_filter)

    def test_parser_supports_disabling_benchmarks(self):
        parser = build_parser()
        args = parser.parse_args(
            ["--vendor", "Kelloggs", "--date", "2026-04-03", "--no-include-benchmarks"]
        )
        self.assertFalse(args.include_benchmarks)


class ProviderSelectionTests(unittest.TestCase):
    def test_resolve_provider_uses_environment_overrides(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": " openai ", "LLM_MODEL": "gpt-4.1-mini"}):
            selection = resolve_provider()
        self.assertEqual(selection.provider, "openai")
        self.assertEqual(selection.model, "gpt-4.1-mini")

    def test_resolve_provider_rejects_unknown_provider(self):
        with self.assertRaisesRegex(ValueError, "Unsupported provider 'unknown'"):
            resolve_provider("unknown", None)

    def test_generate_text_reports_selected_provider_and_prompt_size(self):
        result = generate_text("hello world", provider="groq", model="llama-test")
        self.assertIn("provider=groq", result)
        self.assertIn("model=llama-test", result)
        self.assertIn("prompt_chars=11", result)


class DataFixtureIntegrityTests(unittest.TestCase):
    def test_mock_manifest_is_valid_yaml_mapping(self):
        manifest = yaml.safe_load((MOCK_DATA_DIR / "manifest.yaml").read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict)
        self.assertEqual(manifest["environment"], "mock")
        self.assertIn("files", manifest)

    def test_manifest_declared_files_exist_and_row_counts_match(self):
        manifest = yaml.safe_load((MOCK_DATA_DIR / "manifest.yaml").read_text(encoding="utf-8"))
        for dataset_name, file_meta in manifest["files"].items():
            csv_path = MOCK_DATA_DIR / file_meta["filename"]
            self.assertTrue(csv_path.exists(), f"Missing CSV for {dataset_name}: {csv_path}")
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(
                len(rows),
                file_meta["row_count"],
                f"Manifest row_count mismatch for {dataset_name}",
            )

    def test_schema_required_columns_exist_in_mock_csvs(self):
        for schema_path in sorted(SCHEMA_DIR.glob("*.yaml")):
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            csv_path = MOCK_DATA_DIR / f"{schema['name']}.csv"
            with csv_path.open(newline="", encoding="utf-8") as handle:
                headers = csv.DictReader(handle).fieldnames or []
            missing = [column for column in schema["required_columns"] if column not in headers]
            self.assertEqual([], missing, f"Missing required columns for {schema['name']}")

    def test_pandas_foundation_dependency_is_importable(self):
        frame = pd.DataFrame(
            [{"vendor_id": "V1001", "metric_code": "FILL_RATE", "metric_value": 0.918}]
        )
        self.assertEqual(["vendor_id", "metric_code", "metric_value"], frame.columns.tolist())
        self.assertEqual(1, len(frame))


if __name__ == "__main__":
    unittest.main()
