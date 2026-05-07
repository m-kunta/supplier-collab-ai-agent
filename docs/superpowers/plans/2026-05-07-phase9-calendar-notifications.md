# Phase 9: Calendar & Notification Automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> ⚠️ **PROTOTYPE NOTE** — This entire phase is a prototype / proof-of-concept.
> - Calendar ingestion uses a **mock JSON schedule** (no live Google Calendar OAuth in prod).
> - Delivery uses **real HTTP POST** for webhooks and **real SMTP** for email, but is wired to env-var-configurable targets — no credentials are hardcoded.
> - The settings store is **file-based JSON** (`config/notification_settings.json`) — not a database.
> - The frontend settings page is intentionally minimal: no auth, no multi-user, no persistence beyond the JSON file.
> - Everything is generic enough to swap real implementations in later without restructuring.

**Goal:** Wire automated briefing triggers (calendar → pipeline → delivery) and a frontend settings page for notification preferences.

**Architecture:** A pluggable `NotificationDispatcher` in `src/delivery.py` holds channel implementations (Slack, Teams, Email); the existing `BriefingScheduler._trigger_briefing()` calls it after a successful run. Calendar ingestion already supports mock fallback via `src/calendar_trigger.py`. A new `SettingsStore` mirrors `BriefingStore` patterns (file-backed JSON). Two new API routes expose settings CRUD. A new Next.js page at `/settings` renders the config form.

**Tech Stack:** Python 3.9, FastAPI, APScheduler (already present), `smtplib` (stdlib), `httpx` (already in requirements), Next.js 14, React, TypeScript.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/delivery.py` | `NotificationDispatcher` + channel impls (Slack, Teams, Email) |
| Create | `src/settings_store.py` | File-backed JSON settings store |
| Modify | `src/scheduler.py` | Call `delivery.dispatch()` after `_trigger_briefing` succeeds |
| Modify | `api/schemas.py` | Add `NotificationSettings` Pydantic model |
| Modify | `api/main.py` | Add `GET/PUT /api/settings` routes + `GET /api/schedule` (mock jobs) |
| Create | `tests/test_delivery.py` | Unit tests for dispatcher + channels |
| Create | `tests/test_settings_store.py` | Unit tests for settings CRUD |
| Create | `tests/test_settings_api.py` | FastAPI test-client tests for settings routes |
| Create | `frontend/app/settings/page.tsx` | Settings dashboard page |
| Create | `frontend/app/settings/page.test.tsx` | Rendering + form interaction tests |
| Create | `frontend/components/NotificationSettingsForm.tsx` | Controlled form component |
| Create | `frontend/components/NotificationSettingsForm.test.tsx` | Component unit tests |
| Modify | `frontend/components/AppHeader.tsx` | Add "Settings" nav link |
| Modify | `frontend/lib/api.ts` | Add `getSettings()` / `updateSettings()` API helpers |

---

## Task 1: Delivery Module (`src/delivery.py`)

**Files:**
- Create: `src/delivery.py`
- Create: `tests/test_delivery.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_delivery.py
import pytest
from unittest.mock import patch, MagicMock
from src.delivery import NotificationDispatcher, NotificationSettings, DeliveryResult


def make_settings(**overrides):
    base = {
        "slack_webhook_url": "",
        "teams_webhook_url": "",
        "email_enabled": False,
        "email_smtp_host": "",
        "email_smtp_port": 587,
        "email_smtp_user": "",
        "email_smtp_password": "",
        "email_from": "",
        "email_to": [],
    }
    return NotificationSettings(**{**base, **overrides})


def make_briefing():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-08",
        "briefing_id": "abc-123",
        "briefing_text": "Executive summary...",
        "output_files": {"docx_path": "/tmp/briefing.docx"},
    }


def test_dispatcher_no_channels_enabled():
    dispatcher = NotificationDispatcher(make_settings())
    results = dispatcher.dispatch(make_briefing())
    assert results == []


