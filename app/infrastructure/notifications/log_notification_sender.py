"""Log-based notification senders (simulated).

These stand in for real AWS SES (email) / SNS (SMS) integrations: they implement
the same ``NotificationSender`` port, so swapping to AWS later means replacing
only these classes. Errors are swallowed and logged so a notification failure
never affects an already-committed money operation.
"""

from __future__ import annotations

import logging

from app.application.services.notification_sender import NotificationSender
from app.domain.entities.client import Client

logger = logging.getLogger("notifications")


class EmailNotificationSender(NotificationSender):
    def send(self, client: Client, message: str) -> None:
        try:
            logger.info("[EMAIL] to %s: %s", client.email, message)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to send EMAIL notification")


class SmsNotificationSender(NotificationSender):
    def send(self, client: Client, message: str) -> None:
        try:
            logger.info("[SMS] to %s: %s", client.phone, message)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to send SMS notification")
