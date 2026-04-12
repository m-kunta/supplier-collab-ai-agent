"""In-memory briefing record store (process-local; resets on server restart)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


class BriefingStore:
    """Thread-safe UUID-keyed store for completed ``summarize_request`` payloads.

    .. note::
        This store is **process-local** and resets on server restart.  Output files
        written to ``output/`` on disk persist across restarts, but ``GET
        /api/briefings/{id}`` will return 404 for any run from a previous process.
        Swap in a SQLite or Redis backend before exposing the download endpoint to
        end-users.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}

    def save(self, summary: dict[str, Any]) -> tuple[str, str]:
        """Persist a summary dict; returns ``(briefing_id, created_at_iso)``."""
        briefing_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        record = {
            "id": briefing_id,
            "created_at": created_at,
            "summary": summary,
        }
        with self._lock:
            self._records[briefing_id] = record
        return briefing_id, created_at

    def get(self, briefing_id: str) -> Optional[dict[str, Any]]:
        """Return the full stored record (``id``, ``created_at``, ``summary``) or ``None``."""
        with self._lock:
            rec = self._records.get(briefing_id)
            return dict(rec) if rec else None

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        """Drop all records (intended for tests)."""
        with self._lock:
            self._records.clear()

    def list_briefs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Newest first; each item is a shallow summary row for history UIs."""
        with self._lock:
            records = list(self._records.values())
        records.sort(key=lambda r: r["created_at"], reverse=True)
        rows: list[dict[str, Any]] = []
        for rec in records[: max(0, limit)]:
            summary = rec["summary"]
            req = summary.get("request") or {}
            rows.append(
                {
                    "id": rec["id"],
                    "created_at": rec["created_at"],
                    "status": summary.get("status"),
                    "vendor_id": summary.get("vendor_id"),
                    "vendor": req.get("vendor"),
                    "meeting_date": req.get("meeting_date"),
                }
            )
        return rows