def test_slack_channel_sends_post():
    settings = make_settings(slack_webhook_url="https://hooks.slack.com/fake")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 1
    assert results[0].channel == "slack"
    assert results[0].success is True
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert "Northstar Foods Co" in payload["text"]


def test_teams_channel_sends_post():
    settings = make_settings(teams_webhook_url="https://teams.webhook.fake/url")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 1
    assert results[0].channel == "teams"
    assert results[0].success is True


def test_slack_channel_handles_http_error():
    settings = make_settings(slack_webhook_url="https://hooks.slack.com/fake")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post", side_effect=Exception("timeout")):
        results = dispatcher.dispatch(make_briefing())
    assert results[0].success is False
    assert "timeout" in results[0].error


def test_email_channel_sends_when_enabled():
    settings = make_settings(
        email_enabled=True,
        email_smtp_host="smtp.example.com",
        email_from="from@example.com",
        email_to=["buyer@example.com"],
    )
    dispatcher = NotificationDispatcher(settings)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        results = dispatcher.dispatch(make_briefing())
    assert results[0].channel == "email"
    assert results[0].success is True


def test_email_skipped_when_no_recipients():
    settings = make_settings(email_enabled=True, email_smtp_host="smtp.example.com",
                              email_from="from@example.com", email_to=[])
    dispatcher = NotificationDispatcher(settings)
    results = dispatcher.dispatch(make_briefing())
    assert results == []


def test_multiple_channels_dispatched():
    settings = make_settings(
        slack_webhook_url="https://hooks.slack.com/fake",
        teams_webhook_url="https://teams.webhook.fake/url",
    )
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 2
    channels = {r.channel for r in results}
    assert channels == {"slack", "teams"}
