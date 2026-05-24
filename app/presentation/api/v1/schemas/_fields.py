"""Reusable schema field types.

``MoneyField`` serializes a domain ``Money`` value object as an integer COP
amount, so every response schema can annotate a money field the same way
without repeating the serialization logic.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import PlainSerializer

from app.domain.value_objects.money import Money

MoneyField = Annotated[
    Money,
    PlainSerializer(lambda m: int(m.amount), return_type=int),
]
