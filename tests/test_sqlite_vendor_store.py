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