```

- [ ] **Step 2: Run tests — expect ImportError / FAIL**

```bash
.venv/bin/pytest tests/test_delivery.py -v
```
Expected: `ImportError: cannot import name 'NotificationDispatcher' from 'src.delivery'`

- [ ] **Step 3: Implement `src/delivery.py`**

```python
"""Notification delivery module (prototype).

Dispatches briefing summaries to configured channels: Slack webhook,
Teams webhook, and SMTP email. All channels are optional — only channels
with non-empty config are activated.

PROTOTYPE: No retry logic, no queue. Fire-and-forget per channel.
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NotificationSettings(BaseModel):
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_from: str = ""
    email_to: list[str] = field(default_factory=list)

    class Config:
        # Allow field() defaults for mutable types
        arbitrary_types_allowed = True


@dataclass
class DeliveryResult:
    channel: str
    success: bool
    error: str = ""


class NotificationDispatcher:
    """Sends a briefing summary to all configured channels."""

    def __init__(self, settings: NotificationSettings) -> None:
        self.settings = settings

    def dispatch(self, briefing: dict[str, Any]) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        s = self.settings

        if s.slack_webhook_url:
            results.append(self._send_slack(briefing))

        if s.teams_webhook_url:
            results.append(self._send_teams(briefing))

        if s.email_enabled and s.email_to:
            results.append(self._send_email(briefing))

        return results

    # ------------------------------------------------------------------
    def _send_slack(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        text = (
            f":clipboard: *Supplier Briefing Ready* — {vendor} ({date})\n"
            f"Briefing ID: `{bid}`\n"
            f"Open in dashboard: http://localhost:3000/briefings/{bid}"
        )
        try:
            resp = httpx.post(
                self.settings.slack_webhook_url,
                json={"text": text},
                timeout=10,
            )
            if resp.status_code != 200:
                return DeliveryResult("slack", False, f"HTTP {resp.status_code}: {resp.text}")
            return DeliveryResult("slack", True)
        except Exception as exc:
            return DeliveryResult("slack", False, str(exc))

    def _send_teams(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0072C6",
            "summary": f"Briefing ready for {vendor}",
            "sections": [{
                "activityTitle": f"Supplier Briefing Ready: {vendor}",
                "activitySubtitle": f"Meeting: {date}",
                "facts": [{"name": "Briefing ID", "value": bid}],
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "Open Dashboard",
                "targets": [{"os": "default", "uri": f"http://localhost:3000/briefings/{bid}"}],
            }],
        }
        try:
            resp = httpx.post(self.settings.teams_webhook_url, json=payload, timeout=10)
            if resp.status_code != 200:
                return DeliveryResult("teams", False, f"HTTP {resp.status_code}: {resp.text}")
            return DeliveryResult("teams", True)
        except Exception as exc:
            return DeliveryResult("teams", False, str(exc))

    def _send_email(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        text_body = briefing.get("briefing_text", "")[:500] + "..."
        s = self.settings

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Briefing Ready] {vendor} — {date}"
        msg["From"] = s.email_from
        msg["To"] = ", ".join(s.email_to)
        msg.attach(MIMEText(
            f"Briefing for {vendor} ({date}) is ready.\n\nPreview:\n{text_body}\n\n"
            f"View: http://localhost:3000/briefings/{bid}\nID: {bid}",
            "plain",
        ))

        try:
            with smtplib.SMTP(s.email_smtp_host, s.email_smtp_port) as server:
                if s.email_smtp_user:
                    server.starttls()
                    server.login(s.email_smtp_user, s.email_smtp_password)
                server.sendmail(s.email_from, s.email_to, msg.as_string())
            return DeliveryResult("email", True)
        except Exception as exc:
            return DeliveryResult("email", False, str(exc))
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/test_delivery.py -v
```
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/delivery.py tests/test_delivery.py
git commit -m "feat(phase9): add NotificationDispatcher with Slack/Teams/email channels"
```

---

## Task 2: Settings Store (`src/settings_store.py`)

**Files:**
- Create: `src/settings_store.py`
- Create: `tests/test_settings_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_settings_store.py
import json
import pytest
from pathlib import Path
from src.settings_store import SettingsStore
from src.delivery import NotificationSettings


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_path=tmp_path / "notification_settings.json")


def test_load_returns_defaults_when_file_missing(store):
    settings = store.load()
    assert isinstance(settings, NotificationSettings)
    assert settings.slack_webhook_url == ""
    assert settings.email_enabled is False


def test_save_and_reload(store):
    original = store.load()
    original.slack_webhook_url = "https://hooks.slack.com/T123"
    store.save(original)
    reloaded = store.load()
    assert reloaded.slack_webhook_url == "https://hooks.slack.com/T123"


def test_save_writes_valid_json(store):
    settings = store.load()
    settings.email_enabled = True
    settings.email_to = ["a@b.com"]
    store.save(settings)
    raw = json.loads(store.settings_path.read_text())
    assert raw["email_enabled"] is True
    assert raw["email_to"] == ["a@b.com"]


def test_update_partial(store):
    store.save(store.load())  # write defaults
    store.update({"slack_webhook_url": "https://x.com"})
    assert store.load().slack_webhook_url == "https://x.com"


def test_update_ignores_unknown_keys(store):
    store.update({"nonexistent_key": "value"})
    settings = store.load()
    assert not hasattr(settings, "nonexistent_key")
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/bin/pytest tests/test_settings_store.py -v
```
Expected: `ImportError: cannot import name 'SettingsStore'`

- [ ] **Step 3: Implement `src/settings_store.py`**

```python
"""File-backed JSON store for notification settings (prototype).

PROTOTYPE: Single-file, no locking across processes, no migrations.
Swap for a proper DB store when productionising.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from src.delivery import NotificationSettings

_DEFAULT_PATH = Path("config/notification_settings.json")


