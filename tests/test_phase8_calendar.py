from __future__ import annotations

import datetime
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.calendar_trigger import GoogleCalendarClient
from src.scheduler import BriefingScheduler


class CalendarClientFallbackTests(unittest.TestCase):
    def test_mock_fallback_returns_meetings_when_auth_fails(self) -> None:
        client = GoogleCalendarClient(
            credentials_path="nonexistent/credentials.json",
            token_path="nonexistent/token.json",
        )

        with patch.object(client, "authenticate", return_value=False):
            meetings = client.get_upcoming_vendor_meetings(days_ahead=2)

        self.assertGreater(len(meetings), 0)
        self.assertIn("summary", meetings[0])


class SchedulerCalendarTests(unittest.TestCase):
    def _make_meeting(self, hours_from_now: float, vendor: str = "Test Vendor") -> dict:
        start = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            hours=hours_from_now
        )
        return {
            "id": f"evt-{int(hours_from_now * 10)}",
            "summary": f"Vendor Review: {vendor}",
            "start_time": start.isoformat(),
            "creator": "buyer@example.com",
        }

    def test_poll_calendar_schedules_t24_and_t2_jobs(self) -> None:
        scheduler = BriefingScheduler()
        scheduler.start()

        meeting = self._make_meeting(hours_from_now=30)
        with patch.object(
            scheduler.calendar,
            "get_upcoming_vendor_meetings",
            return_value=[meeting],
        ):
            scheduler.poll_calendar()

        job_ids = {job.id for job in scheduler.scheduler.get_jobs()}
        self.assertIn(f"{meeting['id']}_t24", job_ids)
        self.assertIn(f"{meeting['id']}_t2", job_ids)
        scheduler.stop()

    def test_trigger_briefing_uses_absolute_prod_data_dir(self) -> None:
        scheduler = BriefingScheduler()
        meeting = {
            "id": "meeting-1",
            "summary": "Vendor Review: Northstar Foods Co",
            "start_time": "2026-05-01T10:00:00+00:00",
        }

        with patch("src.scheduler.summarize_request") as mock_summarize:
            mock_summarize.return_value = {"output_files": {}}
            scheduler._trigger_briefing(meeting, "Draft (T-24h)")

        kwargs = mock_summarize.call_args.kwargs
        self.assertEqual(kwargs["vendor"], "Northstar Foods Co")
        self.assertEqual(kwargs["meeting_date"], "2026-05-01")
        self.assertTrue(Path(kwargs["data_dir"]).is_absolute())
        self.assertTrue(str(kwargs["data_dir"]).endswith("data/inbound/prod"))
