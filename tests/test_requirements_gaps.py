from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import build_parser
from src.agent import summarize_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_DIR = PROJECT_ROOT / "data" / "inbound" / "mock"


class CategoryFilterTests(unittest.TestCase):
    def test_category_filter_rejects_vendor_outside_requested_category(self) -> None:
        with patch("src.agent.generate_text", return_value="# Stub briefing\n"):
            with patch("src.agent.write_output") as mock_write:
                mock_write.return_value = {
                    "md_path": PROJECT_ROOT / "output" / "V1001_2026-04-03.md",
                }

                with self.assertRaisesRegex(
                    Exception,
                    "category_filter 'Frozen'",
                ):
                    summarize_request(
                        vendor="Northstar Foods Co",
                        meeting_date="2026-04-03",
                        data_dir=MOCK_DATA_DIR,
                        lookback_weeks=13,
                        persona_emphasis="both",
                        include_benchmarks=True,
                        output_format="md",
                        category_filter="Frozen",
                    )


class OutputFormatDefaultTests(unittest.TestCase):
    def test_cli_output_format_default_is_docx(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--vendor", "Northstar Foods Co", "--date", "2026-04-03"])
        self.assertEqual(args.output_format, "docx")
