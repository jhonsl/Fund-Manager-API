"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.domain.value_objects.enums import NotificationPreference


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str
    notify_pref: NotificationPreference


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
