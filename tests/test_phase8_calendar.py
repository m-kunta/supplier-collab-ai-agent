"""Tests for Phase 8 calendar trigger and scheduler modules."""
import datetime
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _stub_google_modules():
    """Inject lightweight stubs for Google auth/api/genai modules before any google import fires."""
    stub_names = [
        'google', 'google.auth', 'google.auth.transport', 'google.auth.transport.requests',
        'google.oauth2', 'google.oauth2.credentials',
        'google.auth.crypt', 'google.auth._service_account_info',
        'google.oauth2.service_account',
        'google_auth_oauthlib', 'google_auth_oauthlib.flow',
        'googleapiclient', 'googleapiclient.discovery',
        # google-genai chain (used by llm_providers.py, pulled in via src.agent)
        'google.genai', 'google.genai.types', 'google.genai.client',
    ]
    for mod_name in stub_names:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    sys.modules['google.auth.transport.requests'].Request = MagicMock()
    sys.modules['google.oauth2.credentials'].Credentials = MagicMock()
    sys.modules['google_auth_oauthlib.flow'].InstalledAppFlow = MagicMock()
    sys.modules['googleapiclient.discovery'].build = MagicMock()
    sys.modules['google.genai'].Client = MagicMock()


def _stub_agent_modules():
    """Stub src.agent and src.config so _trigger_briefing's local imports resolve to mocks.

    These are injected into sys.modules *before* src.scheduler is imported so
    the lazy ``from src.agent import summarize_request`` inside _trigger_briefing
    hits the stub rather than the real module (which would pull in the broken
    google-genai → cryptography → cffi chain).
    """
    agent_mod = types.ModuleType('src.agent')
    agent_mod.summarize_request = MagicMock(return_value={'output_files': {}})
    agent_mod.AgentPipelineError = type('AgentPipelineError', (Exception,), {})
    sys.modules.setdefault('src.agent', agent_mod)

    config_mod = types.ModuleType('src.config')
    config_mod.load_config = MagicMock(return_value={'defaults': {}})
    sys.modules.setdefault('src.config', config_mod)


_stub_google_modules()
_stub_agent_modules()

# Now safe to import
from src.calendar_trigger import GoogleCalendarClient  # noqa: E402
from src.scheduler import BriefingScheduler  # noqa: E402


class TestGoogleCalendarClientMockFallback(unittest.TestCase):
    """GoogleCalendarClient — mock fallback path (no real creds)."""

    def setUp(self):
        self.client = GoogleCalendarClient(
            credentials_path="nonexistent/credentials.json",
            token_path="nonexistent/token.json",
        )

    def test_mock_fallback_returns_list(self):
        meetings = self.client.get_upcoming_vendor_meetings(days_ahead=7)
        self.assertIsInstance(meetings, list)
        self.assertGreater(len(meetings), 0)

    def test_mock_fallback_meeting_shape(self):
        meetings = self.client.get_upcoming_vendor_meetings()
        for m in meetings:
            self.assertIn('id', m)
            self.assertIn('summary', m)
            self.assertIn('start_time', m)
            self.assertIn('creator', m)

    def test_mock_fallback_start_times_are_future(self):
        now = datetime.datetime.utcnow()
        meetings = self.client.get_upcoming_vendor_meetings()
        for m in meetings:
            start_str = m['start_time'].rstrip('Z')
            start = datetime.datetime.fromisoformat(start_str)
            self.assertGreater(start, now)

    def test_authenticate_returns_false_without_credentials(self):
        result = self.client.authenticate()
        self.assertFalse(result)


class TestBriefingSchedulerInit(unittest.TestCase):
    """BriefingScheduler — instantiation and lifecycle."""

    def test_scheduler_creates_empty_processed_jobs(self):
        sched = BriefingScheduler()
        self.assertIsInstance(sched.processed_jobs, set)
        self.assertEqual(len(sched.processed_jobs), 0)

    def test_start_and_stop(self):
        sched = BriefingScheduler()
        sched.start()
        self.assertTrue(sched.scheduler.running)
        sched.stop()
        self.assertFalse(sched.scheduler.running)


