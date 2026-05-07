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
        self.settings_path = Path(settings_path)
        self._lock = threading.Lock()

    def load(self) -> NotificationSettings:
        with self._lock:
            if not self.settings_path.exists():
                return NotificationSettings()
            raw = json.loads(self.settings_path.read_text())
            valid_keys = set(NotificationSettings.model_fields)
            return NotificationSettings(**{k: v for k, v in raw.items() if k in valid_keys})

    def save(self, settings: NotificationSettings) -> None:
        with self._lock:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(settings.model_dump_json(indent=2))

    def update(self, partial: dict[str, Any]) -> NotificationSettings:
        current = self.load()
        valid_keys = set(NotificationSettings.model_fields)
        for k, v in partial.items():
            if k in valid_keys:
                setattr(current, k, v)
        self.save(current)
        return current
