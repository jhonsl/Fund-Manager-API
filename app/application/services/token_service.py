"""Access-token port.

Abstracts JWT creation/verification so use cases and auth dependencies do not
import jose directly. The concrete implementation lives in infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.value_objects.enums import Role


@dataclass(frozen=True)
class TokenClaims:
    """Decoded token payload the app cares about."""

    sub: str  # client id
    role: Role


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, client_id: str, role: Role) -> str:
        ...

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenClaims:
        """Return the claims, or raise InvalidTokenError if invalid/expired."""
