"""Retry/dead-letter orchestration for notification delivery."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from src.delivery import DeliveryResult, NotificationDispatcher, NotificationSettings
from src.delivery_attempt_store import DeliveryAttemptStore

_DEFAULT_DB_PATH = Path("config/supplier_collab.db")


class NotificationRetryService:
    def __init__(
        self,
        settings: NotificationSettings,
        attempt_store: DeliveryAttemptStore | None = None,
        dispatcher_factory: Callable[[NotificationSettings], NotificationDispatcher] = NotificationDispatcher,
        max_attempts: int = 3,
    ) -> None:
        self.settings = settings
        self.attempt_store = attempt_store or DeliveryAttemptStore(
            os.getenv("SUPPLIER_COLLAB_DB_PATH", str(_DEFAULT_DB_PATH))
        )
        self.dispatcher = dispatcher_factory(settings)
        self.max_attempts = max_attempts

    def _configured_channels(self) -> list[str]:
        channels: list[str] = []
        if self.settings.slack_webhook_url:
            channels.append("slack")
        if self.settings.teams_webhook_url:
            channels.append("teams")
        if self.settings.email_enabled and self.settings.email_to:
            channels.append("email")
        return channels

    def dispatch_with_retries(self, briefing: dict[str, Any]) -> list[DeliveryResult]:
        final_results: list[DeliveryResult] = []
        briefing_id = str(briefing.get("briefing_id") or "")

        for channel in self._configured_channels():
            final_result = DeliveryResult(channel, False, "not attempted")
            for attempt in range(1, self.max_attempts + 1):
                result = self.dispatcher.dispatch_channel(channel, briefing)
                final_result = result
                if result.success:
                    self.attempt_store.record_attempt(
                        briefing_id=briefing_id,
                        channel=channel,
                        status="sent",
                        attempt_count=attempt,
                        payload=briefing,
                        last_error="",
                    )
                    break

                status = "dead_letter" if attempt == self.max_attempts else "failed"
                self.attempt_store.record_attempt(
                    briefing_id=briefing_id,
                    channel=channel,
                    status=status,
                    attempt_count=attempt,
                    payload=briefing,
                    last_error=result.error,
                )
            final_results.append(final_result)

        return final_results
