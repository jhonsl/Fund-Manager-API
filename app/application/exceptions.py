"""Application-layer signals (not domain errors).

``IdempotentReplay`` is a control-flow sentinel, not an error: when a request
with an already-seen Idempotency-Key reaches the repository, it carries back the
previously stored client so the use case can return it without reprocessing or
re-notifying. It is deliberately NOT a ``DomainError`` so it never reaches the
HTTP error map.
"""

from __future__ import annotations

from app.domain.entities.client import Client
from app.domain.exceptions.errors import DomainError


class IdempotentReplay(Exception):  # noqa: N818 - control-flow signal, not an error
    """Signals that a request was already processed; carries the stored result."""

    def __init__(self, client: Client) -> None:
        super().__init__("Idempotent replay")
        self.client = client


class IdempotencyConflictError(DomainError):
    """Same Idempotency-Key reused for a different operation or fund (409)."""

    def __init__(self, key: str) -> None:
        super().__init__(
            f"Idempotency-Key '{key}' was already used for a different request"
        )
        self.key = key


class InvalidCredentialsError(Exception):  # noqa: N818 - mapped to 401, not a domain error
    """Wrong email or password on login (→ 401). Same error for both cases to
    avoid leaking which clients exist."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InvalidTokenError(Exception):  # noqa: N818 - mapped to 401
    """A bearer token is missing, malformed or expired (→ 401)."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message)
