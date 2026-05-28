import json

from src.delivery import NotificationSettings
from src.sqlite_settings_store import SQLiteSettingsStore


def make_store(tmp_path):
    return SQLiteSettingsStore(db_path=tmp_path / "supplier_collab.db")


def test_load_returns_defaults_when_row_missing(tmp_path):
    store = make_store(tmp_path)

    settings = store.load()

    assert isinstance(settings, NotificationSettings)
    assert settings.slack_webhook_url == ""
    assert settings.email_enabled is False


def test_save_and_reload_survives_new_store_instance(tmp_path):
    store = make_store(tmp_path)
    settings = NotificationSettings(
        slack_webhook_url="https://hooks.slack.com/T123",
        email_enabled=True,
        email_to=["buyer@example.com"],
    )

    store.save(settings)
    reloaded = make_store(tmp_path).load()

    assert reloaded.slack_webhook_url == "https://hooks.slack.com/T123"
    assert reloaded.email_enabled is True
    assert reloaded.email_to == ["buyer@example.com"]


def test_save_stores_valid_json_payload(tmp_path):
    store = make_store(tmp_path)
    store.save(NotificationSettings(email_enabled=True, email_to=["a@b.com"]))

    with store._connect() as conn:
        row = conn.execute(
            "SELECT payload_json FROM notification_settings WHERE id = ?",
            ("default",),
        ).fetchone()

    payload = json.loads(row["payload_json"])
    assert payload["email_enabled"] is True
    assert payload["email_to"] == ["a@b.com"]


def test_update_partial_ignores_unknown_keys(tmp_path):
    store = make_store(tmp_path)

    updated = store.update({
        "slack_webhook_url": "https://x.com",
        "nonexistent_key": "ignored",
    })

    assert updated.slack_webhook_url == "https://x.com"
    assert not hasattr(updated, "nonexistent_key")
    assert make_store(tmp_path).load().slack_webhook_url == "https://x.com"
