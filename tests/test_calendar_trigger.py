from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.calendar_trigger import GoogleCalendarClient


class CalendarTriggerTests(unittest.TestCase):
    def test_returns_mock_meetings_when_authentication_fails(self) -> None:
        client = GoogleCalendarClient()

        with patch.object(client, "authenticate", return_value=False):
            meetings = client.get_upcoming_vendor_meetings(days_ahead=2)

        self.assertEqual(len(meetings), 2)
        self.assertTrue(all("summary" in meeting for meeting in meetings))
        self.assertIn("Vendor Review", meetings[0]["summary"])

    @patch("src.calendar_trigger.build")
    def test_filters_calendar_events_to_vendor_like_meetings(self, mock_build) -> None:
        client = GoogleCalendarClient()
        client.creds = object()

        events = [
            {
                "id": "evt-1",
                "summary": "Vendor Review: Northstar Foods Co",
                "start": {"dateTime": "2026-04-03T15:00:00Z"},
                "creator": {"email": "buyer@example.com"},
            },
            {
                "id": "evt-2",
                "summary": "Internal Team Standup",
                "start": {"dateTime": "2026-04-03T16:00:00Z"},
                "creator": {"email": "planner@example.com"},
            },
            {
                "id": "evt-3",
                "summary": "Supplier Sync: Acme Corp",
                "start": {"date": "2026-04-04"},
                "creator": {"email": "buyer@example.com"},
            },
        ]

        mock_service = MagicMock()
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": events
        }
        mock_build.return_value = mock_service

        meetings = client.get_upcoming_vendor_meetings(days_ahead=3)

        self.assertEqual([meeting["id"] for meeting in meetings], ["evt-1", "evt-3"])
        self.assertEqual(meetings[1]["start_time"], "2026-04-04")
