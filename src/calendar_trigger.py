import datetime
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import load_config

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


@dataclass(frozen=True)
class CalendarClientSettings:
    provider: str = "google"
    credentials_path: str = "config/credentials.json"
    token_path: str = "config/token.json"
    calendar_id: str = "primary"
    vendor_keywords: List[str] = field(default_factory=lambda: ["vendor", "supplier", "review"])
    allow_mock_fallback: bool = True
    outlook_client_id: str = ""
    outlook_tenant_id: str = "common"
    outlook_token_cache_path: str = "config/outlook_token_cache.json"
    outlook_scopes: List[str] = field(default_factory=lambda: ["Calendars.Read"])


def _resolve_bool_env(env_name: str, default: bool) -> bool:
    env_value = os.getenv(env_name)
    if env_value is None:
        return bool(default)
    return env_value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_vendor_keywords(configured_keywords: Any, env_name: str = "GOOGLE_CALENDAR_VENDOR_KEYWORDS") -> List[str]:
    env_keywords = os.getenv(env_name)
    if env_keywords:
        return [keyword.strip().lower() for keyword in env_keywords.split(",") if keyword.strip()]
    if isinstance(configured_keywords, list) and configured_keywords:
        return [str(keyword).strip().lower() for keyword in configured_keywords if str(keyword).strip()]
    return ["vendor", "supplier", "review"]


def _resolve_scopes(configured_scopes: Any) -> List[str]:
    env_scopes = os.getenv("OUTLOOK_CALENDAR_SCOPES")
    if env_scopes:
        return [scope.strip() for scope in env_scopes.split(",") if scope.strip()]
    if isinstance(configured_scopes, list) and configured_scopes:
        return [str(scope).strip() for scope in configured_scopes if str(scope).strip()]
    return ["Calendars.Read"]


def _calendar_settings_from_config() -> CalendarClientSettings:
    config = load_config()
    calendar_config = config.get("calendar", {})
    return CalendarClientSettings(
        provider=os.getenv("SUPPLIER_COLLAB_CALENDAR_PROVIDER", calendar_config.get("provider", "google")),
        credentials_path=os.getenv(
            "GOOGLE_CALENDAR_CREDENTIALS_PATH",
            calendar_config.get("credentials_path", "config/credentials.json"),
        ),
        token_path=os.getenv(
            "GOOGLE_CALENDAR_TOKEN_PATH",
            calendar_config.get("token_path", "config/token.json"),
        ),
        calendar_id=os.getenv("GOOGLE_CALENDAR_ID", calendar_config.get("calendar_id", "primary")),
        vendor_keywords=_resolve_vendor_keywords(calendar_config.get("vendor_keywords")),
        allow_mock_fallback=_resolve_bool_env(
            "GOOGLE_CALENDAR_ALLOW_MOCK_FALLBACK",
            calendar_config.get("allow_mock_fallback", True),
        ),
        outlook_client_id=os.getenv(
            "OUTLOOK_CALENDAR_CLIENT_ID",
            calendar_config.get("outlook_client_id", ""),
        ),
        outlook_tenant_id=os.getenv(
            "OUTLOOK_CALENDAR_TENANT_ID",
            calendar_config.get("outlook_tenant_id", "common"),
        ),
        outlook_token_cache_path=os.getenv(
            "OUTLOOK_CALENDAR_TOKEN_CACHE_PATH",
            calendar_config.get("outlook_token_cache_path", "config/outlook_token_cache.json"),
        ),
        outlook_scopes=_resolve_scopes(calendar_config.get("outlook_scopes")),
    )


