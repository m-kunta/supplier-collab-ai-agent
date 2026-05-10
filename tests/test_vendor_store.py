import pytest
from src.vendor_store import VendorStore, VendorRecord


def make_store(tmp_path):
    """Return a VendorStore backed by an isolated temp file."""
    return VendorStore(path=str(tmp_path / "vendors.json"))


def make_record(**overrides):
    base = dict(vendor_id="VEN001", vendor_name="Northstar Foods Co",
                category="Grocery", tier="Tier 1")
    return VendorRecord(**{**base, **overrides})


# ---------------------------------------------------------------------------
# list_vendors
# ---------------------------------------------------------------------------

def test_list_vendors_empty_on_init(tmp_path):
    store = make_store(tmp_path)
    assert store.list_vendors() == []


def test_list_vendors_returns_all(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record(vendor_id="VEN001"))
    store.add_vendor(make_record(vendor_id="VEN002", vendor_name="Apex Supply"))
    vendors = store.list_vendors()
    assert len(vendors) == 2
    ids = {v["vendor_id"] for v in vendors}
    assert ids == {"VEN001", "VEN002"}


# ---------------------------------------------------------------------------
# add_vendor
# ---------------------------------------------------------------------------

def test_add_vendor_persists(tmp_path):
    store = make_store(tmp_path)
    rec = store.add_vendor(make_record())
    assert rec["vendor_id"] == "VEN001"
    assert rec["status"] == "pending_data"
    # Reload from disk to confirm persistence
    store2 = make_store(tmp_path)
    assert len(store2.list_vendors()) == 1


def test_add_vendor_generates_id_and_timestamp(tmp_path):
    store = make_store(tmp_path)
    rec = store.add_vendor(make_record())
    assert rec["id"] and len(rec["id"]) == 36  # UUID4 format
    assert rec["created_at"].endswith("Z")


def test_add_vendor_raises_on_duplicate_vendor_id(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())
    with pytest.raises(ValueError, match="already exists"):
        store.add_vendor(make_record())


# ---------------------------------------------------------------------------
# get_vendor
# ---------------------------------------------------------------------------

def test_get_vendor_by_vendor_id(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())
    found = store.get_vendor("VEN001")
    assert found is not None
    assert found["vendor_name"] == "Northstar Foods Co"


def test_get_vendor_by_uuid(tmp_path):
    store = make_store(tmp_path)
    rec = store.add_vendor(make_record())
    found = store.get_vendor(rec["id"])
    assert found is not None
    assert found["vendor_id"] == "VEN001"


def test_get_vendor_returns_none_for_unknown(tmp_path):
    store = make_store(tmp_path)
    assert store.get_vendor("DOES_NOT_EXIST") is None


# ---------------------------------------------------------------------------
# update_vendor_status
# ---------------------------------------------------------------------------

def test_update_vendor_status_changes_field(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())
    updated = store.update_vendor_status("VEN001", "active")
    assert updated["status"] == "active"


def test_update_vendor_status_persists(tmp_path):
    store = make_store(tmp_path)
    store.add_vendor(make_record())
    store.update_vendor_status("VEN001", "active")
    store2 = make_store(tmp_path)
    vendor = store2.get_vendor("VEN001")
    assert vendor["status"] == "active"


def test_update_vendor_status_raises_for_unknown(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        store.update_vendor_status("GHOST_ID", "active")