class SettingsStore:
    def __init__(self, settings_path: Path = _DEFAULT_PATH) -> None:
        self.settings_path = settings_path
        self._lock = threading.Lock()

    def load(self) -> NotificationSettings:
        with self._lock:
            if not self.settings_path.exists():
                return NotificationSettings()
            raw = json.loads(self.settings_path.read_text())
            return NotificationSettings(**{k: v for k, v in raw.items()
                                           if k in NotificationSettings.__fields__})

    def save(self, settings: NotificationSettings) -> None:
        with self._lock:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(settings.json(indent=2))

    def update(self, partial: dict[str, Any]) -> NotificationSettings:
        current = self.load()
        valid_keys = set(NotificationSettings.__fields__)
        for k, v in partial.items():
            if k in valid_keys:
                setattr(current, k, v)
        self.save(current)
        return current
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/test_settings_store.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/settings_store.py tests/test_settings_store.py
git commit -m "feat(phase9): add file-backed SettingsStore for notification config"
```

---

## Task 3: Wire Delivery into Scheduler

**Files:**
- Modify: `src/scheduler.py` (lines 100–132 — `_trigger_briefing`)

- [ ] **Step 1: Replace the `# FUTURE` comment in `_trigger_briefing`**

In `src/scheduler.py`, after `logger.info(f"Successfully generated briefing! Saved to: {saved_path}")`, replace the `# FUTURE` comment block:

```python
    def _trigger_briefing(self, meeting: dict, phase: str):
        logger.info(f"*** AUTO-TRIGGER *** Generating {phase} briefing for: {meeting['summary']}")

        summary = meeting.get('summary', '')
        vendor_name = "Northstar Foods Co"
        if ":" in summary:
            vendor_name = summary.split(":", 1)[1].strip()

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

            # Dispatch notifications
            from src.delivery import NotificationDispatcher
            from src.settings_store import SettingsStore
            settings = SettingsStore().load()
            dispatcher = NotificationDispatcher(settings)
            briefing_payload = {
                "vendor": vendor_name,
                "meeting_date": meeting_date,
                "briefing_id": result.get("briefing_id", ""),
                "briefing_text": result.get("briefing_text", ""),
                "output_files": output_files,
            }
            delivery_results = dispatcher.dispatch(briefing_payload)
            for dr in delivery_results:
                if dr.success:
                    logger.info(f"Notified [{dr.channel}] successfully.")
                else:
                    logger.warning(f"Notification [{dr.channel}] failed: {dr.error}")

        except Exception as e:
            logger.error(f"Failed to generate scheduled briefing for {vendor_name}: {e}")
```

- [ ] **Step 2: Run full backend tests to confirm no regressions**

```bash
.venv/bin/pytest tests/ -q
```
Expected: all tests pass (existing suite + new delivery/settings tests)

- [ ] **Step 3: Commit**

```bash
git add src/scheduler.py
git commit -m "feat(phase9): wire NotificationDispatcher into BriefingScheduler"
```

---

## Task 4: Settings API Routes

**Files:**
- Modify: `api/schemas.py` — add `NotificationSettingsPayload`
- Modify: `api/main.py` — add `GET /api/settings` and `PUT /api/settings`
- Create: `tests/test_settings_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# tests/test_settings_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)


def test_get_settings_returns_defaults():
    with patch("api.main.settings_store") as mock_store:
        from src.delivery import NotificationSettings
        mock_store.load.return_value = NotificationSettings()
        resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slack_webhook_url"] == ""
    assert data["email_enabled"] is False


def test_put_settings_updates_and_returns():
    with patch("api.main.settings_store") as mock_store:
        from src.delivery import NotificationSettings
        updated = NotificationSettings(slack_webhook_url="https://hooks.slack.com/X")
        mock_store.update.return_value = updated
        resp = client.put("/api/settings", json={"slack_webhook_url": "https://hooks.slack.com/X"})
    assert resp.status_code == 200
    assert resp.json()["slack_webhook_url"] == "https://hooks.slack.com/X"


def test_get_schedule_returns_list():
    resp = client.get("/api/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/bin/pytest tests/test_settings_api.py -v
```
Expected: FAIL — routes not defined yet

