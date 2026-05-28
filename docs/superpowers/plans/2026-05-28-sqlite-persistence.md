# SQLite Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SQLite-backed persistence for notification settings and registered vendors while preserving existing API behavior.

**Architecture:** Keep current JSON stores intact for backwards compatibility, add SQLite-backed implementations with the same public methods, and introduce a factory that selects `json` or `sqlite` via environment variables. API and scheduler code should use the factory so persistence backend selection is centralized.

**Tech Stack:** Python standard library `sqlite3`, Pydantic v2 models, pytest, FastAPI existing route tests.

---

## Files

- Create: `src/store_factory.py` — selects settings/vendor stores from environment variables.
- Create: `src/sqlite_settings_store.py` — SQLite implementation of notification settings persistence.
- Create: `src/sqlite_vendor_store.py` — SQLite implementation of vendor onboarding persistence.
- Create: `tests/test_sqlite_settings_store.py` — tests SQLite settings behavior.
- Create: `tests/test_sqlite_vendor_store.py` — tests SQLite vendor behavior.
- Create: `tests/test_store_factory.py` — tests backend selection.
- Modify: `api/main.py` — use store factory instead of direct JSON-store construction.
- Modify: `src/scheduler.py` — use store factory for settings loads.
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`, `TODO.md`, `docs/implementation_plan.md` — document Phase 10 persistence status.

---

## Task 1: SQLite Settings Store

**Files:**
- Create: `tests/test_sqlite_settings_store.py`
- Create: `src/sqlite_settings_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sqlite_settings_store.py`:

```python
import json

from src.delivery import NotificationSettings
from src.sqlite_settings_store import SQLiteSettingsStore


def make_store(tmp_path):
    return SQLiteSettingsStore(db_path=tmp_path / "supplier_collab.db")


def test_load_returns_defaults_when_row_missing(tmp_path):
    store = make_store(tmp_path)

    settings = store.load()

    assert isinstance(settings, NotificationSettings)
    assert settings.slack_webhook_url == ""
    assert settings.email_enabled is False


def test_save_and_reload_survives_new_store_instance(tmp_path):
    store = make_store(tmp_path)
    settings = NotificationSettings(
        slack_webhook_url="https://hooks.slack.com/T123",
        email_enabled=True,
        email_to=["buyer@example.com"],
    )

    store.save(settings)
    reloaded = make_store(tmp_path).load()

    assert reloaded.slack_webhook_url == "https://hooks.slack.com/T123"
    assert reloaded.email_enabled is True
    assert reloaded.email_to == ["buyer@example.com"]


def test_save_stores_valid_json_payload(tmp_path):
    store = make_store(tmp_path)
    store.save(NotificationSettings(email_enabled=True, email_to=["a@b.com"]))

    with store._connect() as conn:
        row = conn.execute(
            "SELECT payload_json FROM notification_settings WHERE id = ?",
            ("default",),
        ).fetchone()

    payload = json.loads(row["payload_json"])
    assert payload["email_enabled"] is True
    assert payload["email_to"] == ["a@b.com"]


def test_update_partial_ignores_unknown_keys(tmp_path):
    store = make_store(tmp_path)

    updated = store.update({
        "slack_webhook_url": "https://x.com",
        "nonexistent_key": "ignored",
    })

    assert updated.slack_webhook_url == "https://x.com"
    assert not hasattr(updated, "nonexistent_key")
    assert make_store(tmp_path).load().slack_webhook_url == "https://x.com"
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_sqlite_settings_store.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.sqlite_settings_store'`.

- [ ] **Step 3: Implement SQLite settings store**

Create `src/sqlite_settings_store.py`:

