import pytest
from unittest.mock import patch, MagicMock
from src.delivery import NotificationDispatcher, NotificationSettings, DeliveryResult


def make_settings(**overrides):
    base = {
        "slack_webhook_url": "",
        "teams_webhook_url": "",
        "email_enabled": False,
        "email_smtp_host": "",
        "email_smtp_port": 587,
        "email_smtp_user": "",
        "email_smtp_password": "",
        "email_from": "",
        "email_to": [],
    }
    return NotificationSettings(**{**base, **overrides})


def make_briefing():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-08",
        "briefing_id": "abc-123",
        "briefing_text": "Executive summary...",
        "output_files": {"docx_path": "/tmp/briefing.docx"},
    }


def test_dispatcher_no_channels_enabled():
    dispatcher = NotificationDispatcher(make_settings())
    results = dispatcher.dispatch(make_briefing())
    assert results == []


def test_slack_channel_sends_post():
    settings = make_settings(slack_webhook_url="https://hooks.slack.com/fake")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 1
    assert results[0].channel == "slack"
    assert results[0].success is True
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert "Northstar Foods Co" in payload["text"]


def test_teams_channel_sends_post():
    settings = make_settings(teams_webhook_url="https://teams.webhook.fake/url")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 1
    assert results[0].channel == "teams"
    assert results[0].success is True


def test_slack_channel_handles_http_error():
    settings = make_settings(slack_webhook_url="https://hooks.slack.com/fake")
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post", side_effect=Exception("timeout")):
        results = dispatcher.dispatch(make_briefing())
    assert results[0].success is False
    assert "timeout" in results[0].error


def test_email_channel_sends_when_enabled():
    settings = make_settings(
        email_enabled=True,
        email_smtp_host="smtp.example.com",
        email_from="from@example.com",
        email_to=["buyer@example.com"],
    )
    dispatcher = NotificationDispatcher(settings)
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        results = dispatcher.dispatch(make_briefing())
    assert results[0].channel == "email"
    assert results[0].success is True


def test_email_skipped_when_no_recipients():
    settings = make_settings(email_enabled=True, email_smtp_host="smtp.example.com",
                              email_from="from@example.com", email_to=[])
    dispatcher = NotificationDispatcher(settings)
    results = dispatcher.dispatch(make_briefing())
    assert results == []


def test_multiple_channels_dispatched():
    settings = make_settings(
        slack_webhook_url="https://hooks.slack.com/fake",
        teams_webhook_url="https://teams.webhook.fake/url",
    )
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch(make_briefing())
    assert len(results) == 2
    channels = {r.channel for r in results}
    assert channels == {"slack", "teams"}
