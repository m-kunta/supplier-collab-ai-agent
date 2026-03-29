from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.data_loader import load_manifest, resolve_data_dir
from src.llm_providers import resolve_provider


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTests(unittest.TestCase):
    def test_required_scaffold_paths_exist(self):
        expected_paths = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "cli.py",
            PROJECT_ROOT / "config" / "agent_config.yaml",
            PROJECT_ROOT / "data" / "inbound" / "mock" / "manifest.yaml",
            PROJECT_ROOT / "data" / "schemas" / "vendor_master.schema.yaml",
            PROJECT_ROOT / "docs" / "implementation_plan.md",
            PROJECT_ROOT / "prompts" / "briefing_v0.md",
            PROJECT_ROOT / "src" / "agent.py",
            PROJECT_ROOT / "tests" / "test_scaffold.py",
        ]
        for path in expected_paths:
            self.assertTrue(path.exists(), f"Missing scaffold path: {path}")

    def test_cli_help_exposes_expected_arguments(self):
        result = subprocess.run(
            [sys.executable, "cli.py", "--help"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        help_text = result.stdout
        self.assertIn("--vendor", help_text)
        self.assertIn("--date", help_text)
        self.assertIn("--data-dir", help_text)
        self.assertIn("--lookback-weeks", help_text)
        self.assertIn("--persona-emphasis", help_text)
        self.assertIn("--include-benchmarks", help_text)
        self.assertIn("--output-format", help_text)

    def test_config_loads_defaults(self):
        config = load_config()
        self.assertEqual(config["defaults"]["lookback_weeks"], 13)
        self.assertEqual(config["llm"]["default_provider"], "anthropic")

    def test_config_loads_native_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "agent_config.yaml"
            config_path.write_text(
                "defaults:\n"
                "  lookback_weeks: 8\n"
                "llm:\n"
                "  default_provider: openai\n"
                "  default_model: gpt-4.1-mini\n",
                encoding="utf-8",
            )
            config = load_config(config_path)
        self.assertEqual(config["defaults"]["lookback_weeks"], 8)
        self.assertEqual(config["llm"]["default_provider"], "openai")

    def test_manifest_path_resolution(self):
        data_dir = PROJECT_ROOT / "data" / "inbound" / "mock"
        resolved_dir = resolve_data_dir(data_dir)
        manifest = load_manifest(data_dir)
        self.assertEqual(resolved_dir.name, "mock")
        self.assertEqual(manifest["environment"], "mock")
        self.assertTrue(manifest["_manifest_path"].endswith("manifest.yaml"))

    def test_provider_selection_without_live_call(self):
        selection = resolve_provider("anthropic", None)
        self.assertEqual(selection.provider, "anthropic")
        self.assertTrue(selection.model.startswith("claude-"))


if __name__ == "__main__":
    unittest.main()
