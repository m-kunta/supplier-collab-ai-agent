from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.calendar_trigger import GoogleCalendarClient


class CalendarTriggerTests(unittest.TestCase):
    def test_from_config_uses_yaml_defaults_and_environment_overrides(self) -> None:
        config = {
            "calendar": {
                "provider": "google",
                "credentials_path": "config/from-yaml.json",
                "token_path": "config/from-yaml-token.json",
                "calendar_id": "yaml-calendar@example.com",
                "vendor_keywords": ["vendor", "supplier"],
                "allow_mock_fallback": True,
            }
        }

        env = {
            "GOOGLE_CALENDAR_CREDENTIALS_PATH": "config/from-env.json",
            "GOOGLE_CALENDAR_TOKEN_PATH": "config/from-env-token.json",
            "GOOGLE_CALENDAR_ID": "env-calendar@example.com",
            "GOOGLE_CALENDAR_VENDOR_KEYWORDS": "qbr,partner review",
            "GOOGLE_CALENDAR_ALLOW_MOCK_FALLBACK": "false",
        }

        with patch("src.calendar_trigger.load_config", return_value=config), patch.dict(os.environ, env, clear=True):
            client = GoogleCalendarClient.from_config()

        self.assertEqual(str(client.credentials_path), "config/from-env.json")
        self.assertEqual(str(client.token_path), "config/from-env-token.json")
        self.assertEqual(client.calendar_id, "env-calendar@example.com")
        self.assertEqual(client.vendor_keywords, ["qbr", "partner review"])
        self.assertFalse(client.allow_mock_fallback)

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

    @patch("src.calendar_trigger.build")
    def test_uses_configured_calendar_id_and_vendor_keywords(self, mock_build) -> None:
        client = GoogleCalendarClient(
            calendar_id="team-calendar@example.com",
            vendor_keywords=["qbr"],
        )
        client.creds = object()

        events = [
            {
                "id": "evt-qbr",
                "summary": "QBR: Northstar Foods Co",
                "start": {"dateTime": "2026-04-03T15:00:00Z"},
                "creator": {"email": "buyer@example.com"},
            },
            {
                "id": "evt-vendor",
                "summary": "Vendor Review: Acme Corp",
                "start": {"dateTime": "2026-04-03T16:00:00Z"},
                "creator": {"email": "planner@example.com"},
            },
        ]
        mock_service = MagicMock()
        mock_list = mock_service.events.return_value.list
        mock_list.return_value.execute.return_value = {"items": events}
        mock_build.return_value = mock_service

        meetings = client.get_upcoming_vendor_meetings(days_ahead=3)

        self.assertEqual([meeting["id"] for meeting in meetings], ["evt-qbr"])
        mock_list.assert_called_once()
        self.assertEqual(mock_list.call_args.kwargs["calendarId"], "team-calendar@example.com")

    def test_returns_empty_list_when_authentication_fails_and_mock_fallback_disabled(self) -> None:
        client = GoogleCalendarClient(allow_mock_fallback=False)

        with patch.object(client, "authenticate", return_value=False):
            meetings = client.get_upcoming_vendor_meetings(days_ahead=2)

        self.assertEqual(meetings, [])

    def test_authenticate_creates_token_parent_directory_before_saving(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials.json")
            token_path = os.path.join(temp_dir, "nested", "token.json")
            with open(credentials_path, "w", encoding="utf-8") as handle:
                handle.write("{}")

            client = GoogleCalendarClient(credentials_path=credentials_path, token_path=token_path)
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_creds.to_json.return_value = '{"token": "saved"}'
            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = mock_creds

            with patch("src.calendar_trigger.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow):
                self.assertTrue(client.authenticate())

            self.assertTrue(os.path.exists(token_path))
