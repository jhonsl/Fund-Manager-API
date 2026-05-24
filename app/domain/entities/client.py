"""Client entity — a platform user who manages their fund subscriptions."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.enums import NotificationPreference, Role
from app.domain.value_objects.money import Money


@dataclass
class Client:
    """A client account.

    ``balance`` changes over time (subscriptions debit it, cancellations credit
    it), so this entity is mutable. The balance-rule behaviour (subscribe/cancel)
    is added in the use-case step.
    """

    id: str
    email: str
    phone: str
    balance: Money
    notify_pref: NotificationPreference
    role: Role
    password_hash: str
