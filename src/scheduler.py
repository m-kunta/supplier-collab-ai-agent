import datetime
import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.agent import summarize_request
from src.calendar_trigger import GoogleCalendarClient
from src.config import load_config

logger = logging.getLogger(__name__)

class BriefingScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.calendar = GoogleCalendarClient()
        self.processed_jobs = set()
        config = load_config()
        defaults = config.get("defaults", {})
        self.prod_data_dir = Path(__file__).resolve().parent.parent / "data" / "inbound" / "prod"
        self.default_lookback_weeks = defaults.get("lookback_weeks", 13)
        self.default_persona_emphasis = defaults.get("persona_emphasis", "both")
        self.default_include_benchmarks = defaults.get("include_benchmarks", True)
        self.default_output_format = defaults.get("output_format", "docx")
        
    def start(self):
        # Poll calendar every 15 minutes to find new meetings
        self.scheduler.add_job(
            self.poll_calendar,
            trigger=IntervalTrigger(minutes=15),
            id='poll_calendar',
            name='Poll Google Calendar for Vendor Meetings',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("BriefingScheduler started. Waiting for next calendar poll.")
        
    def stop(self):
        self.scheduler.shutdown()
        logger.info("BriefingScheduler stopped.")
        
    def poll_calendar(self):
        logger.info("Polling calendar for upcoming vendor meetings...")
        try:
            # We fetch meetings for the next 2 days to catch the T-24h and T-2h windows
            meetings = self.calendar.get_upcoming_vendor_meetings(days_ahead=2)
            now = datetime.datetime.now(datetime.timezone.utc)
            
            for meeting in meetings:
                meeting_id = meeting['id']
                start_str = meeting['start_time']
                
                # Handle varying ISO formats from Google Calendar
                if start_str.endswith('Z'):
                    start_str = start_str[:-1] + '+00:00'
                
                try:
                    start_time = datetime.datetime.fromisoformat(start_str)
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    logger.warning(f"Could not parse meeting start time: {start_str}")
                    continue
                
                t_minus_24 = start_time - datetime.timedelta(hours=24)
                t_minus_2 = start_time - datetime.timedelta(hours=2)
                
                # Job IDs to prevent duplicate scheduling
                job_id_24h = f"{meeting_id}_t24"
                job_id_2h = f"{meeting_id}_t2"
                
                # If T-24h is in the future and not already processed/scheduled
                if t_minus_24 > now and job_id_24h not in self.processed_jobs:
                    self.scheduler.add_job(
                        self._trigger_briefing,
                        'date',
                        run_date=t_minus_24,
                        args=[meeting, "Draft (T-24h)"],
                        id=job_id_24h
                    )
                    self.processed_jobs.add(job_id_24h)
                    logger.info(f"Scheduled T-24h briefing for '{meeting['summary']}' at {t_minus_24}")
                
                # If T-2h is in the future and not already processed/scheduled
                if t_minus_2 > now and job_id_2h not in self.processed_jobs:
                    self.scheduler.add_job(
                        self._trigger_briefing,
                        'date',
                        run_date=t_minus_2,
                        args=[meeting, "Final (T-2h)"],
                        id=job_id_2h
                    )
                    self.processed_jobs.add(job_id_2h)
                    logger.info(f"Scheduled T-2h briefing for '{meeting['summary']}' at {t_minus_2}")
                    
        except Exception as e:
            logger.error(f"Error polling calendar: {e}")
            
    def _trigger_briefing(self, meeting: dict, phase: str):
        logger.info(f"*** AUTO-TRIGGER *** Generating {phase} briefing for: {meeting['summary']}")

        # Extract vendor name from meeting title, e.g., "Vendor Review: Northstar Foods Co"
        summary = meeting.get('summary', '')
        vendor_name = "Northstar Foods Co"  # Default fallback
        if ":" in summary:
            vendor_name = summary.split(":", 1)[1].strip()

        logger.info(f"Resolved vendor name: {vendor_name}. Calling agent pipeline...")
        
        # Assuming the meeting date is the target reference date
        meeting_date = meeting['start_time'][:10]

        try:
            result = summarize_request(
                vendor=vendor_name,
                meeting_date=meeting_date,
                data_dir=self.prod_data_dir,
                lookback_weeks=self.default_lookback_weeks,
                persona_emphasis=self.default_persona_emphasis,
                include_benchmarks=self.default_include_benchmarks,
                output_format=self.default_output_format,
                category_filter=None,
            )
            output_files = result.get("output_files") or {}
            saved_path = output_files.get("md_path") or output_files.get("docx_path")
            logger.info(f"Successfully generated briefing! Saved to: {saved_path}")
            
            # FUTURE: Send Email / Teams notification here with the file attached

        except Exception as e:
            logger.error(f"Failed to generate scheduled briefing for {vendor_name}: {e}")
