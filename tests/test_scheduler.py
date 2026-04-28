from __future__ import annotations

import unittest
from unittest.mock import patch

from src.scheduler import BriefingScheduler


class SchedulerTriggerTests(unittest.TestCase):
    def test_trigger_briefing_uses_current_summarize_request_api(self) -> None:
        scheduler = BriefingScheduler()
        meeting = {
            "id": "meeting-1",
            "summary": "Vendor Review: Northstar Foods Co",
            "start_time": "2026-04-03T15:00:00Z",
        }

        with patch("src.scheduler.summarize_request") as mock_summarize:
            mock_summarize.return_value = {
                "output_files": {"md_path": "output/V1001_2026-04-03.md"}
            }

            scheduler._trigger_briefing(meeting, "Draft (T-24h)")

        mock_summarize.assert_called_once_with(
            vendor="Northstar Foods Co",
            meeting_date="2026-04-03",
            data_dir=scheduler.prod_data_dir,
            lookback_weeks=scheduler.default_lookback_weeks,
            persona_emphasis=scheduler.default_persona_emphasis,
            include_benchmarks=scheduler.default_include_benchmarks,
            output_format=scheduler.default_output_format,
            category_filter=None,
        )
