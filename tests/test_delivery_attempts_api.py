from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app

client = TestClient(app)


def make_attempt(**overrides):
    base = {
        "id": "attempt-1",
        "briefing_id": "brief-123",
        "channel": "slack",
        "status": "dead_letter",
        "attempt_count": 3,
        "payload": {"vendor": "Northstar Foods Co"},
        "last_error": "timeout",
        "created_at": "2026-05-29T00:00:00Z",
        "updated_at": "2026-05-29T00:01:00Z",
    }
    return {**base, **overrides}


def test_get_deliveries_returns_attempts_and_total():
    with patch("api.main.delivery_attempt_store") as mock_store:
        mock_store.list_attempts.return_value = [make_attempt()]

        resp = client.get("/api/deliveries")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["attempts"][0]["status"] == "dead_letter"
    assert data["attempts"][0]["payload"]["vendor"] == "Northstar Foods Co"
    mock_store.list_attempts.assert_called_once_with(briefing_id=None)


def test_get_deliveries_filters_by_briefing_id_and_limit():
    attempts = [
        make_attempt(id="attempt-1", attempt_count=1),
        make_attempt(id="attempt-2", attempt_count=2),
    ]
    with patch("api.main.delivery_attempt_store") as mock_store:
        mock_store.list_attempts.return_value = attempts

        resp = client.get("/api/deliveries?briefing_id=brief-123&limit=1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert [row["id"] for row in data["attempts"]] == ["attempt-1"]
    mock_store.list_attempts.assert_called_once_with(briefing_id="brief-123")
