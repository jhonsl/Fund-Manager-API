"""Transaction entity — an immutable record of an opening or cancellation.

Every transaction has a unique id (business rule). The history feature lists a
client's transactions ordered by time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects.enums import TransactionType
from app.domain.value_objects.money import Money


@dataclass(frozen=True)
class Transaction:
    """A single fund transaction (apertura or cancelación)."""

    id: str
    client_id: str
    type: TransactionType
    fund_id: str
    amount: Money
    created_at: datetime
