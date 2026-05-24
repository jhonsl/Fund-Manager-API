"""``Money`` value object for COP amounts.

Wraps a ``Decimal`` to guarantee exact arithmetic (no binary-float rounding) on
balances and subscription amounts. This is a pure domain type: it must never
import boto3 — the Decimal <-> DynamoDB conversion happens in the infrastructure
layer. The system is single-currency (COP), so currency is implicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """An immutable, non-negative monetary amount in COP."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal")
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    @classmethod
    def of(cls, value: int | str | Decimal) -> Money:
        """Build Money from an int/str/Decimal. Never accept float (precision)."""
        if isinstance(value, float):
            raise TypeError("Use int, str or Decimal for Money, not float")
        return cls(Decimal(str(value)))

    def add(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def subtract(self, other: Money) -> Money:
        """Subtract another amount. Raises if the result would be negative."""
        return Money(self.amount - other.amount)

    def is_greater_than_or_equal(self, other: Money) -> bool:
        return self.amount >= other.amount

    def __lt__(self, other: Money) -> bool:
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"COP {self.amount:,.0f}"
