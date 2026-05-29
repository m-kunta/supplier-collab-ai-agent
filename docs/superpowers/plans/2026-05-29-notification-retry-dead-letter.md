# Notification Retry Dead-Letter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable retry and dead-letter handling for scheduled notification delivery.

**Architecture:** Keep `NotificationDispatcher` as the single-attempt sender. Add a SQLite `DeliveryAttemptStore` for durable audit records and a `NotificationRetryService` that orchestrates channel-level retries, then wire the scheduler through that service.

**Tech Stack:** Python standard library `sqlite3`, Pydantic/dataclasses already in use, pytest, existing APScheduler scheduler module.

---

## Files

- Create: `src/delivery_attempt_store.py` — SQLite persistence for notification delivery attempt records.
- Create: `src/notification_retry.py` — retry/dead-letter orchestration service.
- Create: `tests/test_delivery_attempt_store.py` — store tests.
- Create: `tests/test_notification_retry.py` — retry service tests.
- Modify: `src/delivery.py` — add channel dispatch helper for one-channel retry attempts.
- Modify: `src/scheduler.py` — use `NotificationRetryService`.
- Modify: `tests/test_delivery.py` — cover one-channel dispatch helper.
- Modify: `tests/test_scheduler_integration.py` or scheduler tests found in repo — assert scheduler uses retry service.
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`, `TODO.md`, `docs/implementation_plan.md` — document Phase 10 retry/dead-letter status.

---

## Task 1: Delivery Attempt Store

**Files:**
- Create: `tests/test_delivery_attempt_store.py`
- Create: `src/delivery_attempt_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_delivery_attempt_store.py`:

```python
from src.delivery_attempt_store import DeliveryAttemptStore


def make_store(tmp_path):
    return DeliveryAttemptStore(db_path=tmp_path / "supplier_collab.db")


def make_payload():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-29",
        "briefing_id": "brief-123",
        "briefing_text": "Ready",
    }


def test_record_attempt_persists_row(tmp_path):
    store = make_store(tmp_path)

    row = store.record_attempt(
        briefing_id="brief-123",
        channel="slack",
        status="sent",
        attempt_count=1,
        payload=make_payload(),
        last_error="",
    )

    assert row["briefing_id"] == "brief-123"
    assert row["channel"] == "slack"
    assert row["status"] == "sent"
    assert row["attempt_count"] == 1
    assert row["payload"]["vendor"] == "Northstar Foods Co"
    assert row["created_at"].endswith("Z")
    assert row["updated_at"].endswith("Z")


def test_list_attempts_for_briefing_survives_new_store_instance(tmp_path):
    store = make_store(tmp_path)
    store.record_attempt("brief-123", "slack", "failed", 1, make_payload(), "timeout")
    store.record_attempt("brief-123", "slack", "sent", 2, make_payload(), "")
    store.record_attempt("other", "email", "sent", 1, make_payload(), "")

    rows = make_store(tmp_path).list_attempts(briefing_id="brief-123")

    assert [row["status"] for row in rows] == ["failed", "sent"]
    assert rows[0]["last_error"] == "timeout"


def test_list_attempts_without_filter_returns_all(tmp_path):
    store = make_store(tmp_path)
    store.record_attempt("brief-123", "slack", "sent", 1, make_payload(), "")
    store.record_attempt("brief-456", "email", "dead_letter", 3, make_payload(), "smtp")

    rows = store.list_attempts()

    assert len(rows) == 2
    assert {row["briefing_id"] for row in rows} == {"brief-123", "brief-456"}
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_delivery_attempt_store.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.delivery_attempt_store'`.

- [ ] **Step 3: Implement store**

Create `src/delivery_attempt_store.py`:

```python
"""SQLite-backed delivery attempt store."""
from __future__ import annotations

import datetime
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")


class DeliveryAttemptStore:
    def __init__(self, db_path: Path | str = _DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS delivery_attempts (
                    id TEXT PRIMARY KEY,
                    briefing_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    last_error TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "briefing_id": row["briefing_id"],
            "channel": row["channel"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "payload": json.loads(row["payload_json"]),
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def record_attempt(
        self,
        briefing_id: str,
        channel: str,
        status: str,
        attempt_count: int,
        payload: dict[str, Any],
        last_error: str = "",
    ) -> dict[str, Any]:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        row_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO delivery_attempts (
                    id, briefing_id, channel, status, attempt_count,
                    payload_json, last_error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    briefing_id,
                    channel,
                    status,
                    attempt_count,
                    json.dumps(payload),
                    last_error,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM delivery_attempts WHERE id = ?",
                (row_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def list_attempts(self, briefing_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM delivery_attempts"
        params: tuple[str, ...] = ()
        if briefing_id is not None:
            query += " WHERE briefing_id = ?"
            params = (briefing_id,)
        query += " ORDER BY created_at ASC, attempt_count ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_delivery_attempt_store.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/delivery_attempt_store.py tests/test_delivery_attempt_store.py
git commit -m "feat(delivery): add delivery attempt store"
```

---

## Task 2: Channel Dispatch Helper

