"""JWT access-token service (python-jose, HS256)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.application.exceptions import InvalidTokenError
from app.application.services.token_service import TokenClaims, TokenService
from app.domain.value_objects.enums import Role
from app.infrastructure.config.settings import get_settings


class JoseTokenService(TokenService):
    def create_access_token(self, client_id: str, role: Role) -> str:
        settings = get_settings()
        now = datetime.now(UTC)
        claims = {
            "sub": client_id,
            "role": role.value,
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        }
        return jwt.encode(
            claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def decode_access_token(self, token: str) -> TokenClaims:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            return TokenClaims(sub=payload["sub"], role=Role(payload["role"]))
        except (JWTError, KeyError, ValueError) as exc:
            raise InvalidTokenError() from exc