- [ ] **Step 3: Add `NotificationSettingsPayload` to `api/schemas.py`**

Append to `api/schemas.py`:

```python
from src.delivery import NotificationSettings

# Re-export so routes can reference it from schemas
NotificationSettingsPayload = NotificationSettings
```

- [ ] **Step 4: Add routes to `api/main.py`**

Add the following imports near the top of `api/main.py` (after existing src imports):

```python
from src.delivery import NotificationSettings
from src.settings_store import SettingsStore
```

Add a module-level store instance (after `briefing_store = BriefingStore()`):

```python
settings_store = SettingsStore()
```

Add routes at the bottom of `api/main.py` (before or after the existing briefing routes):

```python
# ---------------------------------------------------------------------------
# Notification Settings (Phase 9 — prototype)
# ---------------------------------------------------------------------------

@app.get("/api/settings")
def get_settings() -> dict:
    """Return current notification settings."""
    return settings_store.load().dict()


@app.put("/api/settings")
def update_settings(payload: dict) -> dict:
    """Partial-update notification settings and persist."""
    updated = settings_store.update(payload)
    return updated.dict()


@app.get("/api/schedule")
def get_schedule() -> dict:
    """Return upcoming scheduled briefing jobs (from APScheduler)."""
    jobs = []
    for job in scheduler.scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {"jobs": jobs}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/test_settings_api.py -v
```
Expected: 3 PASSED

- [ ] **Step 6: Run full backend suite**

```bash
.venv/bin/pytest tests/ -q
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add api/main.py api/schemas.py tests/test_settings_api.py
git commit -m "feat(phase9): add GET/PUT /api/settings and GET /api/schedule routes"
```

---

## Task 5: Frontend API Helpers (`frontend/lib/api.ts`)

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts` (add new test cases)

- [ ] **Step 1: Add `NotificationSettings` type and helpers to `frontend/lib/api.ts`**

Append to `frontend/lib/api.ts`:

```typescript
// ---------------------------------------------------------------------------
// Notification Settings (Phase 9 — prototype)
// ---------------------------------------------------------------------------

export interface NotificationSettings {
  slack_webhook_url: string;
  teams_webhook_url: string;
  email_enabled: boolean;
  email_smtp_host: string;
  email_smtp_port: number;
  email_smtp_user: string;
  email_smtp_password: string;
  email_from: string;
  email_to: string[];
}

export interface ScheduledJob {
  id: string;
  name: string;
  next_run: string | null;
}

export interface ScheduleResponse {
  jobs: ScheduledJob[];
}

export async function getSettings(): Promise<NotificationSettings> {
  const res = await fetch(`${API_BASE}/api/settings`);
  if (!res.ok) throw new Error(`Failed to load settings: ${res.status}`);
  return res.json();
}

export async function updateSettings(
  partial: Partial<NotificationSettings>
): Promise<NotificationSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(partial),
  });
  if (!res.ok) throw new Error(`Failed to update settings: ${res.status}`);
  return res.json();
}

export async function getSchedule(): Promise<ScheduleResponse> {
  const res = await fetch(`${API_BASE}/api/schedule`);
  if (!res.ok) throw new Error(`Failed to load schedule: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Add tests to `frontend/lib/api.test.ts`**

In the existing `frontend/lib/api.test.ts`, append:

```typescript
describe("getSettings", () => {
  it("returns parsed settings from /api/settings", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        slack_webhook_url: "https://hooks.slack.com/X",
        teams_webhook_url: "",
        email_enabled: false,
        email_smtp_host: "",
        email_smtp_port: 587,
        email_smtp_user: "",
        email_smtp_password: "",
        email_from: "",
        email_to: [],
      }),
    } as Response);
    const settings = await getSettings();
    expect(settings.slack_webhook_url).toBe("https://hooks.slack.com/X");
  });
});

