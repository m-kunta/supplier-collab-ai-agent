"""Tests for the DOCX email attachment added in Phase 9 (today)."""
import pytest
from unittest.mock import patch, MagicMock
from src.delivery import NotificationDispatcher, NotificationSettings


def make_email_settings():
    return NotificationSettings(
        email_enabled=True,
        email_smtp_host="smtp.example.com",
        email_smtp_port=587,
        email_from="from@example.com",
        email_to=["buyer@example.com"],
    )


def _smtp_ctx(mock_smtp_cls):
    """Wire the SMTP context manager mock."""
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_smtp


def test_email_attaches_docx_when_file_exists(tmp_path):
    """When output_files.docx_path points to a real file, it should be attached."""
    docx_file = tmp_path / "briefing.docx"
    docx_file.write_bytes(b"PK fake docx content")

    briefing = {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-09",
        "briefing_id": "xyz-789",
        "briefing_text": "Summary text",
        "output_files": {"docx_path": str(docx_file)},
    }

    dispatcher = NotificationDispatcher(make_email_settings())
    with patch("smtplib.SMTP") as mock_smtp_cls:
        smtp = _smtp_ctx(mock_smtp_cls)
        result = dispatcher.dispatch(briefing)

    assert result[0].success is True
    # Verify sendmail was called with a payload that includes the attachment header
    call_args = smtp.sendmail.call_args
    raw_message = call_args[0][2]  # positional arg 3: the raw message string
    assert "Content-Disposition" in raw_message
    assert "briefing.docx" in raw_message


def test_email_sends_without_attachment_when_docx_missing(tmp_path):
    """When docx_path points to a non-existent file, email should still send."""
    briefing = {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-09",
        "briefing_id": "xyz-789",
        "briefing_text": "Summary text",
        "output_files": {"docx_path": str(tmp_path / "nonexistent.docx")},
    }

    dispatcher = NotificationDispatcher(make_email_settings())
    with patch("smtplib.SMTP") as mock_smtp_cls:
        smtp = _smtp_ctx(mock_smtp_cls)
        result = dispatcher.dispatch(briefing)

    assert result[0].success is True
    raw_message = smtp.sendmail.call_args[0][2]
    assert "nonexistent.docx" not in raw_message


def test_email_sends_without_attachment_when_no_output_files():
    """Briefings with no output_files key should still email cleanly."""
    briefing = {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-09",
        "briefing_id": "xyz-789",
        "briefing_text": "Summary text",
    }

    dispatcher = NotificationDispatcher(make_email_settings())
    with patch("smtplib.SMTP") as mock_smtp_cls:
        smtp = _smtp_ctx(mock_smtp_cls)
        result = dispatcher.dispatch(briefing)

    assert result[0].success is True


def test_automation_enabled_flag_defaults_true():
    """automation_enabled should default to True."""
    settings = NotificationSettings()
    assert settings.automation_enabled is True


def test_automation_disabled_does_not_affect_dispatch():
    """dispatch() does not check automation_enabled — that gate lives in the scheduler."""
    settings = NotificationSettings(
        automation_enabled=False,
        slack_webhook_url="https://hooks.slack.com/fake",
    )
    dispatcher = NotificationDispatcher(settings)
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        results = dispatcher.dispatch({"vendor": "X", "meeting_date": "2026-05-09",
                                       "briefing_id": "b1"})
    # dispatch() is channel-level, not automation-level — still fires
    assert len(results) == 1
    assert results[0].success is True
