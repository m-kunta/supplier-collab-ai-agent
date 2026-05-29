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
