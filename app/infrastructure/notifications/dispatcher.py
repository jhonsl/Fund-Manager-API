"""Notification dispatcher — selects the channel by client preference (Strategy)."""

from __future__ import annotations

from app.application.services.notification_dispatcher import NotificationDispatcher
from app.application.services.notification_sender import NotificationSender
from app.domain.entities.client import Client
from app.domain.value_objects.enums import NotificationPreference
from app.infrastructure.notifications.log_notification_sender import (
    EmailNotificationSender,
    SmsNotificationSender,
)


class LogNotificationDispatcher(NotificationDispatcher):
    """Routes to the email or SMS sender based on ``client.notify_pref``."""

    def __init__(
        self,
        senders: dict[NotificationPreference, NotificationSender] | None = None,
    ) -> None:
        self._senders: dict[NotificationPreference, NotificationSender] = senders or {
            NotificationPreference.EMAIL: EmailNotificationSender(),
            NotificationPreference.SMS: SmsNotificationSender(),
        }

    def notify(self, client: Client, message: str) -> None:
        sender = self._senders.get(client.notify_pref)
        if sender is not None:
            sender.send(client, message)
