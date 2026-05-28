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
