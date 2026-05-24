"""Input commands for use cases.

Plain frozen dataclasses (not Pydantic) so the application layer stays free of
web-framework concerns. The presentation layer maps request schemas to these.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.enums import NotificationPreference


@dataclass(frozen=True)
class CreateClientCommand:
    email: str
    phone: str
    notify_pref: NotificationPreference
    password: str


@dataclass(frozen=True)
class SubscribeCommand:
    client_id: str
    fund_id: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class CancelCommand:
    client_id: str
    fund_id: str
    idempotency_key: str | None = None
