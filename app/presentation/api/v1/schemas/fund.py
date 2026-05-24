"""Pydantic schemas for fund endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.domain.value_objects.enums import FundCategory
from app.presentation.api.v1.schemas._fields import MoneyField


class FundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: str
    name: str
    min_amount: MoneyField
    category: FundCategory
