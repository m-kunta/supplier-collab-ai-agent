"""Tests for Phase 9 vendor onboarding API routes:
  GET  /api/vendors/registered
  POST /api/vendors
  GET  /api/vendors/{vendor_id}/onboarding-pack
"""
import io
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

SAMPLE_VENDOR_PAYLOAD = {
    "vendor_id": "VEN_TEST",
    "vendor_name": "Test Supplier Inc",
    "category": "Grocery",
    "tier": "Tier 1",
}

SAMPLE_VENDOR_RECORD = {
    "id": "uuid-abc-123",
    "vendor_id": "VEN_TEST",
    "vendor_name": "Test Supplier Inc",
    "category": "Grocery",
    "tier": "Tier 1",
    "status": "pending_data",
    "created_at": "2026-05-09T00:00:00Z",
}


# ---------------------------------------------------------------------------
# GET /api/vendors/registered
# ---------------------------------------------------------------------------

def test_list_registered_vendors_returns_empty():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.list_vendors.return_value = []
        resp = client.get("/api/vendors/registered")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendors"] == []
    assert data["total"] == 0


def test_list_registered_vendors_returns_all():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.list_vendors.return_value = [SAMPLE_VENDOR_RECORD]
        resp = client.get("/api/vendors/registered")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["vendors"][0]["vendor_id"] == "VEN_TEST"


# ---------------------------------------------------------------------------
# POST /api/vendors
# ---------------------------------------------------------------------------

def test_register_vendor_success():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.add_vendor.return_value = SAMPLE_VENDOR_RECORD
        resp = client.post("/api/vendors", json=SAMPLE_VENDOR_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendor_id"] == "VEN_TEST"
    assert data["status"] == "pending_data"


def test_register_vendor_duplicate_returns_409():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.add_vendor.side_effect = ValueError("Vendor with ID VEN_TEST already exists.")
        resp = client.post("/api/vendors", json=SAMPLE_VENDOR_PAYLOAD)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_register_vendor_invalid_payload_returns_400():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.add_vendor.side_effect = Exception("Unexpected error")
        resp = client.post("/api/vendors", json=SAMPLE_VENDOR_PAYLOAD)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/onboarding-pack
# ---------------------------------------------------------------------------

def test_onboarding_pack_returns_zip():
    fake_zip = io.BytesIO()
    with zipfile.ZipFile(fake_zip, "w") as zf:
        zf.writestr("instructions.md", "# Test")
    fake_zip.seek(0)

    with patch("api.main.vendor_store") as mock_store, \
         patch("api.main.generate_onboarding_pack", return_value=fake_zip):
        mock_store.get_vendor.return_value = SAMPLE_VENDOR_RECORD
        resp = client.get("/api/vendors/VEN_TEST/onboarding-pack")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/x-zip-compressed"
    assert "VEN_TEST_onboarding_pack.zip" in resp.headers["content-disposition"]


def test_onboarding_pack_returns_404_for_unknown_vendor():
    with patch("api.main.vendor_store") as mock_store:
        mock_store.get_vendor.return_value = None
        resp = client.get("/api/vendors/GHOST/onboarding-pack")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
