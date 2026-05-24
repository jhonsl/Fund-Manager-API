"""Notification dispatcher port.

A use case calls ``notify`` after a successful subscription; the dispatcher picks
the channel (email/SMS) based on the client's preference. The selection logic and
concrete senders live in infrastructure — the use case only depends on this port.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.client import Client


class NotificationDispatcher(ABC):
    """Routes a notification to the right channel for a client."""

    @abstractmethod
    def notify(self, client: Client, message: str) -> None:
        ...
