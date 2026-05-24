"""Unit tests for the jose JWT token service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.application.exceptions import InvalidTokenError
from app.domain.value_objects.enums import Role
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.jwt_service import JoseTokenService


def test_token_round_trip_preserves_sub_and_role():
    service = JoseTokenService()
    token = service.create_access_token("client-1", Role.ADMIN)

    claims = service.decode_access_token(token)
    assert claims.sub == "client-1"
    assert claims.role is Role.ADMIN


def test_tampered_token_is_rejected():
    service = JoseTokenService()
    token = service.create_access_token("client-1", Role.CLIENT)

    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token + "tampered")


def test_expired_token_is_rejected():
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "client-1",
            "role": "CLIENT",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError):
        JoseTokenService().decode_access_token(expired)
