# Outlook Calendar OAuth Design

## Goal

Add Microsoft Outlook / Graph calendar ingestion as a selectable Phase 10 calendar provider while preserving the existing Google Calendar behavior and mock fallback safety.

## Scope

- Add an Outlook calendar client that uses Microsoft Graph delegated `Calendars.Read` access.
- Select the calendar provider from `calendar.provider` or `SUPPLIER_COLLAB_CALENDAR_PROVIDER`.
- Normalize Outlook events to the scheduler's existing meeting shape:
  - `id`
  - `summary`
  - `start_time`
  - `creator`
- Keep `BriefingScheduler` unchanged except for using a provider factory.
- Preserve mock fallback behavior when Outlook auth/config is unavailable.

## Configuration

Outlook settings live under the existing `calendar` section:

```yaml
calendar:
  provider: google
  outlook_client_id: ""
  outlook_tenant_id: common
  outlook_token_cache_path: config/outlook_token_cache.json
  outlook_scopes:
    - Calendars.Read
```

Environment overrides:

- `SUPPLIER_COLLAB_CALENDAR_PROVIDER=outlook`
- `OUTLOOK_CALENDAR_CLIENT_ID`
- `OUTLOOK_CALENDAR_TENANT_ID`
- `OUTLOOK_CALENDAR_TOKEN_CACHE_PATH`
- `OUTLOOK_CALENDAR_SCOPES`

## Non-Goals

- No Microsoft Graph application-permission daemon flow.
- No admin consent workflow.
- No frontend credential management.
- No encrypted token cache.

## Implementation Notes

- Use MSAL device-code flow so local/pilot users can authenticate without a hosted callback URL.
- Use `https://graph.microsoft.com/v1.0/me/calendarView` with `startDateTime`, `endDateTime`, `$top`, `$orderby`, and `$select`.
- Filter by configured vendor keywords the same way Google events are filtered.
- If no cached token is available, authentication may require user interaction; tests should mock MSAL so CI never blocks.
