from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from src.calendar_trigger import GoogleCalendarClient, OutlookCalendarClient, build_calendar_client


class CalendarTriggerTests(unittest.TestCase):
    def test_build_calendar_client_selects_google_by_default(self) -> None:
        config = {"calendar": {"provider": "google"}}

        with patch("src.calendar_trigger.load_config", return_value=config), patch.dict(os.environ, {}, clear=True):
            client = build_calendar_client()

        self.assertIsInstance(client, GoogleCalendarClient)

    def test_build_calendar_client_selects_outlook_from_environment(self) -> None:
        config = {
            "calendar": {
                "provider": "google",
                "vendor_keywords": ["vendor"],
                "allow_mock_fallback": True,
            }
        }
        env = {
            "SUPPLIER_COLLAB_CALENDAR_PROVIDER": "outlook",
            "OUTLOOK_CALENDAR_CLIENT_ID": "client-id",
            "OUTLOOK_CALENDAR_TENANT_ID": "organizations",
            "OUTLOOK_CALENDAR_TOKEN_CACHE_PATH": "config/outlook-cache.json",
            "OUTLOOK_CALENDAR_SCOPES": "Calendars.Read,User.Read",
        }

        with patch("src.calendar_trigger.load_config", return_value=config), patch.dict(os.environ, env, clear=True):
            client = build_calendar_client()

        self.assertIsInstance(client, OutlookCalendarClient)
        self.assertEqual(client.client_id, "client-id")
        self.assertEqual(client.tenant_id, "organizations")
        self.assertEqual(str(client.token_cache_path), "config/outlook-cache.json")
        self.assertEqual(client.scopes, ["Calendars.Read", "User.Read"])

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


class OutlookCalendarTriggerTests(unittest.TestCase):
    def test_returns_mock_meetings_when_authentication_fails(self) -> None:
        client = OutlookCalendarClient(client_id="")

        meetings = client.get_upcoming_vendor_meetings(days_ahead=2)

        self.assertEqual(len(meetings), 2)
        self.assertIn("Vendor Review", meetings[0]["summary"])

    def test_returns_empty_list_when_authentication_fails_and_mock_fallback_disabled(self) -> None:
        client = OutlookCalendarClient(client_id="", allow_mock_fallback=False)

        meetings = client.get_upcoming_vendor_meetings(days_ahead=2)

        self.assertEqual(meetings, [])

    def test_authenticate_uses_msal_silent_token_and_persists_changed_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_cache_path = os.path.join(temp_dir, "nested", "outlook-cache.json")
            fake_cache = MagicMock()
            fake_cache.has_state_changed = True
            fake_cache.serialize.return_value = '{"cached": true}'
            fake_app = MagicMock()
            fake_app.get_accounts.return_value = [{"username": "buyer@example.com"}]
            fake_app.acquire_token_silent.return_value = {"access_token": "silent-token"}
            fake_msal = types.SimpleNamespace(
                SerializableTokenCache=MagicMock(return_value=fake_cache),
                PublicClientApplication=MagicMock(return_value=fake_app),
            )
            client = OutlookCalendarClient(
                client_id="client-id",
                tenant_id="organizations",
                token_cache_path=token_cache_path,
                scopes=["Calendars.Read"],
            )

            with patch.dict(sys.modules, {"msal": fake_msal}):
                self.assertTrue(client.authenticate())

            self.assertEqual(client.access_token, "silent-token")
            fake_msal.PublicClientApplication.assert_called_once()
            fake_app.acquire_token_silent.assert_called_once_with(
                ["Calendars.Read"],
                account={"username": "buyer@example.com"},
            )
            self.assertTrue(os.path.exists(token_cache_path))

    @patch("src.calendar_trigger.httpx.get")
    def test_fetches_calendar_view_and_filters_vendor_meetings(self, mock_get) -> None:
        client = OutlookCalendarClient(
            client_id="client-id",
            tenant_id="common",
            vendor_keywords=["qbr"],
            token_cache_path="config/outlook-cache.json",
        )
        client.access_token = "token-value"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "evt-qbr",
                    "subject": "QBR: Northstar Foods Co",
                    "start": {"dateTime": "2026-04-03T15:00:00.0000000", "timeZone": "UTC"},
                    "organizer": {"emailAddress": {"address": "buyer@example.com"}},
                },
                {
                    "id": "evt-internal",
                    "subject": "Internal Team Standup",
                    "start": {"dateTime": "2026-04-03T16:00:00.0000000", "timeZone": "UTC"},
                    "organizer": {"emailAddress": {"address": "planner@example.com"}},
                },
            ]
        }
        mock_get.return_value = mock_response

        meetings = client.get_upcoming_vendor_meetings(days_ahead=3)

        self.assertEqual([meeting["id"] for meeting in meetings], ["evt-qbr"])
        self.assertEqual(meetings[0]["summary"], "QBR: Northstar Foods Co")
        self.assertEqual(meetings[0]["start_time"], "2026-04-03T15:00:00.0000000Z")
        self.assertEqual(meetings[0]["creator"], "buyer@example.com")
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.args[0], "https://graph.microsoft.com/v1.0/me/calendarView")
        self.assertEqual(mock_get.call_args.kwargs["headers"]["Authorization"], "Bearer token-value")
        self.assertEqual(mock_get.call_args.kwargs["params"]["$orderby"], "start/dateTime")
        self.assertIn("subject", mock_get.call_args.kwargs["params"]["$select"])
