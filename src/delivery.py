"""Notification delivery module (prototype).

Dispatches briefing summaries to configured channels: Slack webhook,
Teams webhook, and SMTP email. All channels are optional — only channels
with non-empty config are activated.

PROTOTYPE: No retry logic, no queue. Fire-and-forget per channel.
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, List

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NotificationSettings(BaseModel):
    automation_enabled: bool = True
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_from: str = ""
    email_to: List[str] = Field(default_factory=list)


@dataclass
class DeliveryResult:
    channel: str
    success: bool
    error: str = ""


class NotificationDispatcher:
    """Sends a briefing summary to all configured channels."""

    def __init__(self, settings: NotificationSettings) -> None:
        self.settings = settings

    def dispatch(self, briefing: dict[str, Any]) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        s = self.settings

        if s.slack_webhook_url:
            results.append(self._send_slack(briefing))

        if s.teams_webhook_url:
            results.append(self._send_teams(briefing))

        if s.email_enabled and s.email_to:
            results.append(self._send_email(briefing))

        return results

    # ------------------------------------------------------------------

    def _send_slack(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        text = (
            f":clipboard: *Supplier Briefing Ready* — {vendor} ({date})\n"
            f"Briefing ID: `{bid}`\n"
            f"Open in dashboard: http://localhost:3000/briefings/{bid}"
        )
        try:
            resp = httpx.post(
                self.settings.slack_webhook_url,
                json={"text": text},
                timeout=10,
            )
            if resp.status_code != 200:
                return DeliveryResult("slack", False, f"HTTP {resp.status_code}: {resp.text}")
            return DeliveryResult("slack", True)
        except Exception as exc:
            return DeliveryResult("slack", False, str(exc))

    def _send_teams(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0072C6",
            "summary": f"Briefing ready for {vendor}",
            "sections": [{
                "activityTitle": f"Supplier Briefing Ready: {vendor}",
                "activitySubtitle": f"Meeting: {date}",
                "facts": [{"name": "Briefing ID", "value": bid}],
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "Open Dashboard",
                "targets": [{"os": "default", "uri": f"http://localhost:3000/briefings/{bid}"}],
            }],
        }
        try:
            resp = httpx.post(self.settings.teams_webhook_url, json=payload, timeout=10)
            if resp.status_code != 200:
                return DeliveryResult("teams", False, f"HTTP {resp.status_code}: {resp.text}")
            return DeliveryResult("teams", True)
        except Exception as exc:
            return DeliveryResult("teams", False, str(exc))

    def _send_email(self, briefing: dict[str, Any]) -> DeliveryResult:
        vendor = briefing.get("vendor", "Unknown Vendor")
        date = briefing.get("meeting_date", "")
        bid = briefing.get("briefing_id", "")
        text_body = briefing.get("briefing_text", "")[:500] + "..."
        s = self.settings

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Briefing Ready] {vendor} — {date}"
        msg["From"] = s.email_from
        msg["To"] = ", ".join(s.email_to)
        msg.attach(MIMEText(
            f"Briefing for {vendor} ({date}) is ready.\n\nPreview:\n{text_body}\n\n"
            f"View: http://localhost:3000/briefings/{bid}\nID: {bid}",
            "plain",
        ))

        output_files = briefing.get("output_files", {})
        docx_path = output_files.get("docx_path")
        if docx_path:
            from pathlib import Path
            p = Path(docx_path)
            if p.exists():
                from email.mime.base import MIMEBase
                from email import encoders
                with open(p, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={p.name}",
                )
                msg.attach(part)

        try:
            with smtplib.SMTP(s.email_smtp_host, s.email_smtp_port) as server:
                if s.email_smtp_user:
                    server.starttls()
                    server.login(s.email_smtp_user, s.email_smtp_password)
                server.sendmail(s.email_from, s.email_to, msg.as_string())
            return DeliveryResult("email", True)
        except Exception as exc:
            return DeliveryResult("email", False, str(exc))
