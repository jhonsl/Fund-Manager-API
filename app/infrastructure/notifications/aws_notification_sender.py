"""AWS notification senders (SES email / SNS SMS).

Real implementations of the ``NotificationSender`` port. They mirror the
log-based senders' contract: a delivery failure is logged and swallowed so it
never affects an already-committed money operation. Selected over the log
senders when ``settings.notifications_backend == "aws"``.
"""

from __future__ import annotations

import logging

from app.application.services.notification_sender import NotificationSender
from app.domain.entities.client import Client
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.dynamodb.client import get_aws_client

logger = logging.getLogger("notifications")

_SUBJECT = "BTG Pactual - Notificación de fondos"


class SesEmailSender(NotificationSender):
    """Sends email via AWS SES. The sender address must be SES-verified."""

    def send(self, client: Client, message: str) -> None:
        try:
            settings = get_settings()
            get_aws_client("ses").send_email(
                Source=settings.ses_sender_email,
                Destination={"ToAddresses": [client.email]},
                Message={
                    "Subject": {"Data": _SUBJECT, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": message, "Charset": "UTF-8"}},
                },
            )
            logger.info("[SES] sent to %s", client.email)
        except Exception:  # pragma: no cover - defensive; never break the op
            logger.exception("Failed to send SES email to %s", client.email)


class SnsSmsSender(NotificationSender):
    """Sends SMS via AWS SNS to the client's phone number (E.164 format)."""

    def send(self, client: Client, message: str) -> None:
        try:
            settings = get_settings()
            get_aws_client("sns").publish(
                PhoneNumber=client.phone,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {
                        "DataType": "String",
                        "StringValue": settings.sns_sender_id,
                    }
                },
            )
            logger.info("[SNS] sent to %s", client.phone)
        except Exception:  # pragma: no cover - defensive; never break the op
            logger.exception("Failed to send SNS SMS to %s", client.phone)
