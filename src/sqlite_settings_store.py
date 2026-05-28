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