def build_calendar_client():
    settings = _calendar_settings_from_config()
    provider = settings.provider.strip().lower()
    if provider == "outlook":
        return OutlookCalendarClient(
            client_id=settings.outlook_client_id,
            tenant_id=settings.outlook_tenant_id,
            token_cache_path=settings.outlook_token_cache_path,
            scopes=settings.outlook_scopes,
            vendor_keywords=settings.vendor_keywords,
            allow_mock_fallback=settings.allow_mock_fallback,
        )
    if provider != "google":
        logger.warning("Unsupported calendar provider '%s'; using Google Calendar client.", settings.provider)
    return GoogleCalendarClient(
        credentials_path=settings.credentials_path,
        token_path=settings.token_path,
        calendar_id=settings.calendar_id,
        vendor_keywords=settings.vendor_keywords,
        allow_mock_fallback=settings.allow_mock_fallback,
    )


class GoogleCalendarClient:
    def __init__(
        self,
        credentials_path: str = "config/credentials.json",
        token_path: str = "config/token.json",
        calendar_id: str = "primary",
        vendor_keywords: List[str] = None,
        allow_mock_fallback: bool = True,
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.calendar_id = calendar_id
        self.vendor_keywords = vendor_keywords or ["vendor", "supplier", "review"]
        self.allow_mock_fallback = allow_mock_fallback
        self.creds = None

    @classmethod
    def from_config(cls) -> "GoogleCalendarClient":
        settings = _calendar_settings_from_config()

        if settings.provider != "google":
            logger.warning("Unsupported calendar provider '%s'; using Google Calendar client.", settings.provider)

        return cls(
            credentials_path=settings.credentials_path,
            token_path=settings.token_path,
            calendar_id=settings.calendar_id,
            vendor_keywords=settings.vendor_keywords,
            allow_mock_fallback=settings.allow_mock_fallback,
        )

    @staticmethod
    def _resolve_vendor_keywords(configured_keywords: Any) -> List[str]:
        return _resolve_vendor_keywords(configured_keywords)

    @staticmethod
    def _resolve_bool_env(env_name: str, default: bool) -> bool:
        return _resolve_bool_env(env_name, default)

    def authenticate(self) -> bool:
        """
        Authenticates with Google Calendar API using OAuth 2.0.
        Returns True if successful.
        """
        if self.token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    self.creds = None
            
            if not self.creds:
                if not self.credentials_path.exists():
                    logger.error(f"Credentials file not found at {self.credentials_path}. Please download from Google Cloud Console.")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                    self.creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    return False

            # Save the credentials for the next run
            try:
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            except Exception as e:
                logger.error(f"Failed to save token.json: {e}")
                
        return True

    def _mock_vendor_meetings(self) -> List[Dict[str, Any]]:
        now = datetime.datetime.utcnow()
        t24 = now + datetime.timedelta(hours=24, minutes=5)
        t2 = now + datetime.timedelta(hours=2, minutes=5)
        return [
            {
                'id': 'mock_meeting_1',
                'summary': 'Vendor Review: Northstar Foods Co',
                'start_time': t24.isoformat() + 'Z',
                'creator': 'buyer@retailer.com'
            },
            {
                'id': 'mock_meeting_2',
                'summary': 'Supplier Sync: Acme Corp',
                'start_time': t2.isoformat() + 'Z',
                'creator': 'buyer@retailer.com'
            }
        ]

    def _event_matches_vendor_meeting(self, event: Dict[str, Any]) -> bool:
        summary = event.get('summary', '').lower()
        return any(keyword.lower() in summary for keyword in self.vendor_keywords)

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        start = event['start'].get('dateTime', event['start'].get('date'))
        return {
            'id': event['id'],
            'summary': event.get('summary', ''),
            'start_time': start,
            'creator': event.get('creator', {}).get('email', '')
        }

    def get_upcoming_vendor_meetings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Fetches upcoming vendor meetings from the calendar.
        Looks for meetings with a specific tag or vendor name in the summary.
        """
        if not self.creds:
            if not self.authenticate():
                if self.allow_mock_fallback:
                    logger.warning("No Google credentials found. Falling back to MOCK calendar data.")
                    return self._mock_vendor_meetings()
                logger.warning("No Google credentials found and mock fallback is disabled.")
                return []

        service = build('calendar', 'v3', credentials=self.creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
        
        logger.info(f"Fetching calendar events from {now} to {future}")
        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=now,
            timeMax=future,
            maxResults=100, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        vendor_meetings = []
        for event in events:
            if self._event_matches_vendor_meeting(event):
                vendor_meetings.append(self._normalize_event(event))

        return vendor_meetings


class OutlookCalendarClient:
    GRAPH_CALENDAR_VIEW_URL = "https://graph.microsoft.com/v1.0/me/calendarView"

    def __init__(
        self,
        client_id: str,
        tenant_id: str = "common",
        token_cache_path: str = "config/outlook_token_cache.json",
        scopes: List[str] = None,
        vendor_keywords: List[str] = None,
        allow_mock_fallback: bool = True,
    ):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.token_cache_path = Path(token_cache_path)
        self.scopes = scopes or ["Calendars.Read"]
        self.vendor_keywords = vendor_keywords or ["vendor", "supplier", "review"]
        self.allow_mock_fallback = allow_mock_fallback
        self.access_token = None

    def authenticate(self) -> bool:
        if self.access_token:
            return True
        if not self.client_id:
            logger.error("Outlook calendar client ID is not configured.")
            return False

        try:
            import msal
        except ImportError:
            logger.error("MSAL is not installed. Install requirements before using Outlook calendar OAuth.")
            return False

        cache = msal.SerializableTokenCache()
        if self.token_cache_path.exists():
            cache.deserialize(self.token_cache_path.read_text(encoding="utf-8"))

        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            token_cache=cache,
        )
        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(self.scopes, account=accounts[0])
        if not result:
            flow = app.initiate_device_flow(scopes=self.scopes)
            if "user_code" not in flow:
                logger.error("Failed to initiate Outlook device-code flow: %s", flow)
                return False
            logger.warning(flow.get("message", "Complete Microsoft device login to authorize calendar access."))
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            logger.error("Outlook OAuth failed: %s", result.get("error_description", result))
            return False

        self.access_token = result["access_token"]
        if cache.has_state_changed:
            self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_cache_path.write_text(cache.serialize(), encoding="utf-8")
        return True

    def _mock_vendor_meetings(self) -> List[Dict[str, Any]]:
        return GoogleCalendarClient(allow_mock_fallback=True)._mock_vendor_meetings()

    def _event_matches_vendor_meeting(self, event: Dict[str, Any]) -> bool:
        subject = event.get("subject", "").lower()
        return any(keyword.lower() in subject for keyword in self.vendor_keywords)

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        start = event.get("start", {})
        start_time = start.get("dateTime", "")
        if start.get("timeZone") == "UTC" and start_time and not start_time.endswith("Z"):
            start_time = f"{start_time}Z"
        return {
            "id": event.get("id", ""),
            "summary": event.get("subject", ""),
            "start_time": start_time,
            "creator": event.get("organizer", {}).get("emailAddress", {}).get("address", ""),
        }

    def get_upcoming_vendor_meetings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        if not self.authenticate():
            if self.allow_mock_fallback:
                logger.warning("No Outlook credentials found. Falling back to MOCK calendar data.")
                return self._mock_vendor_meetings()
            logger.warning("No Outlook credentials found and mock fallback is disabled.")
            return []

        now = datetime.datetime.utcnow()
        future = now + datetime.timedelta(days=days_ahead)
        response = httpx.get(
            self.GRAPH_CALENDAR_VIEW_URL,
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={
                "startDateTime": now.isoformat() + "Z",
                "endDateTime": future.isoformat() + "Z",
                "$top": "100",
                "$orderby": "start/dateTime",
                "$select": "id,subject,start,organizer",
            },
            timeout=10,
        )
        response.raise_for_status()
        events = response.json().get("value", [])
        return [self._normalize_event(event) for event in events if self._event_matches_vendor_meeting(event)]