describe("updateSettings", () => {
  it("sends PUT with partial payload and returns updated settings", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ slack_webhook_url: "new-url", email_enabled: true }),
    } as Response);
    const result = await updateSettings({ slack_webhook_url: "new-url" });
    expect(result.slack_webhook_url).toBe("new-url");
    const [url, opts] = (fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/api/settings");
    expect(opts.method).toBe("PUT");
  });
});

describe("getSchedule", () => {
  it("returns job list from /api/schedule", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ jobs: [{ id: "poll_calendar", name: "Poll", next_run: null }] }),
    } as Response);
    const schedule = await getSchedule();
    expect(schedule.jobs).toHaveLength(1);
    expect(schedule.jobs[0].id).toBe("poll_calendar");
  });
});
```

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -20
```
Expected: all pass (including new 3 cases)

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat(phase9): add getSettings/updateSettings/getSchedule API helpers"
```

---

## Task 6: Settings Dashboard — Component

**Files:**
- Create: `frontend/components/NotificationSettingsForm.tsx`
- Create: `frontend/components/NotificationSettingsForm.test.tsx`

- [ ] **Step 1: Write failing component tests**

```typescript
// frontend/components/NotificationSettingsForm.test.tsx
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NotificationSettingsForm } from "./NotificationSettingsForm";
import { NotificationSettings } from "../lib/api";

const defaults: NotificationSettings = {
  slack_webhook_url: "",
  teams_webhook_url: "",
  email_enabled: false,
  email_smtp_host: "",
  email_smtp_port: 587,
  email_smtp_user: "",
  email_smtp_password: "",
  email_from: "",
  email_to: [],
};

it("renders Slack webhook input", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={jest.fn()} saving={false} />);
  expect(screen.getByLabelText(/slack webhook/i)).toBeInTheDocument();
});

it("renders Teams webhook input", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={jest.fn()} saving={false} />);
  expect(screen.getByLabelText(/teams webhook/i)).toBeInTheDocument();
});

it("toggles email fields when email enabled checkbox is checked", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={jest.fn()} saving={false} />);
  const toggle = screen.getByLabelText(/enable email/i);
  fireEvent.click(toggle);
  expect(screen.getByLabelText(/smtp host/i)).toBeInTheDocument();
});

it("calls onSave with current form values on submit", async () => {
  const onSave = jest.fn();
  render(<NotificationSettingsForm settings={defaults} onSave={onSave} saving={false} />);
  fireEvent.change(screen.getByLabelText(/slack webhook/i), {
    target: { value: "https://hooks.slack.com/T999" },
  });
  fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(onSave).toHaveBeenCalledWith(
    expect.objectContaining({ slack_webhook_url: "https://hooks.slack.com/T999" })
  ));
});

it("shows saving state on button when saving=true", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={jest.fn()} saving={true} />);
  expect(screen.getByRole("button", { name: /saving/i })).toBeDisabled();
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend && npm test -- --watchAll=false --testPathPattern="NotificationSettingsForm" 2>&1 | tail -20
```

- [ ] **Step 3: Implement `frontend/components/NotificationSettingsForm.tsx`**

```tsx
"use client";

import React, { useState } from "react";
import { NotificationSettings } from "../lib/api";

interface Props {
  settings: NotificationSettings;
  onSave: (settings: NotificationSettings) => void;
  saving: boolean;
}

