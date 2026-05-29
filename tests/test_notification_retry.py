from src.delivery import DeliveryResult, NotificationSettings
from src.delivery_attempt_store import DeliveryAttemptStore
from src.notification_retry import NotificationRetryService


class FakeDispatcher:
    def __init__(self, results_by_channel):
        self.results_by_channel = {
            channel: list(results)
            for channel, results in results_by_channel.items()
        }
        self.calls = []

    def dispatch_channel(self, channel, briefing):
        self.calls.append(channel)
        return self.results_by_channel[channel].pop(0)


def make_briefing():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-29",
        "briefing_id": "brief-123",
        "briefing_text": "Ready",
    }


def test_successful_channel_records_one_sent_attempt(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "slack": [DeliveryResult("slack", True)],
    })
    service = NotificationRetryService(
        NotificationSettings(slack_webhook_url="https://hooks.slack.com/fake"),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("slack", True)]
    assert dispatcher.calls == ["slack"]
    rows = store.list_attempts("brief-123")
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["attempt_count"] == 1


def test_failed_channel_retries_until_success(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "slack": [
            DeliveryResult("slack", False, "timeout"),
            DeliveryResult("slack", True),
        ],
    })
    service = NotificationRetryService(
        NotificationSettings(slack_webhook_url="https://hooks.slack.com/fake"),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
        max_attempts=3,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("slack", True)]
    assert dispatcher.calls == ["slack", "slack"]
    rows = store.list_attempts("brief-123")
    assert [row["status"] for row in rows] == ["failed", "sent"]
    assert rows[0]["last_error"] == "timeout"
    assert rows[1]["attempt_count"] == 2


def test_exhausted_channel_records_dead_letter(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({
        "email": [
            DeliveryResult("email", False, "smtp down"),
            DeliveryResult("email", False, "smtp down"),
        ],
    })
    service = NotificationRetryService(
        NotificationSettings(
            email_enabled=True,
            email_smtp_host="smtp.example.com",
            email_from="from@example.com",
            email_to=["buyer@example.com"],
        ),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
        max_attempts=2,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == [DeliveryResult("email", False, "smtp down")]
    rows = store.list_attempts("brief-123")
    assert [row["status"] for row in rows] == ["failed", "dead_letter"]
    assert rows[-1]["attempt_count"] == 2
    assert rows[-1]["last_error"] == "smtp down"


def test_no_configured_channels_returns_empty_and_records_nothing(tmp_path):
    store = DeliveryAttemptStore(tmp_path / "state.db")
    dispatcher = FakeDispatcher({})
    service = NotificationRetryService(
        NotificationSettings(),
        attempt_store=store,
        dispatcher_factory=lambda settings: dispatcher,
    )

    results = service.dispatch_with_retries(make_briefing())

    assert results == []
    assert store.list_attempts() == []