**Files:**
- Modify: `src/delivery.py`
- Modify: `tests/test_delivery.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_delivery.py`:

```python
def test_dispatch_channel_sends_only_requested_channel():
    settings = make_settings(
        slack_webhook_url="https://hooks.slack.com/fake",
        teams_webhook_url="https://teams.webhook.fake/url",
    )
    dispatcher = NotificationDispatcher(settings)

    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        result = dispatcher.dispatch_channel("slack", make_briefing())

    assert result.channel == "slack"
    assert result.success is True
    assert mock_post.call_count == 1
    assert mock_post.call_args.args[0] == "https://hooks.slack.com/fake"


def test_dispatch_channel_returns_failure_for_unconfigured_channel():
    dispatcher = NotificationDispatcher(make_settings())

    result = dispatcher.dispatch_channel("slack", make_briefing())

    assert result.channel == "slack"
    assert result.success is False
    assert "not configured" in result.error
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_delivery.py::test_dispatch_channel_sends_only_requested_channel tests/test_delivery.py::test_dispatch_channel_returns_failure_for_unconfigured_channel -q
```

Expected: FAIL with `AttributeError: 'NotificationDispatcher' object has no attribute 'dispatch_channel'`.

- [ ] **Step 3: Implement helper**

In `src/delivery.py`, add this method to `NotificationDispatcher` after `dispatch`:

```python
    def dispatch_channel(self, channel: str, briefing: dict[str, Any]) -> DeliveryResult:
        if channel == "slack":
            if not self.settings.slack_webhook_url:
                return DeliveryResult("slack", False, "slack channel not configured")
            return self._send_slack(briefing)
        if channel == "teams":
            if not self.settings.teams_webhook_url:
                return DeliveryResult("teams", False, "teams channel not configured")
            return self._send_teams(briefing)
        if channel == "email":
            if not (self.settings.email_enabled and self.settings.email_to):
                return DeliveryResult("email", False, "email channel not configured")
            return self._send_email(briefing)
        return DeliveryResult(channel, False, f"unknown channel: {channel}")
```

- [ ] **Step 4: Run delivery tests**

```bash
.venv/bin/pytest tests/test_delivery.py -q
```

Expected: all delivery tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/delivery.py tests/test_delivery.py
git commit -m "feat(delivery): dispatch individual notification channels"
```

---

## Task 3: Notification Retry Service

**Files:**
- Create: `tests/test_notification_retry.py`
- Create: `src/notification_retry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_notification_retry.py`:

```python
from src.delivery import DeliveryResult, NotificationSettings
from src.delivery_attempt_store import DeliveryAttemptStore
from src.notification_retry import NotificationRetryService


class FakeDispatcher:
    def __init__(self, results_by_channel):
        self.results_by_channel = {
            channel: list(results)
            for channel, results in results_by_channel.items()
        }
        self.calls = []

    def dispatch_channel(self, channel, briefing):
        self.calls.append(channel)
        return self.results_by_channel[channel].pop(0)


def make_briefing():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-29",
        "briefing_id": "brief-123",
        "briefing_text": "Ready",
    }


def test_successful_channel_records_one_sent_attempt(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "slack": [DeliveryResult("slack", True)],
    })
    service = NotificationRetryService(
        NotificationSettings(slack_webhook_url="https://hooks.slack.com/fake"),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("slack", True)]
    assert dispatcher.calls == ["slack"]
    rows = store.list_attempts("brief-123")
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["attempt_count"] == 1


def test_failed_channel_retries_until_success(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "slack": [
            DeliveryResult("slack", False, "timeout"),
            DeliveryResult("slack", True),
        ],
    })
    service = NotificationRetryService(
        NotificationSettings(slack_webhook_url="https://hooks.slack.com/fake"),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
        max_attempts=3,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("slack", True)]
    assert dispatcher.calls == ["slack", "slack"]
    rows = store.list_attempts("brief-123")
    assert [row["status"] for row in rows] == ["failed", "sent"]
    assert rows[0]["last_error"] == "timeout"
    assert rows[1]["attempt_count"] == 2


def test_exhausted_channel_records_dead_letter(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "email": [
            DeliveryResult("email", False, "smtp down"),
            DeliveryResult("email", False, "smtp down"),
        ],
    })
    service = NotificationRetryService(
        NotificationSettings(
            email_enabled=True,
            email_smtp_host="smtp.example.com",
            email_from="from@example.com",
            email_to=["buyer@example.com"],
        ),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
        max_attempts=2,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("email", False, "smtp down")]
    rows = store.list_attempts("brief-123")
    assert [row["status"] for row in rows] == ["failed", "dead_letter"]
    assert rows[-1]["attempt_count"] == 2
    assert rows[-1]["last_error"] == "smtp down"


