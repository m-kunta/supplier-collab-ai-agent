# Google Calendar OAuth Configuration Design

## Goal

Harden the existing Google Calendar OAuth integration so the scheduler can be configured from `config/agent_config.yaml` and environment variables, while preserving the safe mock fallback for local development and demos.

## Scope

This slice covers Google Calendar only. Microsoft Outlook / Graph OAuth remains the next independent Phase 10 task.

## Behavior

- `BriefingScheduler` should construct the calendar client from project config instead of hard-coded constructor defaults.
- `GoogleCalendarClient` should support configurable credentials path, token path, calendar ID, vendor-match keywords, and mock fallback behavior.
- Environment variables should override YAML config for deployment-friendly setup:
  - `SUPPLIER_COLLAB_CALENDAR_PROVIDER`
  - `GOOGLE_CALENDAR_CREDENTIALS_PATH`
  - `GOOGLE_CALENDAR_TOKEN_PATH`
  - `GOOGLE_CALENDAR_ID`
  - `GOOGLE_CALENDAR_VENDOR_KEYWORDS`
  - `GOOGLE_CALENDAR_ALLOW_MOCK_FALLBACK`
- Missing OAuth credentials should continue returning mock vendor meetings when fallback is enabled.
- Missing OAuth credentials should return an empty list when fallback is disabled.
- Token saving should create the token directory if needed.
- Event polling should use the configured Google calendar ID instead of always using `primary`.
- Vendor-meeting filtering should use configured keywords instead of a fixed list.

## Non-Goals

- No Outlook / Microsoft Graph implementation in this slice.
- No hosted OAuth callback service.
- No frontend settings UI for calendar credentials.
- No encrypted secret storage beyond accepting external paths and environment variables.

## Risks

- Installed-app OAuth is acceptable for local/pilot usage but is not the final enterprise SSO model.
- Calendar event title heuristics are intentionally simple; richer vendor matching should come after vendor identity workflows mature.