export function NotificationSettingsForm({ settings, onSave, saving }: Props) {
  const [form, setForm] = useState<NotificationSettings>(settings);

  const set = (key: keyof NotificationSettings, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} aria-label="notification settings">
      <section style={{ marginBottom: "2rem" }}>
        <h3>Slack</h3>
        <label htmlFor="slack_webhook_url">Slack Webhook URL</label>
        <input
          id="slack_webhook_url"
          type="url"
          placeholder="https://hooks.slack.com/services/..."
          value={form.slack_webhook_url}
          onChange={(e) => set("slack_webhook_url", e.target.value)}
          style={{ width: "100%", marginTop: "0.25rem" }}
        />
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>Microsoft Teams</h3>
        <label htmlFor="teams_webhook_url">Teams Webhook URL</label>
        <input
          id="teams_webhook_url"
          type="url"
          placeholder="https://outlook.office.com/webhook/..."
          value={form.teams_webhook_url}
          onChange={(e) => set("teams_webhook_url", e.target.value)}
          style={{ width: "100%", marginTop: "0.25rem" }}
        />
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>Email</h3>
        <label>
          <input
            id="email_enabled"
            type="checkbox"
            checked={form.email_enabled}
            onChange={(e) => set("email_enabled", e.target.checked)}
          />{" "}
          Enable Email notifications
        </label>

        {form.email_enabled && (
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.75rem" }}>
            <div>
              <label htmlFor="email_smtp_host">SMTP Host</label>
              <input
                id="email_smtp_host"
                type="text"
                value={form.email_smtp_host}
                onChange={(e) => set("email_smtp_host", e.target.value)}
                style={{ width: "100%", marginTop: "0.25rem" }}
              />
            </div>
            <div>
              <label htmlFor="email_from">From Address</label>
              <input
                id="email_from"
                type="email"
                value={form.email_from}
                onChange={(e) => set("email_from", e.target.value)}
                style={{ width: "100%", marginTop: "0.25rem" }}
              />
            </div>
            <div>
              <label htmlFor="email_to">To Addresses (comma-separated)</label>
              <input
                id="email_to"
                type="text"
                value={form.email_to.join(", ")}
                onChange={(e) =>
                  set("email_to", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
                }
                style={{ width: "100%", marginTop: "0.25rem" }}
              />
            </div>
          </div>
        )}
      </section>

      <button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save Settings"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd frontend && npm test -- --watchAll=false --testPathPattern="NotificationSettingsForm" 2>&1 | tail -20
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/components/NotificationSettingsForm.tsx frontend/components/NotificationSettingsForm.test.tsx
git commit -m "feat(phase9): add NotificationSettingsForm component"
```

---

## Task 7: Settings Dashboard — Page

**Files:**
- Create: `frontend/app/settings/page.tsx`
- Create: `frontend/app/settings/page.test.tsx`
- Modify: `frontend/components/AppHeader.tsx`

- [ ] **Step 1: Write failing page tests**

```typescript
// frontend/app/settings/page.test.tsx
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import SettingsPage from "./page";
import * as api from "../../lib/api";

jest.mock("../../lib/api");

const mockSettings: api.NotificationSettings = {
  slack_webhook_url: "",
  teams_webhook_url: "",
  email_enabled: false,
  email_smtp_host: "",
  email_smtp_port: 587,
  email_smtp_user: "",
  email_smtp_password: "",
  email_from: "",
  email_to: [],
};

beforeEach(() => {
  (api.getSettings as jest.Mock).mockResolvedValue(mockSettings);
  (api.updateSettings as jest.Mock).mockResolvedValue(mockSettings);
  (api.getSchedule as jest.Mock).mockResolvedValue({ jobs: [] });
});

it("renders page heading", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/notification settings/i)).toBeInTheDocument());
});

it("renders schedule section", async () => {
  (api.getSchedule as jest.Mock).mockResolvedValue({
    jobs: [{ id: "poll_calendar", name: "Poll Google Calendar", next_run: "2026-05-08T10:00:00Z" }],
  });
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/poll google calendar/i)).toBeInTheDocument());
});

it("shows no scheduled jobs message when list is empty", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/no scheduled jobs/i)).toBeInTheDocument());
});
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd frontend && npm test -- --watchAll=false --testPathPattern="settings/page" 2>&1 | tail -20
```

- [ ] **Step 3: Implement `frontend/app/settings/page.tsx`**

```tsx
"use client";