```python
"""SQLite-backed notification settings store."""
from __future__ import annotations

import datetime
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from src.delivery import NotificationSettings

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")
_SETTINGS_ID = "default"


class SQLiteSettingsStore:
    def __init__(self, db_path: Path | str = _DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
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
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def load(self) -> NotificationSettings:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM notification_settings WHERE id = ?",
                (_SETTINGS_ID,),
            ).fetchone()
            if row is None:
                return NotificationSettings()
            raw = json.loads(row["payload_json"])
            valid_keys = set(NotificationSettings.model_fields)
            return NotificationSettings(**{k: v for k, v in raw.items() if k in valid_keys})

    def save(self, settings: NotificationSettings) -> None:
        payload_json = settings.model_dump_json(indent=2)
        updated_at = datetime.datetime.utcnow().isoformat() + "Z"
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notification_settings (id, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (_SETTINGS_ID, payload_json, updated_at),
            )

    def update(self, partial: dict[str, Any]) -> NotificationSettings:
        current = self.load()
        valid_keys = set(NotificationSettings.model_fields)
        for key, value in partial.items():
            if key in valid_keys:
                setattr(current, key, value)
        self.save(current)
        return current
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
.venv/bin/pytest tests/test_sqlite_settings_store.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/sqlite_settings_store.py tests/test_sqlite_settings_store.py
git commit -m "feat(persistence): add SQLite settings store"
```

---

## Task 2: SQLite Vendor Store

**Files:**
- Create: `tests/test_sqlite_vendor_store.py`
- Create: `src/sqlite_vendor_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sqlite_vendor_store.py`:

```python
import pytest

from src.sqlite_vendor_store import SQLiteVendorStore
from src.vendor_store import VendorRecord


def make_store(tmp_path):
    return SQLiteVendorStore(db_path=tmp_path / "supplier_collab.db")


def make_record(**overrides):
    base = {
        "vendor_id": "VEN001",
        "vendor_name": "Northstar Foods Co",
        "category": "Grocery",
        "tier": "Tier 1",
    }
    return VendorRecord(**{**base, **overrides})


def test_list_vendors_empty_on_init(tmp_path):
    store = make_store(tmp_path)

    assert store.list_vendors() == []


def test_add_vendor_persists_across_store_instances(tmp_path):
    store = make_store(tmp_path)

    saved = store.add_vendor(make_record())
    reloaded = make_store(tmp_path).get_vendor("VEN001")

    assert saved["vendor_id"] == "VEN001"
    assert saved["status"] == "pending_data"
    assert reloaded["vendor_name"] == "Northstar Foods Co"


def test_list_vendors_returns_all_in_insert_order(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record(vendor_id="VEN001"))
    store.add_vendor(make_record(vendor_id="VEN002", vendor_name="Apex Supply"))

    vendors = store.list_vendors()

    assert [v["vendor_id"] for v in vendors] == ["VEN001", "VEN002"]


def test_get_vendor_by_uuid_and_vendor_id(tmp_path):
    store = make_store(tmp_path)
    saved = store.add_vendor(make_record())

    assert store.get_vendor("VEN001")["id"] == saved["id"]
    assert store.get_vendor(saved["id"])["vendor_id"] == "VEN001"


def test_get_vendor_returns_none_for_unknown(tmp_path):
    store = make_store(tmp_path)

    assert store.get_vendor("GHOST") is None


def test_add_vendor_rejects_duplicate_vendor_id(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())

    with pytest.raises(ValueError, match="already exists"):
        store.add_vendor(make_record())


def test_update_vendor_status_persists(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())

    updated = store.update_vendor_status("VEN001", "active")
    reloaded = make_store(tmp_path).get_vendor("VEN001")

    assert updated["status"] == "active"
    assert reloaded["status"] == "active"


def test_update_vendor_status_raises_for_unknown(tmp_path):
    store = make_store(tmp_path)

    with pytest.raises(ValueError, match="not found"):
        store.update_vendor_status("GHOST", "active")
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_sqlite_vendor_store.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.sqlite_vendor_store'`.

- [ ] **Step 3: Implement SQLite vendor store**

Create `src/sqlite_vendor_store.py`:

