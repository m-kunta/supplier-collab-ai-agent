# Outlook Calendar OAuth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Outlook / Microsoft Graph calendar ingestion as a selectable scheduler provider.

**Architecture:** Introduce a provider factory in `src/calendar_trigger.py` that returns either `GoogleCalendarClient` or `OutlookCalendarClient`. The Outlook client owns MSAL token handling and Graph event retrieval, but returns the same normalized meeting dictionaries that the scheduler already consumes.

**Tech Stack:** Python, MSAL Python, httpx, Microsoft Graph `calendarView`, pytest/unittest.

---

## Files

- Modify: `src/calendar_trigger.py` — add Outlook settings/client and provider factory.
- Modify: `src/scheduler.py` — call the provider factory instead of `GoogleCalendarClient.from_config()`.
- Modify: `tests/test_calendar_trigger.py` — add provider-selection and Outlook normalization/fallback tests.
- Modify: `requirements.txt` — add `msal`.
- Modify: `config/agent_config.yaml` — add Outlook defaults.
- Modify: docs — mark Outlook provider support complete and document environment variables.

## Tasks

- [ ] Add failing tests for `build_calendar_client()` selecting Google vs Outlook from config/env.
- [ ] Add failing tests for Outlook fallback when auth/config is unavailable.
- [ ] Add failing tests for Outlook Graph request parameters and normalized vendor meeting output.
- [ ] Implement `OutlookCalendarClient` with MSAL token cache, device-code auth, Graph request, keyword filtering, and mock fallback.
- [ ] Update scheduler to call `build_calendar_client()`.
- [ ] Update config, requirements, and docs.
- [ ] Run focused tests: `.venv/bin/pytest tests/test_calendar_trigger.py tests/test_phase8_calendar.py tests/test_scheduler.py -q`.
- [ ] Run full backend tests: `.venv/bin/pytest tests/ -q`.
- [ ] Commit and push.
