import pytest

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

    with pytest.raises(ValueError, match="Unsupported SUPPLIER_COLLAB_STORE_BACKEND"):
        create_settings_store()
