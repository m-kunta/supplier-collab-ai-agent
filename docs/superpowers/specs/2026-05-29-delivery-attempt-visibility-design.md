# Delivery Attempt Visibility Design

## Goal

Expose scheduled notification delivery attempts through the API and settings UI so operators can see sent, failed, and dead-letter notification outcomes without opening SQLite directly.

## Scope

This slice includes:

- `GET /api/deliveries` for recent delivery attempts.
- Optional `briefing_id` filter and `limit` query parameter.
- Frontend API helper and types.
- A compact "Recent Delivery Attempts" panel on `/settings`.

This slice does not include editing/replaying dead-letter attempts, a separate delivery-history page, or auth/permissions.

## Design

Use the existing `DeliveryAttemptStore.list_attempts()` as the source of truth. Add an API-level store instance in `api/main.py`, mirroring the settings/vendor store globals so tests can patch it easily. Return `{ attempts, total }` with the store's row shape intact.

The settings page should fetch delivery attempts independently from settings and schedule data. Failed delivery-attempt loading should not block the settings form. The UI shows a simple table with status, channel, briefing ID, attempts, last error, and update time. Empty state text should explain that no delivery attempts have been recorded yet.

## Testing

Add tests for:

- Backend `GET /api/deliveries` returns attempts and total.
- Backend `GET /api/deliveries?briefing_id=...&limit=...` passes filters to the store and limits results.
- Frontend helper calls `/api/deliveries` and supports query parameters.
- Settings page renders a delivery attempt row and empty state.

## Documentation

Update project docs to mention the new delivery-attempt API and settings-page visibility.
