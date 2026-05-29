# Notification Retry and Dead-Letter Design

## Goal

Add durable notification delivery attempt tracking, retry behavior, and dead-letter status for scheduled briefing notifications without changing frontend behavior.

## Scope

This slice covers backend notification reliability only:

- Persist delivery attempts for Slack, Teams, and email channels.
- Retry failed channel sends up to a configured maximum.
- Mark exhausted failures as `dead_letter`.
- Wire scheduled briefing notifications through the retry service.

This slice does not add a UI, an API endpoint for delivery history, a background queue worker, or external infrastructure such as Redis/Celery.

## Design

Keep `NotificationDispatcher` responsible for a single send attempt to all configured channels. Add a new `NotificationRetryService` that orchestrates retries around the dispatcher and writes attempt records to a new SQLite-backed `DeliveryAttemptStore`.

The service runs synchronously inside the scheduler path for this first Phase 10 increment. This keeps the feature simple and testable while still producing durable audit records and final dead-letter rows.

## Data Model

Create a SQLite table named `delivery_attempts`:

- `id TEXT PRIMARY KEY`
- `briefing_id TEXT NOT NULL`
- `channel TEXT NOT NULL`
- `status TEXT NOT NULL` — `pending`, `sent`, `failed`, or `dead_letter`
- `attempt_count INTEGER NOT NULL`
- `payload_json TEXT NOT NULL`
- `last_error TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

The store uses `SUPPLIER_COLLAB_DB_PATH` when provided and otherwise defaults to `config/supplier_collab.db`, matching the SQLite persistence work.

## Retry Behavior

For each configured channel:

- Call the dispatcher through a channel-specific dispatch method.
- Record every channel result in `delivery_attempts`.
- Stop retrying a channel when it succeeds.
- Retry failed sends up to `max_attempts`, default `3`.
- Mark final failed attempts as `dead_letter`.

`NotificationRetryService.dispatch_with_retries(briefing)` returns the final `DeliveryResult` for each attempted channel.

## Scheduler Wiring

`BriefingScheduler._trigger_briefing()` currently creates `NotificationDispatcher` directly and logs returned results. Replace that with `NotificationRetryService(settings).dispatch_with_retries(briefing_payload)`. Preserve current success/failure logging semantics.

## Testing

Add tests for:

- SQLite delivery attempt store creates and lists attempts.
- Attempt records persist across store instances.
- Retry service sends once when the first attempt succeeds.
- Retry service retries failures and succeeds before max attempts.
- Retry service marks final failures as `dead_letter`.
- Scheduler uses `NotificationRetryService` instead of directly dispatching.

## Documentation

Update README/AGENTS/CLAUDE/TODO and implementation docs to mark Phase 10 notification retry/dead-letter handling complete for the backend scheduler path.