```python
"""SQLite-backed vendor onboarding store."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from src.vendor_store import VendorRecord

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")


class SQLiteVendorStore:
    def __init__(self, db_path: Path | str = _DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
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
                CREATE TABLE IF NOT EXISTS vendors (
                    id TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL UNIQUE,
                    vendor_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "vendor_id": row["vendor_id"],
            "vendor_name": row["vendor_name"],
            "category": row["category"],
            "tier": row["tier"],
            "status": row["status"],
            "created_at": row["created_at"],
        }

    def list_vendors(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, vendor_id, vendor_name, category, tier, status, created_at
                FROM vendors
                ORDER BY created_at ASC, vendor_id ASC
                """
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_vendor(self, id_or_vendor_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, vendor_id, vendor_name, category, tier, status, created_at
                FROM vendors
                WHERE id = ? OR vendor_id = ?
                """,
                (id_or_vendor_id, id_or_vendor_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def add_vendor(self, vendor: VendorRecord) -> dict[str, Any]:
        record = vendor.model_dump()
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO vendors (
                        id, vendor_id, vendor_name, category, tier, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["id"],
                        record["vendor_id"],
                        record["vendor_name"],
                        record["category"],
                        record["tier"],
                        record["status"],
                        record["created_at"],
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Vendor with ID {vendor.vendor_id} already exists.") from exc
        return record

    def update_vendor_status(self, vendor_id: str, new_status: str) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, vendor_id, vendor_name, category, tier, status, created_at
                FROM vendors
                WHERE id = ? OR vendor_id = ?
                """,
                (vendor_id, vendor_id),
            ).fetchone()
            if row is None:
                raise ValueError(f"Vendor {vendor_id} not found.")
            conn.execute(
                "UPDATE vendors SET status = ? WHERE id = ?",
                (new_status, row["id"]),
            )
            updated = conn.execute(
                """
                SELECT id, vendor_id, vendor_name, category, tier, status, created_at
                FROM vendors
                WHERE id = ?
                """,
                (row["id"],),
            ).fetchone()
        return self._row_to_dict(updated)
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
.venv/bin/pytest tests/test_sqlite_vendor_store.py -q
```

Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/sqlite_vendor_store.py tests/test_sqlite_vendor_store.py
git commit -m "feat(persistence): add SQLite vendor store"
```

---

## Task 3: Store Factory and Wiring

**Files:**
- Create: `tests/test_store_factory.py`
- Create: `src/store_factory.py`
- Modify: `api/main.py`
- Modify: `src/scheduler.py`

- [ ] **Step 1: Write failing factory tests**

Create `tests/test_store_factory.py`:

```python
from src.settings_store import SettingsStore
from src.sqlite_settings_store import SQLiteSettingsStore
from src.sqlite_vendor_store import SQLiteVendorStore
from src.store_factory import create_settings_store, create_vendor_store
from src.vendor_store import VendorStore


def test_create_settings_store_defaults_to_json(monkeypatch):
    monkeypatch.delenv("SUPPLIER_COLLAB_STORE_BACKEND", raising=False)

    store = create_settings_store()

    assert isinstance(store, SettingsStore)


def test_create_vendor_store_defaults_to_json(monkeypatch):
    monkeypatch.delenv("SUPPLIER_COLLAB_STORE_BACKEND", raising=False)

    store = create_vendor_store()

    assert isinstance(store, VendorStore)


def test_create_settings_store_uses_sqlite_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPPLIER_COLLAB_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("SUPPLIER_COLLAB_DB_PATH", str(tmp_path / "state.db"))

    store = create_settings_store()

    assert isinstance(store, SQLiteSettingsStore)


def test_create_vendor_store_uses_sqlite_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPPLIER_COLLAB_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("SUPPLIER_COLLAB_DB_PATH", str(tmp_path / "state.db"))

    store = create_vendor_store()

    assert isinstance(store, SQLiteVendorStore)