import React, { useEffect, useState } from "react";
import {
  getSettings,
  updateSettings,
  getSchedule,
  NotificationSettings,
  ScheduledJob,
} from "../../lib/api";
import { NotificationSettingsForm } from "../../components/NotificationSettingsForm";

export default function SettingsPage() {
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings().then(setSettings).catch((e) => setError(e.message));
    getSchedule().then((r) => setJobs(r.jobs)).catch(() => {});
  }, []);

  const handleSave = async (updated: NotificationSettings) => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const result = await updateSettings(updated);
      setSettings(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Notification Settings</h1>
      <p style={{ color: "#888", fontSize: "0.875rem" }}>
        ⚠️ Prototype — configuration is stored in{" "}
        <code>config/notification_settings.json</code>.
      </p>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", padding: "0.75rem", borderRadius: 6, marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {saved && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac", padding: "0.75rem", borderRadius: 6, marginBottom: "1rem" }}>
          Settings saved.
        </div>
      )}

      {settings ? (
        <NotificationSettingsForm settings={settings} onSave={handleSave} saving={saving} />
      ) : (
        !error && <p>Loading…</p>
      )}

      <hr style={{ margin: "2rem 0" }} />

      <h2>Scheduled Jobs</h2>
      {jobs.length === 0 ? (
        <p style={{ color: "#888" }}>No scheduled jobs currently queued.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid #e5e7eb" }}>Job</th>
              <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid #e5e7eb" }}>Next Run</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td style={{ padding: "0.5rem" }}>{job.name}</td>
                <td style={{ padding: "0.5rem", color: "#888" }}>
                  {job.next_run ? new Date(job.next_run).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Add Settings link to `AppHeader.tsx`**

Open `frontend/components/AppHeader.tsx`. Add a `<a href="/settings">Settings</a>` or `<Link href="/settings">Settings</Link>` alongside the existing nav links. Match the exact pattern already used in that file (check whether it uses `<Link>` from `next/link` or plain `<a>`).

- [ ] **Step 5: Run frontend tests**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -30
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add frontend/app/settings/ frontend/components/AppHeader.tsx
git commit -m "feat(phase9): add /settings dashboard page with schedule viewer"
```

---

## Task 8: Final Integration Smoke Test & Notes

- [ ] **Step 1: Run full backend suite**

```bash
.venv/bin/pytest tests/ -q
```
Expected: 270+ tests, 0 failures

- [ ] **Step 2: Run full frontend suite**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -10
```
Expected: 59+ tests, 0 failures

- [ ] **Step 3: Manual smoke test (optional)**

Start the API and frontend:
```bash
# Terminal 1
source .venv/bin/activate && uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend && npm run dev
```
Navigate to `http://localhost:3000/settings`. Verify:
- Settings form renders with empty defaults.
- Saving Slack webhook URL shows "Settings saved." toast.
- Scheduled Jobs table renders (at minimum the `poll_calendar` polling job).

- [ ] **Step 4: Add prototype note to Apple Notes**

> **PROTOTYPE NOTE — Phase 9 (captured 2026-05-07)**
> Calendar & Notification Automation is intentionally generic:
> - Calendar uses mock JSON fallback in `src/calendar_trigger.py` when no OAuth credentials present.
> - Delivery channels (Slack/Teams/email) are real HTTP calls but fire-and-forget — no retry, no queue.
> - Settings persist to `config/notification_settings.json` (file-backed, not a database).
> - Frontend `/settings` page has no auth, no multi-user support.
> To productionise: replace `SettingsStore` with DB-backed store, add retry/dead-letter queue in `delivery.py`, wire real Google/Outlook Calendar OAuth, add auth to `/settings`.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(phase9): complete Calendar & Notification Automation prototype"
```
