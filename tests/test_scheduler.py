from __future__ import annotations

import unittest
from unittest.mock import patch

from src.delivery import NotificationSettings
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

    def test_trigger_briefing_uses_repo_anchored_prod_data_dir(self) -> None:
        scheduler = BriefingScheduler()
        self.assertTrue(scheduler.prod_data_dir.is_absolute())
        self.assertTrue(str(scheduler.prod_data_dir).endswith("data/inbound/prod"))

    def test_trigger_briefing_uses_notification_retry_service(self) -> None:
        scheduler = BriefingScheduler()
        meeting = {
            "id": "meeting-1",
            "summary": "Vendor Review: Northstar Foods Co",
            "start_time": "2026-04-03T15:00:00Z",
        }

        with patch("src.scheduler.summarize_request") as mock_summarize, \
             patch("src.store_factory.create_settings_store") as mock_settings_factory, \
             patch("src.notification_retry.NotificationRetryService") as mock_retry_cls:
            mock_summarize.return_value = {
                "briefing_id": "brief-123",
                "briefing_text": "Executive summary",
                "output_files": {"docx_path": "output/brief.docx"},
            }
            mock_settings_factory.return_value.load.return_value = NotificationSettings(
                slack_webhook_url="https://hooks.slack.com/fake"
            )

            scheduler._trigger_briefing(meeting, "Draft (T-24h)")

        mock_retry_cls.assert_called_once()
        payload = mock_retry_cls.return_value.dispatch_with_retries.call_args.args[0]
        self.assertEqual(payload["vendor"], "Northstar Foods Co")
        self.assertEqual(payload["meeting_date"], "2026-04-03")
        self.assertEqual(payload["briefing_id"], "brief-123")
        self.assertEqual(payload["briefing_text"], "Executive summary")
        self.assertEqual(payload["output_files"], {"docx_path": "output/brief.docx"})
