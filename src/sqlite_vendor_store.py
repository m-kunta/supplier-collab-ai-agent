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
