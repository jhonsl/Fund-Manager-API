"""Notification port (Strategy).

The application depends on this abstraction; concrete senders (log-based now,
SES/SNS later) live in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.client import Client


class NotificationSender(ABC):
    """Sends a notification to a client through a specific channel."""

    @abstractmethod
    def send(self, client: Client, message: str) -> None:
        ...