class TestBriefingSchedulerPollCalendar(unittest.TestCase):
    """BriefingScheduler.poll_calendar — job scheduling logic."""

    def _make_meeting(self, hours_from_now: float, vendor: str = "Test Vendor") -> dict:
        t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours_from_now)
        return {
            'id': f'evt_{int(hours_from_now * 10)}',
            'summary': f'Vendor Review: {vendor}',
            'start_time': t.isoformat(),
            'creator': 'buyer@example.com',
        }

    def test_poll_schedules_t24_and_t2_jobs(self):
        sched = BriefingScheduler()
        sched.start()

        meeting = self._make_meeting(hours_from_now=30)
        with patch.object(sched.calendar, 'get_upcoming_vendor_meetings', return_value=[meeting]):
            sched.poll_calendar()

        job_ids = {job.id for job in sched.scheduler.get_jobs()}
        self.assertIn(f"{meeting['id']}_t24", job_ids)
        self.assertIn(f"{meeting['id']}_t2", job_ids)
        sched.stop()

    def test_poll_does_not_duplicate_jobs(self):
        sched = BriefingScheduler()
        sched.start()

        meeting = self._make_meeting(hours_from_now=30)
        with patch.object(sched.calendar, 'get_upcoming_vendor_meetings', return_value=[meeting]):
            sched.poll_calendar()
            sched.poll_calendar()  # second call must not re-schedule

        job_ids = [job.id for job in sched.scheduler.get_jobs()]
        self.assertEqual(job_ids.count(f"{meeting['id']}_t24"), 1)
        sched.stop()

    def test_poll_skips_meetings_whose_triggers_have_passed(self):
        sched = BriefingScheduler()
        sched.start()

        # Meeting only 1 hour away — both T-24h and T-2h are already in the past
        meeting = self._make_meeting(hours_from_now=1)
        with patch.object(sched.calendar, 'get_upcoming_vendor_meetings', return_value=[meeting]):
            sched.poll_calendar()

        date_jobs = [j for j in sched.scheduler.get_jobs() if j.id != 'poll_calendar']
        self.assertEqual(len(date_jobs), 0)
        sched.stop()

    def test_poll_handles_z_suffix_iso_format(self):
        sched = BriefingScheduler()
        sched.start()

        future = datetime.datetime.utcnow() + datetime.timedelta(hours=30)
        meeting = {
            'id': 'z_evt',
            'summary': 'Vendor Review: Z Corp',
            'start_time': future.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'creator': 'buyer@example.com',
        }
        with patch.object(sched.calendar, 'get_upcoming_vendor_meetings', return_value=[meeting]):
            sched.poll_calendar()  # must not raise

        sched.stop()

    def test_poll_error_is_caught_gracefully(self):
        sched = BriefingScheduler()
        sched.start()

        with patch.object(sched.calendar, 'get_upcoming_vendor_meetings', side_effect=RuntimeError("API error")):
            sched.poll_calendar()  # must not propagate

        sched.stop()


class TestTriggerBriefingVendorExtraction(unittest.TestCase):
    """BriefingScheduler._trigger_briefing — vendor extraction and summarize_request wiring."""

    _BASE_MEETING = {
        'id': 'x1',
        'summary': 'Vendor Review: Northstar Foods Co',
        'start_time': '2026-05-01T10:00:00+00:00',
    }

    def _run_trigger(self, meeting: dict, summarize_side_effect=None):
        sched = BriefingScheduler()
        captured = {}

        def fake_summarize(**kwargs):
            captured.update(kwargs)
            if summarize_side_effect:
                raise summarize_side_effect
            return {'output_files': {'md_path': '/tmp/test.md'}}

        # Patch at the stub module level (src.agent / src.config are stubs in sys.modules)
        with patch.object(sys.modules['src.agent'], 'summarize_request', side_effect=fake_summarize):
            with patch.object(sys.modules['src.config'], 'load_config', return_value={'defaults': {}}):
                sched._trigger_briefing(meeting, "Draft (T-24h)")

        return captured

    def test_vendor_extracted_after_colon(self):
        captured = self._run_trigger(self._BASE_MEETING)
        self.assertEqual(captured.get('vendor'), 'Northstar Foods Co')

    def test_vendor_defaults_when_no_colon(self):
        meeting = {**self._BASE_MEETING, 'summary': 'Weekly Supplier Sync'}
        captured = self._run_trigger(meeting)
        self.assertEqual(captured.get('vendor'), 'Northstar Foods Co')

    def test_trigger_uses_prod_data_dir(self):
        captured = self._run_trigger(self._BASE_MEETING)
        self.assertEqual(str(captured.get('data_dir')), 'data/inbound/prod')

    def test_trigger_meeting_date_from_start_time(self):
        meeting = {**self._BASE_MEETING, 'start_time': '2026-05-15T14:30:00+00:00'}
        captured = self._run_trigger(meeting)
        self.assertEqual(captured.get('meeting_date'), '2026-05-15')

    def test_trigger_passes_correct_defaults(self):
        sched = BriefingScheduler()
        captured = {}

        def fake_summarize(**kwargs):
            captured.update(kwargs)
            return {'output_files': {}}

        config = {'defaults': {'lookback_weeks': 8, 'persona_emphasis': 'buyer', 'include_benchmarks': False, 'output_format': 'docx'}}
        with patch.object(sys.modules['src.agent'], 'summarize_request', side_effect=fake_summarize):
            with patch.object(sys.modules['src.config'], 'load_config', return_value=config):
                sched._trigger_briefing(self._BASE_MEETING, "Final (T-2h)")

        self.assertEqual(captured.get('lookback_weeks'), 8)
        self.assertEqual(captured.get('persona_emphasis'), 'buyer')
        self.assertFalse(captured.get('include_benchmarks'))
        self.assertEqual(captured.get('output_format'), 'docx')

    def test_trigger_handles_summarize_exception_gracefully(self):
        sched = BriefingScheduler()

        with patch.object(sys.modules['src.agent'], 'summarize_request', side_effect=RuntimeError("LLM down")):
            with patch.object(sys.modules['src.config'], 'load_config', return_value={'defaults': {}}):
                sched._trigger_briefing(self._BASE_MEETING, "Draft (T-24h)")  # must not raise


if __name__ == '__main__':
    unittest.main()
