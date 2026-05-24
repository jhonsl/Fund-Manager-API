"""Subscription entity — an active client↔fund link.

Its existence means the client currently holds a subscription to the fund and
can therefore cancel it; cancelling removes the subscription.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects.money import Money


@dataclass(frozen=True)
class Subscription:
    """An active subscription of a client to a fund."""

    client_id: str
    fund_id: str
    amount: Money
    opened_at: datetime