def test_unknown_backend_raises_clear_error(monkeypatch):
    monkeypatch.setenv("SUPPLIER_COLLAB_STORE_BACKEND", "redis")

    try:
        create_settings_store()
    except ValueError as exc:
        assert "Unsupported SUPPLIER_COLLAB_STORE_BACKEND" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
.venv/bin/pytest tests/test_store_factory.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.store_factory'`.

- [ ] **Step 3: Implement store factory**

Create `src/store_factory.py`:

```python
"""Persistence store factory.

Selects prototype JSON stores or SQLite stores from environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from src.settings_store import SettingsStore
from src.sqlite_settings_store import SQLiteSettingsStore
from src.sqlite_vendor_store import SQLiteVendorStore
from src.vendor_store import VendorStore

StoreBackend = Literal["json", "sqlite"]

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")


def _backend() -> StoreBackend:
    value = os.getenv("SUPPLIER_COLLAB_STORE_BACKEND", "json").strip().lower()
    if value in {"json", "sqlite"}:
        return value  # type: ignore[return-value]
    raise ValueError(
        "Unsupported SUPPLIER_COLLAB_STORE_BACKEND "
        f"'{value}'. Expected 'json' or 'sqlite'."
    )


def _db_path() -> Path:
    return Path(os.getenv("SUPPLIER_COLLAB_DB_PATH", str(_DEFAULT_DB_PATH)))


def create_settings_store():
    if _backend() == "sqlite":
        return SQLiteSettingsStore(db_path=_db_path())
    return SettingsStore()


def create_vendor_store():
    if _backend() == "sqlite":
        return SQLiteVendorStore(db_path=_db_path())
    return VendorStore()
```

- [ ] **Step 4: Wire API and scheduler**

In `api/main.py`, replace:

```python
from src.settings_store import SettingsStore
from src.vendor_store import VendorStore, VendorRecord
```

with:

```python
from src.store_factory import create_settings_store, create_vendor_store
from src.vendor_store import VendorRecord
```

Then replace:

```python
settings_store = SettingsStore()
vendor_store = VendorStore()
```

with:

```python
settings_store = create_settings_store()
vendor_store = create_vendor_store()
```

In `src/scheduler.py`, replace each local import/use of `SettingsStore`:

```python
from src.settings_store import SettingsStore
settings = SettingsStore().load()
```

with:

```python
from src.store_factory import create_settings_store
settings = create_settings_store().load()
```

- [ ] **Step 5: Run factory and existing API tests**

```bash
.venv/bin/pytest tests/test_store_factory.py tests/test_settings_api.py tests/test_vendor_api.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/store_factory.py api/main.py src/scheduler.py tests/test_store_factory.py
git commit -m "feat(persistence): select store backend from environment"
```

---

## Task 4: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `TODO.md`
- Modify: `docs/implementation_plan.md`

- [ ] **Step 1: Update docs**

Update the docs to state:

- Phase 10 has started with selectable JSON/SQLite persistence.
- Default local backend remains JSON for compatibility.
- SQLite can be enabled with:

```bash
SUPPLIER_COLLAB_STORE_BACKEND=sqlite
SUPPLIER_COLLAB_DB_PATH=config/supplier_collab.db
```

- SQLite covers notification settings and registered vendor onboarding records.

- [ ] **Step 2: Run backend tests**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test -- --no-cache
```

Expected: all frontend tests pass.

- [ ] **Step 4: Commit docs**

```bash
git add README.md AGENTS.md CLAUDE.md TODO.md docs/implementation_plan.md
git commit -m "docs(persistence): document SQLite store backend"
```

- [ ] **Step 5: Push**

```bash
git push origin master
```

Expected: branch pushed to GitHub.

---

## Self-Review

- Spec coverage: The plan covers SQLite settings, SQLite vendors, backend selection, API/scheduler wiring, tests, docs, and verification.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: Store methods match the existing JSON store contracts and the design spec.
