import datetime
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

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
        config = load_config()
        calendar_config = config.get("calendar", {})
        settings = CalendarClientSettings(
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
            vendor_keywords=cls._resolve_vendor_keywords(calendar_config.get("vendor_keywords")),
            allow_mock_fallback=cls._resolve_bool_env(
                "GOOGLE_CALENDAR_ALLOW_MOCK_FALLBACK",
                calendar_config.get("allow_mock_fallback", True),
            ),
        )

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
        env_keywords = os.getenv("GOOGLE_CALENDAR_VENDOR_KEYWORDS")
        if env_keywords:
            return [keyword.strip().lower() for keyword in env_keywords.split(",") if keyword.strip()]
        if isinstance(configured_keywords, list) and configured_keywords:
            return [str(keyword).strip().lower() for keyword in configured_keywords if str(keyword).strip()]
        return ["vendor", "supplier", "review"]

    @staticmethod
    def _resolve_bool_env(env_name: str, default: bool) -> bool:
        env_value = os.getenv(env_name)
        if env_value is None:
            return bool(default)
        return env_value.strip().lower() in {"1", "true", "yes", "on"}

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
