# Google Calendar OAuth Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Google Calendar OAuth client deployment-configurable while preserving safe local mock fallback behavior.

**Architecture:** Keep calendar integration inside `src/calendar_trigger.py`, adding a small settings dataclass and `GoogleCalendarClient.from_config()` factory. `BriefingScheduler` will depend on that factory so production settings flow through the same config/env path as other Phase 10 hardening work.

**Tech Stack:** Python, PyYAML project config, google-auth-oauthlib, google-api-python-client, unittest/pytest.

---

## Files

- Modify: `src/calendar_trigger.py` — add calendar settings, config/env resolution, configurable calendar polling, token directory creation, and fallback control.
- Modify: `src/scheduler.py` — build the calendar client from config.
- Modify: `config/agent_config.yaml` — add default Google Calendar settings.
- Modify: `tests/test_calendar_trigger.py` — cover config/env overrides, calendar ID usage, keyword overrides, fallback disablement, and token directory creation.
- Modify: project docs — mark Google Calendar OAuth hardening complete and leave Outlook OAuth as remaining.

## Task 1: Calendar Config Tests

- [ ] Add tests in `tests/test_calendar_trigger.py` for `GoogleCalendarClient.from_config()` using patched `load_config()` and `patch.dict(os.environ, ...)`.
- [ ] Run `pytest tests/test_calendar_trigger.py -q` and confirm the new config test fails because `from_config()` does not exist.
- [ ] Implement `CalendarClientSettings` and `GoogleCalendarClient.from_config()`.
- [ ] Re-run `pytest tests/test_calendar_trigger.py -q` and confirm the config test passes.

## Task 2: Configurable Polling Tests

- [ ] Add tests proving `get_upcoming_vendor_meetings()` passes the configured `calendar_id` into `events().list()` and filters events using configured `vendor_keywords`.
- [ ] Run `pytest tests/test_calendar_trigger.py -q` and confirm the new polling test fails because the client still uses hard-coded `primary` and fixed keywords.
- [ ] Update `GoogleCalendarClient` to store `calendar_id` and `vendor_keywords`, then use them while listing/filtering events.
- [ ] Re-run `pytest tests/test_calendar_trigger.py -q` and confirm the polling test passes.

## Task 3: Fallback and Token Persistence Tests

- [ ] Add a test showing `allow_mock_fallback=False` returns an empty list when authentication fails.
- [ ] Add a test showing `authenticate()` creates the token file parent directory before saving refreshed or newly-created credentials.
- [ ] Run `pytest tests/test_calendar_trigger.py -q` and confirm the new tests fail.
- [ ] Extract `_mock_vendor_meetings()` and update fallback handling to respect `allow_mock_fallback`.
- [ ] Create `self.token_path.parent` before writing the token file.
- [ ] Re-run `pytest tests/test_calendar_trigger.py -q` and confirm all calendar trigger tests pass.

## Task 4: Scheduler Wiring and Docs

- [ ] Add a `calendar:` section to `config/agent_config.yaml` with Google defaults.
- [ ] Update `BriefingScheduler.__init__()` to call `GoogleCalendarClient.from_config()`.
- [ ] Update `README.md`, `AGENTS.md`, `CLAUDE.md`, `TODO.md`, and `docs/implementation_plan.md` to document Google Calendar OAuth configuration and leave Outlook OAuth as remaining.
- [ ] Run focused backend tests: `pytest tests/test_calendar_trigger.py tests/test_phase8_calendar.py tests/test_scheduler.py -q`.
- [ ] Run full backend tests: `pytest tests/ -q`.
- [ ] Commit and push the completed slice.

## Self-Review

- Spec coverage: all Google Calendar config, env override, fallback, polling, scheduler, and docs requirements map to Tasks 1-4.
- Placeholder scan: no placeholders are present; Outlook is explicitly out of scope.
- Type consistency: the plan uses `CalendarClientSettings`, `GoogleCalendarClient.from_config()`, `calendar_id`, `vendor_keywords`, and `allow_mock_fallback` consistently.
