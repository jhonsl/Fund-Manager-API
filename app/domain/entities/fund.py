"""Fund entity — a catalog investment fund the client can subscribe to."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.enums import FundCategory
from app.domain.value_objects.money import Money


@dataclass(frozen=True)
class Fund:
    """An investment fund. Catalog data is fixed (see seed)."""

    id: str
    name: str
    min_amount: Money
    category: FundCategory
