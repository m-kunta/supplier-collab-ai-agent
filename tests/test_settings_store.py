import json
import pytest
from pathlib import Path
from src.settings_store import SettingsStore
from src.delivery import NotificationSettings


@pytest.fixture
def store(tmp_path):
    return SettingsStore(settings_path=tmp_path / "notification_settings.json")


def test_load_returns_defaults_when_file_missing(store):
    settings = store.load()
    assert isinstance(settings, NotificationSettings)
    assert settings.slack_webhook_url == ""
    assert settings.email_enabled is False


def test_save_and_reload(store):
    original = store.load()
    original.slack_webhook_url = "https://hooks.slack.com/T123"
    store.save(original)
    reloaded = store.load()
    assert reloaded.slack_webhook_url == "https://hooks.slack.com/T123"


def test_save_writes_valid_json(store):
    settings = store.load()
    settings.email_enabled = True
    settings.email_to = ["a@b.com"]
    store.save(settings)
    raw = json.loads(store.settings_path.read_text())
    assert raw["email_enabled"] is True
    assert raw["email_to"] == ["a@b.com"]


def test_update_partial(store):
    store.save(store.load())  # write defaults
    store.update({"slack_webhook_url": "https://x.com"})
    assert store.load().slack_webhook_url == "https://x.com"


def test_update_ignores_unknown_keys(store):
    store.update({"nonexistent_key": "value"})
    settings = store.load()
    assert not hasattr(settings, "nonexistent_key")
