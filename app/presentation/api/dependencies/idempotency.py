"""Dependency that reads and validates the optional Idempotency-Key header."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

_MAX_KEY_LENGTH = 200


def idempotency_key(
    value: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    """Return the validated Idempotency-Key, or None if not provided."""
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Idempotency-Key header",
        )
    return value