def test_no_configured_channels_returns_empty_and_records_nothing(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({})
    service = NotificationRetryService(
        NotificationSettings(),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == []
    assert store.list_attempts() == []
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_notification_retry.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.notification_retry'`.

- [ ] **Step 3: Implement retry service**

Create `src/notification_retry.py`:

```python
"""Retry/dead-letter orchestration for notification delivery."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from src.delivery import DeliveryResult, NotificationDispatcher, NotificationSettings
from src.delivery_attempt_store import DeliveryAttemptStore

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")


class NotificationRetryService:
    def __init__(
        self,
        settings: NotificationSettings,
        attempt_store: DeliveryAttemptStore | None = None,
        dispatcher_factory: Callable[[NotificationSettings], NotificationDispatcher] = NotificationDispatcher,
        max_attempts: int = 3,
    ) -> None:
        self.settings = settings
        self.attempt_store = attempt_store or DeliveryAttemptStore(
            os.getenv("SUPPLIER_COLLAB_DB_PATH", str(_DEFAULT_DB_PATH))
        )
        self.dispatcher = dispatcher_factory(settings)
        self.max_attempts = max_attempts

    def _configured_channels(self) -> list[str]:
        channels: list[str] = []
        if self.settings.slack_webhook_url:
            channels.append("slack")
        if self.settings.teams_webhook_url:
            channels.append("teams")
        if self.settings.email_enabled and self.settings.email_to:
            channels.append("email")
        return channels

    def dispatch_with_retries(self, briefing: dict[str, Any]) -> list[DeliveryResult]:
        final_results: list[DeliveryResult] = []
        briefing_id = str(briefing.get("briefing_id") or "")

        for channel in self._configured_channels():
            final_result = DeliveryResult(channel, False, "not attempted")
            for attempt in range(1, self.max_attempts + 1):
                result = self.dispatcher.dispatch_channel(channel, briefing)
                final_result = result
                if result.success:
                    self.attempt_store.record_attempt(
                        briefing_id=briefing_id,
                        channel=channel,
                        status="sent",
                        attempt_count=attempt,
                        payload=briefing,
                        last_error="",
                    )
                    break

                status = "dead_letter" if attempt == self.max_attempts else "failed"
                self.attempt_store.record_attempt(
                    briefing_id=briefing_id,
                    channel=channel,
                    status=status,
                    attempt_count=attempt,
                    payload=briefing,
                    last_error=result.error,
                )
            final_results.append(final_result)

        return final_results
```

- [ ] **Step 4: Run retry tests**

```bash
.venv/bin/pytest tests/test_notification_retry.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/notification_retry.py tests/test_notification_retry.py
git commit -m "feat(delivery): add notification retry service"
```

---

## Task 4: Scheduler Wiring and Docs

**Files:**
- Modify: `src/scheduler.py`
- Modify: relevant scheduler test file
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`, `TODO.md`, `docs/implementation_plan.md`

- [ ] **Step 1: Find scheduler tests**

```bash
rg -n "BriefingScheduler|_trigger_briefing|NotificationDispatcher|dispatch" tests -g '*.py'
```

Use the scheduler test file found by this command for Step 2.

- [ ] **Step 2: Add failing scheduler test**

Add a test that patches `src.notification_retry.NotificationRetryService`, triggers `_trigger_briefing`, and asserts `dispatch_with_retries` is called with a payload containing `vendor`, `meeting_date`, `briefing_text`, and `output_files`.

Use the existing scheduler tests' setup patterns for mocking `summarize_request` and settings.

- [ ] **Step 3: Run scheduler test and confirm it fails**

```bash
.venv/bin/pytest <scheduler-test-file> -q
```

Expected: FAIL because scheduler still constructs `NotificationDispatcher` directly.

- [ ] **Step 4: Wire scheduler to retry service**

In `src/scheduler.py`, replace:

```python
            from src.delivery import NotificationDispatcher
            from src.store_factory import create_settings_store
            settings = create_settings_store().load()
            dispatcher = NotificationDispatcher(settings)
```

with:

```python
            from src.notification_retry import NotificationRetryService
            from src.store_factory import create_settings_store
            settings = create_settings_store().load()
            dispatcher = NotificationRetryService(settings)
```

Keep the existing:

```python
            delivery_results = dispatcher.dispatch(briefing_payload)
```

but change it to:

```python
            delivery_results = dispatcher.dispatch_with_retries(briefing_payload)
```

- [ ] **Step 5: Update docs**

Update docs to state:

- Phase 10 backend retry/dead-letter handling is implemented for scheduled notifications.
- Delivery attempts are persisted in SQLite table `delivery_attempts`.
- `NotificationDispatcher` remains single-attempt; `NotificationRetryService` handles retry orchestration.

- [ ] **Step 6: Run full verification**

```bash
.venv/bin/pytest tests/ -q
cd frontend && npm test -- --no-cache
```

Expected: all backend and frontend tests pass.

- [ ] **Step 7: Commit and push**

```bash
git add src/scheduler.py tests README.md AGENTS.md CLAUDE.md TODO.md docs/implementation_plan.md
git commit -m "feat(delivery): wire notification retry dead-letter flow"
git push origin master
```

---

## Self-Review

- Spec coverage: The plan covers durable attempt storage, channel-level dispatch, retry/dead-letter orchestration, scheduler wiring, docs, and full verification.
- Placeholder scan: No implementation placeholders remain.
- Type consistency: Store and service method names match across tasks.
