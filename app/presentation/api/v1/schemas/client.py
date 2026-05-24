"""Pydantic schemas for client endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.domain.value_objects.enums import NotificationPreference, Role
from app.presentation.api.v1.schemas._fields import MoneyField


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: str
    email: str
    phone: str
    balance: MoneyField
    notify_pref: NotificationPreference
    role: Role
