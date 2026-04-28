import datetime
import json
import logging
import os.path
from pathlib import Path
from typing import Any, Callable, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendarClient:
    def __init__(self, credentials_path: str = "config/credentials.json", token_path: str = "config/token.json"):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.creds = None

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
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            except Exception as e:
                logger.error(f"Failed to save token.json: {e}")
                
        return True

    def get_upcoming_vendor_meetings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Fetches upcoming vendor meetings from the calendar.
        Looks for meetings with a specific tag or vendor name in the summary.
        """
        if not self.creds:
            if not self.authenticate():
                logger.warning("No Google credentials found. Falling back to MOCK calendar data.")
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

        service = build('calendar', 'v3', credentials=self.creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
        
        logger.info(f"Fetching calendar events from {now} to {future}")
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            timeMax=future,
            maxResults=100, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        vendor_meetings = []
        for event in events:
            summary = event.get('summary', '').lower()
            
            # Simple heuristic: look for "vendor review", "supplier sync", etc.
            # Or explicit [Vendor: X] tags
            if any(keyword in summary for keyword in ['vendor', 'supplier', 'review']):
                start = event['start'].get('dateTime', event['start'].get('date'))
                vendor_meetings.append({
                    'id': event['id'],
                    'summary': event.get('summary', ''),
                    'start_time': start,
                    'creator': event.get('creator', {}).get('email', '')
                })

        return vendor_meetings
