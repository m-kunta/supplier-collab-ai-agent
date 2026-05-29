# Delivery Attempt Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose notification delivery attempts through a backend API and a compact settings-page panel.

**Architecture:** Add a FastAPI route backed by `DeliveryAttemptStore`, a typed frontend helper, and a settings-page table that loads attempts independently from settings/schedule data.

**Tech Stack:** FastAPI, SQLite-backed store already in `src/delivery_attempt_store.py`, Next.js React page, Vitest, pytest.

---

## Tasks

- [ ] Add backend API tests and route for `GET /api/deliveries`.
- [ ] Add frontend API types/helper and tests.
- [ ] Add settings-page delivery attempts panel and tests.
- [ ] Update docs, run full backend/frontend verification, commit, and push.

## Backend Route Details

`GET /api/deliveries`

Query parameters:

- `briefing_id?: string`
- `limit: int = 50`, constrained from 1 to 200

Response:

```json
{
  "attempts": [
    {
      "id": "uuid",
      "briefing_id": "brief-123",
      "channel": "slack",
      "status": "dead_letter",
      "attempt_count": 3,
      "payload": {},
      "last_error": "timeout",
      "created_at": "2026-05-29T00:00:00Z",
      "updated_at": "2026-05-29T00:00:00Z"
    }
  ],
  "total": 1
}
```

## Frontend Panel Details

Settings page copy:

- Heading: `Recent Delivery Attempts`
- Empty state: `No delivery attempts recorded yet.`
- Columns: `Status`, `Channel`, `Briefing`, `Attempts`, `Last Error`, `Updated`

## Verification

Run:

```bash
.venv/bin/pytest tests/ -q
cd frontend && npm test -- --no-cache
```

Expected: all tests pass.
