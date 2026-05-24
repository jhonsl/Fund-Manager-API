"""Pydantic schemas for transaction endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.value_objects.enums import TransactionType
from app.presentation.api.v1.schemas._fields import MoneyField


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: str
    type: TransactionType
    fund_id: str
    amount: MoneyField
    created_at: datetime
