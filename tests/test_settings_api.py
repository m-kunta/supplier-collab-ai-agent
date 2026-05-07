import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)


def test_get_settings_returns_defaults():
    with patch("api.main.settings_store") as mock_store:
        from src.delivery import NotificationSettings
        mock_store.load.return_value = NotificationSettings()
        resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slack_webhook_url"] == ""
    assert data["email_enabled"] is False


def test_put_settings_updates_and_returns():
    with patch("api.main.settings_store") as mock_store:
        from src.delivery import NotificationSettings
        updated = NotificationSettings(slack_webhook_url="https://hooks.slack.com/X")
        mock_store.update.return_value = updated
        resp = client.put("/api/settings", json={"slack_webhook_url": "https://hooks.slack.com/X"})
    assert resp.status_code == 200
    assert resp.json()["slack_webhook_url"] == "https://hooks.slack.com/X"


def test_get_schedule_returns_list():
    resp = client.get("/api/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
